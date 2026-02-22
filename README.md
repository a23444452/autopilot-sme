# AutoPilot SME - 中小製造業 AI 排程自動化平台

AutoPilot SME 是一個專為台灣中小型製造業（20-200 人）打造的 AI 排程自動化平台。透過智慧排程引擎、自然語言對話介面、三層記憶系統與合規治理機制，取代過去依賴資深員工經驗的手動排程流程。

## 解決的核心痛點

| 痛點 | 現況 | AutoPilot SME |
|------|------|---------------|
| 排程知識鎖在資深人員腦中 | 人走經驗走 | 三層記憶系統自動累積決策紀錄 |
| 插單重排耗時 2-4 小時 | 人工反覆調整 | AI 3 秒產出多方案建議 |
| 交期靠感覺估算 | 經驗法則、缺乏數據 | 數據驅動預測 + 信心指數 |
| 人員異動知識流失 | 交接困難 | 自動化決策記錄與語意搜尋 |

## 核心功能

### 1. 智慧排程引擎
三階段排程演算法：規則排序 → 限制滿足 → AI 最佳化，自動產出最佳化生產排程，支援甘特圖視覺化呈現。

### 2. 插單模擬分析
插單時自動模擬影響，產出 2-3 個可行方案，比較對現有訂單的影響，包含延遲天數、加班成本等。

### 3. 自然語言交期查詢
支援繁體中文對話查詢（例：「P001 500pcs 最快何時能交？」），回傳預估交期與信心指數。

### 4. 三層記憶系統
- **結構化記憶**（SQL）：產線資料、產品主檔、歷史工時
- **情節記憶**（Decision Records）：情境 → 方案 → 結果 → 教訓
- **語意記憶**（Vector Search）：透過 Qdrant 進行自然語言相似度搜尋

### 5. 合規治理儀表板
追蹤 LLM 模型使用量、成本統計、AI 決策稽核紀錄，確保 AI 使用透明可控。

### 6. 敏感資料保護
自動偵測 PII 等敏感資料，在送出至外部 LLM 前進行遮罩處理；高敏感內容自動路由至本地模型。

## 技術架構

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Port 3000)              │
│          Next.js 14 + shadcn/ui + ECharts           │
└────────────────────────┬────────────────────────────┘
                         │ API Proxy (/api/*)
┌────────────────────────▼────────────────────────────┐
│                    Backend (Port 8000)               │
│               FastAPI + SQLAlchemy 2.0               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ 排程引擎 │ │ 模擬引擎 │ │ LLM Router (多模型)  │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ 記憶系統 │ │ 隱私防護 │ │ 合規追蹤             │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
└───┬──────────────┬──────────────┬───────────────────┘
    │              │              │
┌───▼───┐    ┌────▼────┐   ┌────▼────┐
│ Postgres│   │ Qdrant  │   │  Redis  │
│  :5432 │    │  :6333  │   │  :6379  │
└────────┘    └─────────┘   └─────────┘
```

### 技術選型

| 層級 | 技術 | 版本 |
|------|------|------|
| 前端框架 | Next.js (App Router) | 14 |
| UI 元件庫 | shadcn/ui + Tailwind CSS | v3 |
| 圖表 | Apache ECharts | 5.5 |
| 後端框架 | FastAPI | 0.109 |
| ORM | SQLAlchemy (async) | 2.0 |
| 關聯式資料庫 | PostgreSQL | 15 |
| 向量資料庫 | Qdrant | latest |
| 快取 | Redis | 7 |
| LLM（主要） | Claude Sonnet | 4.6 |
| LLM（備援） | OpenAI GPT-4.1 / Ollama | - |

### LLM 多模型備援鏈

```
Claude Sonnet 4.6 (主要)
    ↓ 失敗時
OpenAI GPT-4.1 (備援)
    ↓ 失敗時
Ollama llama3.1:8b (本地端 / 隱私場景)
```

## 快速開始

### 前置需求

- [Docker](https://www.docker.com/) & Docker Compose
- [Node.js](https://nodejs.org/) 18+
- [Python](https://www.python.org/) 3.11+
- （選用）[Ollama](https://ollama.ai/) — 本地 LLM 執行

### 1. 複製環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入你的 API 金鑰：

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx   # Claude API 金鑰
OPENAI_API_KEY=sk-xxxxx          # OpenAI API 金鑰（選用，作為備援）
```

### 2. 使用 Docker Compose 啟動（推薦）

一鍵啟動所有服務：

```bash
docker-compose up -d
```

這會啟動：
- PostgreSQL (5432)
- Qdrant (6333)
- Redis (6379)
- Backend API (8000)
- Frontend (3000)

### 3. 本地開發模式

如果你想分開啟動前後端以便開發：

```bash
# 啟動基礎設施（資料庫、向量資料庫、快取）
docker-compose up -d postgres qdrant redis

# 啟動後端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 啟動前端（另開終端機）
cd frontend
npm install
npm run dev
```

### 4. 存取服務

| 服務 | URL |
|------|-----|
| 前端介面 | http://localhost:3000 |
| 後端 API | http://localhost:8000 |
| API 文件 (Swagger) | http://localhost:8000/docs |
| Qdrant Dashboard | http://localhost:6333/dashboard |

## 頁面導覽

| 頁面 | 路徑 | 說明 |
|------|------|------|
| 儀表板 | `/dashboard` | KPI 總覽、產線狀態、待處理警示 |
| 訂單管理 | `/orders` | 訂單 CRUD、篩選、狀態追蹤 |
| 排程中心 | `/schedule` | 甘特圖 + 表格雙視圖、重新排程 |
| 插單模擬 | `/simulate` | What-if 分析、多方案比較 |
| AI 對話 | `/chat` | 自然語言交期查詢、快捷操作 |
| 知識庫 | `/knowledge` | 產線、產品主檔、學習紀錄 |
| 合規儀表板 | `/compliance` | 模型用量、成本、決策稽核 |

## API 端點總覽

```
GET    /api/v1/health              # 健康檢查
POST   /api/v1/orders              # 建立訂單
GET    /api/v1/orders              # 查詢訂單列表
GET    /api/v1/orders/{id}         # 查詢單筆訂單
PUT    /api/v1/orders/{id}         # 更新訂單
DELETE /api/v1/orders/{id}         # 刪除訂單
POST   /api/v1/schedule/generate   # 產生排程
GET    /api/v1/schedule/current    # 取得當前排程
POST   /api/v1/simulate/rush-order # 插單模擬
POST   /api/v1/simulate/delivery   # 交期預估
POST   /api/v1/chat                # AI 對話
GET    /api/v1/memory/search       # 記憶搜尋
GET    /api/v1/compliance/usage    # 模型用量統計
GET    /api/v1/compliance/decisions # 決策稽核紀錄
```

完整 API 文件請參考：http://localhost:8000/docs

## 專案結構

```
autopilot-sme/
├── docker-compose.yml          # Docker 編排設定
├── .env.example                # 環境變數範本
├── backend/                    # FastAPI 後端
│   ├── app/
│   │   ├── api/v1/             # API 路由
│   │   ├── core/               # 核心設定（DB、Redis、Qdrant）
│   │   ├── models/             # SQLAlchemy 資料模型
│   │   ├── schemas/            # Pydantic 請求/回應 Schema
│   │   ├── services/           # 業務邏輯層
│   │   │   ├── scheduler.py    # 排程引擎
│   │   │   ├── simulator.py    # 模擬引擎
│   │   │   ├── chat_service.py # 對話服務
│   │   │   ├── memory_service.py # 記憶系統
│   │   │   ├── llm_router.py   # LLM 多模型路由
│   │   │   ├── privacy_guard.py # 隱私防護
│   │   │   └── compliance_service.py # 合規追蹤
│   │   └── db/                 # 資料庫初始化 & 種子資料
│   ├── alembic/                # 資料庫遷移
│   ├── tests/                  # 測試
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # Next.js 前端
│   ├── src/
│   │   ├── app/                # 頁面路由 (App Router)
│   │   ├── components/         # UI 元件
│   │   │   ├── layout/         # 側邊欄、頂部列
│   │   │   ├── dashboard/      # 儀表板元件
│   │   │   ├── schedule/       # 排程 & 甘特圖
│   │   │   ├── simulate/       # 模擬元件
│   │   │   ├── chat/           # 對話介面
│   │   │   ├── orders/         # 訂單元件
│   │   │   └── compliance/     # 合規元件
│   │   ├── hooks/              # 自訂 Hooks
│   │   └── lib/                # 工具函式、API client、型別
│   ├── Dockerfile
│   └── package.json
```

## 環境變數說明

### 後端 (`backend/.env`)

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql+asyncpg://autopilot:autopilot_dev@localhost:5432/autopilot_sme` |
| `REDIS_URL` | Redis 連線字串 | `redis://localhost:6379/0` |
| `QDRANT_HOST` | Qdrant 主機位址 | `localhost` |
| `QDRANT_PORT` | Qdrant 連接埠 | `6333` |
| `ANTHROPIC_API_KEY` | Claude API 金鑰 | - |
| `OPENAI_API_KEY` | OpenAI API 金鑰（備援） | - |
| `OLLAMA_BASE_URL` | Ollama 本地 URL | `http://localhost:11434` |

### 前端 (`frontend/.env.local`)

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `FASTAPI_URL` | 後端 API URL（Server-side proxy） | `http://localhost:8000` |
| `NEXT_PUBLIC_API_URL` | Client-side API URL | `http://localhost:3000/api` |

## 設計理念

- **AI 輔助，人類決策**：所有 AI 產出均標示為「建議」，需人工確認後方可執行
- **漸進式信任**：系統透過記憶系統持續學習，建議品質隨時間提升
- **隱私優先**：敏感資料在送出外部 LLM 前自動遮罩，高敏感內容路由至本地模型
- **合規透明**：所有 AI 呼叫皆有完整稽核軌跡，支援成本追蹤與決策回溯

## 授權條款

此專案為私有專案，保留所有權利。
