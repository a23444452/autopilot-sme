## 團隊管理最佳實踐

  ### Teammate 完成後立即通知待命
  teammate 完成所有任務後，立即發送「無新任務，請待命」訊息，避免空轉重複回報。

  ### 避免過度阻塞 testing
  testing teammate 不要設為 blockedBy 所有開發任務。應先指派：
  1. 分析現有測試結構
  2. 為已完成的修復撰寫測試
  3. 檢查測試覆蓋率

  ### 任務分配要明確指定順序
  分配多個任務時，使用編號明確順序：「先做 #5，完成後做 #6，再做 #9」
  而非列一個長清單讓 teammate 自行判斷優先順序。

## AutoPilot SME 後端架構要點

  ### 共用 Helper
  - `backend/app/services/production_helpers.py` — scheduler/simulator 共用函式
  - 新增排程/模擬相關工具函式應放在此處

  ### 安全機制
  - `backend/app/core/auth.py` — API Key 認證 (開發模式 API_KEY="" 可跳過)
  - `backend/app/core/rate_limit.py` — Redis rate limit + in-memory fallback
  - 所有 authenticated 路由在 `router.py` 統一加上 `verify_api_key` dependency

  ### 狀態管理
  - 使用 `app.state` + FastAPI dependency injection，不要用 global 變數
  - Redis/Qdrant client 透過 `app.state.redis` / `app.state.qdrant` 存取

  ### Priority 語意
  - 1=最高, 5=最低 (前後端統一)
  - Schema validation: `Field(default=5, ge=1, le=5)`
  
## AutoPilot SME 前端架構要點

  ### API 型別
  - 所有型別定義在 `frontend/src/lib/types.ts`
  - API 函式在 `frontend/src/lib/api.ts`
  - 型別必須與後端 Pydantic schema 一致

  ### Error Handling
  - `frontend/src/app/error.tsx` — 全域 Error Boundary
  - Dashboard fallback mock data 必須顯示離線提示

  ### Priority 語意
  - 1=最高, 5=最低 (與後端統一)

