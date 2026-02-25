# 產線機台連結與自動排程分配 — 設計文件

**日期**: 2026-02-25
**狀態**: Approved
**方案**: 方案 A — 資料模型驅動（由內而外）

## 背景

AutoPilot SME 目前的資料模型是簡化的平面結構，缺少製程站別、製程路線、機台能力矩陣等核心概念。需要擴充資料模型並建立與實際產線的連結，實現：

1. 確認實際產線中每一製程站別的生產時間
2. 不同產線能做哪些產品（精確的能力匹配）
3. 產品規格書讀取後自動分配到對應產線

### 環境條件

| 項目 | 內容 |
|------|------|
| 產線環境 | PLC + MES/SCADA |
| 製程結構 | 線性流程，3-5 個製程站別 |
| 規格書格式 | PDF/Word 完整製造文件（BOM、製程路線、品檢點、SOP） |
| 隱私需求 | 規格書含機密製造參數，需分層隱私保護 |

---

## Phase 1：資料模型擴充

### 新增資料表

#### process_stations（製程站別）

代表產線上的一個工作站。

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID | Primary Key |
| production_line_id | UUID FK | 所屬產線 |
| name | str(100) | e.g. "錫膏印刷", "回焊爐", "AOI檢測" |
| station_order | int | 在該產線中的順序 (1, 2, 3...) |
| equipment_type | str(50) | 設備類型 e.g. "solder_printer", "reflow_oven" |
| standard_cycle_time | float | 該站標準節拍時間 (秒/件) |
| actual_cycle_time | float (nullable) | 從 MES 學到的實際節拍 |
| capabilities | JSONB (nullable) | 該站能處理的參數範圍 |
| status | str(20) | active / maintenance / inactive |
| created_at / updated_at | datetime(tz) | 時間戳 |

`capabilities` 範例：
```json
{"max_board_width": 450, "temperature_range": [200, 280]}
```

#### process_routes（製程路線）

定義某產品要經過哪些站別、順序和各站參數要求。

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID | Primary Key |
| product_id | UUID FK | 所屬產品 |
| version | int | 路線版本（規格書更新時遞增） |
| is_active | bool | 當前有效版本 |
| steps | JSONB | 製程步驟陣列 |
| source | str(20) | "manual" / "spec_parsed" / "mes_learned" |
| source_file | str (nullable) | 原始規格書檔案路徑 |
| created_at / updated_at | datetime(tz) | 時間戳 |

`steps` 範例：
```json
[
  {
    "step_order": 1,
    "equipment_type": "solder_printer",
    "required_params": {"stencil_thickness": 0.12},
    "estimated_cycle_time": 8.5,
    "quality_checkpoints": ["solder_paste_height"]
  },
  {
    "step_order": 2,
    "equipment_type": "pick_and_place",
    "required_params": {"min_component_size": "0402"},
    "estimated_cycle_time": 12.0,
    "quality_checkpoints": []
  },
  {
    "step_order": 3,
    "equipment_type": "reflow_oven",
    "required_params": {"peak_temperature": 260},
    "estimated_cycle_time": 45.0,
    "quality_checkpoints": ["reflow_profile"]
  }
]
```

#### line_capability_matrix（產線能力矩陣）

取代現有 `allowed_products` JSONB 欄位，改為精確的能力匹配。

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID | Primary Key |
| production_line_id | UUID FK | 所屬產線 |
| equipment_type | str(50) | 對應 station 的設備類型 |
| capability_params | JSONB | 該設備實際能力範圍 |
| throughput_range | JSONB | {"min": 80, "max": 120, "unit": "pcs/hr"} |
| updated_at | datetime(tz) | 時間戳 |

### 匹配邏輯

```
ProductRoute.steps[i].equipment_type + required_params
                    ↕ 比對
LineCapabilityMatrix.equipment_type + capability_params
                    ↓
            匹配結果：可用產線清單 + 各站預估時間
```

### 排程引擎升級

- `is_product_allowed()` → 改為查詢 capability matrix 匹配
- `_score_assignment()` → 改用瓶頸站 cycle time 計算
- `ScheduledJob` 可選擇性擴充，記錄各站排程時間

瓶頸站計算邏輯：
```python
def calculate_production_time(route, line, quantity, yield_rate):
    station_times = []
    for step in route.steps:
        station = get_station(line, step.equipment_type)
        ct = station.actual_cycle_time or step.estimated_cycle_time
        station_times.append(ct)

    bottleneck_time = max(station_times)  # 秒/件
    total_hours = (quantity / yield_rate * bottleneck_time) / 3600
    total_setup = sum(step.setup_time for step in route.steps)
    return total_hours + total_setup / 60
```

---

## Phase 2：規格書 AI 解析引擎

### 架構

```
PDF/Word 上傳
     ↓
  文件解析層 (PyMuPDF / python-docx 提取文字 + 表格)
     ↓
  LLM 結構化提取 (依隱私等級選擇模型)
     ↓
  人工確認介面 (審核 AI 解析結果)
     ↓
  寫入 ProcessRoute + 觸發產線匹配
```

### 隱私保護分層

| Level | 策略 | 準確度 | 風險 |
|-------|------|--------|------|
| 1 (預設) | 完全本地處理 (Ollama llama3.1:8b) | 中 | 零外洩 |
| 2 (可選) | privacy_guard 脫敏後送雲端 LLM | 高 | 低殘留風險 |
| 3 (企業版) | 內網私有部署大模型 (Llama 70B+) | 高 | 零外洩 |

設定: `SPEC_PARSING_PRIVACY_LEVEL` in config

### 後端服務

#### SpecParserService (`backend/app/services/spec_parser.py`)

- `parse_spec_file(file)` → 文件解析 + LLM 結構化提取
- `extract_process_route(parsed)` → 提取製程路線、BOM、品檢點
- `match_production_lines(route)` → 比對能力矩陣，回傳匹配結果

### 前端頁面

`/products/[id]/spec-upload`:
- 拖拽上傳區
- 解析進度顯示
- 結果預覽（可編輯製程路線 + 匹配產線建議）
- 原始文件對照檢視
- 確認寫入按鈕

### API 端點

```
POST /api/v1/specs/upload          # 上傳規格書
GET  /api/v1/specs/{id}/status     # 解析進度
GET  /api/v1/specs/{id}/result     # 解析結果
POST /api/v1/specs/{id}/confirm    # 確認並寫入 ProcessRoute
GET  /api/v1/products/{id}/routes  # 查詢產品製程路線
POST /api/v1/matching/evaluate     # 評估產品 ↔ 產線匹配
```

---

## Phase 3：MES 介接層

### 架構

```
MES / SCADA 系統
     ↓ (OPC-UA / REST API / MQTT)
  MES Adapter Layer (協議轉換)
     ↓
  Data Collector Service (定期拉取 / 訂閱推送)
     ↓
  Redis (即時數據快取)
     ↓
  ├── 即時看板 (WebSocket → 前端 Dashboard)
  └── 學習引擎 (歷史數據 → 校準 actual_cycle_time)
```

### 支援協議

| 協議 | 套件 | 適用場景 |
|------|------|---------|
| OPC-UA | `asyncua` | 西門子/三菱 PLC + SCADA |
| REST API | `httpx` | 現代 MES 系統 |
| MQTT | `aiomqtt` | IoT 閘道器 |

初期先實作 REST API adapter。

### 後端服務

#### MesAdapterService (`backend/app/services/mes_adapter.py`)
- 統一介面：connect, disconnect, get_station_status, get_production_count, subscribe_events

#### StationDataCollector (`backend/app/services/station_data_collector.py`)
- collect_cycle_times, collect_production_counts, detect_anomalies

#### CycleTimeLearner (`backend/app/services/cycle_time_learner.py`)
- 從歷史 MES 數據學習各站實際 cycle time
- 移動平均計算 → 更新 actual_cycle_time
- 記錄學習軌跡到 memory_service

### 新增資料表

#### mes_connections

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID | Primary Key |
| production_line_id | UUID FK | 所屬產線 |
| protocol | str(20) | "opcua" / "rest" / "mqtt" |
| connection_config | JSONB | 連線參數 |
| status | str(20) | connected / disconnected / error |
| last_sync_at | datetime(tz) | 最後同步時間 |

#### station_metrics（時序數據）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID | Primary Key |
| station_id | UUID FK | 所屬站別 |
| timestamp | datetime(tz) | 數據時間 |
| cycle_time | float | 實際 cycle time |
| product_sku | str | 生產的產品 |
| is_anomaly | bool | 是否異常 |
| raw_data | JSONB | MES 原始數據備查 |

### 前端頁面

`/production-lines/[id]/monitoring`:
- 各站即時狀態看板（WebSocket）
- MES 連線設定
- 歷史趨勢圖

---

## Phase 4：智慧匹配引擎

### 自動匹配流程

```
ProcessRoute 的每個 step:
  1. 查詢 LineCapabilityMatrix WHERE equipment_type = step.equipment_type
  2. 過濾 capability_params 包含 required_params
  3. 排名依據:
     - 能力餘裕度 (capability headroom)
     - 歷史 actual_cycle_time
     - 產線當前負載率
     - 換線時間
```

### 輸出

- 完全匹配的產線清單（所有站別都能做）
- 部分匹配 + 缺少的能力提示
- 每條產線的預估總生產時間

### 學習回饋迴路

```
實際生產完成 → MES 數據 → CycleTimeLearner
→ 更新 actual_cycle_time → 下次排程更精確
→ 記錄到 memory_service (決策改進軌跡)
```

### API 端點

```
GET    /api/v1/lines/{id}/stations         # 查詢產線所有站別
POST   /api/v1/lines/{id}/stations         # 新增站別
PUT    /api/v1/stations/{id}               # 更新站別
POST   /api/v1/matching/evaluate           # 產品 ↔ 產線匹配評估
GET    /api/v1/matching/recommendations    # 批量匹配建議
POST   /api/v1/mes/connections             # 設定 MES 連線
GET    /api/v1/mes/connections/{id}/test   # 測試連線
GET    /api/v1/lines/{id}/realtime         # 即時站別數據 (WebSocket)
GET    /api/v1/stations/{id}/metrics       # 站別歷史指標
```

---

## Roadmap

| Phase | 內容 | 交付物 |
|-------|------|--------|
| **Phase 1** | 資料模型擴充 | ProcessStation + ProcessRoute + CapabilityMatrix + Migration + 排程引擎升級 |
| **Phase 2** | 規格書解析 | SpecParserService + 上傳/確認 UI + 自動建立 ProcessRoute |
| **Phase 3** | MES 介接 | MesAdapter + DataCollector + CycleTimeLearner + 即時看板 |
| **Phase 4** | 智慧匹配 | MatchingEngine + 自動分配建議 + 學習回饋迴路 |

每個 Phase 可獨立部署和使用。
