"""Chat service for natural language scheduling queries.

Provides:
- Context building from current schedule, relevant memories, and line status
- LLM call orchestration via LLMRouter with privacy sanitization
- Memory updates from conversation outcomes
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_line import ProductionLine
from app.models.schedule import ScheduledJob
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_router import LLMRouter
from app.services.memory_service import MemoryService
from app.services.privacy_guard import PrivacyGuard

logger = logging.getLogger(__name__)

# Maximum tokens to send to LLM for context
MAX_CONTEXT_TOKENS = 3000

# System prompt for the manufacturing scheduling assistant
SYSTEM_PROMPT = """你是一位專業的製造排程AI助手（AutoPilot SME）。你負責協助台灣中小企業的生產排程管理。

你的職責：
- 回答交期查詢，提供預估交貨日期和信心度
- 分析現有排程狀態並提供建議
- 協助評估急單插入的影響
- 基於歷史決策記錄提供參考建議

重要規則：
- 所有回覆使用繁體中文
- AI輸出都是「建議」（建議），絕不是「決策」（決策）——最終決定權在人類
- 提供信心百分比時，說明影響因素
- 引用歷史數據時，標明數據來源和時間範圍
- 若無相關歷史數據，明確告知使用者"""


class ChatService:
    """Orchestrates natural language chat with scheduling context."""

    def __init__(
        self,
        db: AsyncSession,
        llm_router: LLMRouter,
        memory_service: MemoryService,
        privacy_guard: PrivacyGuard | None = None,
    ) -> None:
        self.db = db
        self._llm = llm_router
        self._memory = memory_service
        self._privacy = privacy_guard or PrivacyGuard()

    async def handle_message(self, request: ChatRequest) -> ChatResponse:
        """Process a chat message: build context, call LLM, update memory.

        Steps:
        1. Sanitize user input via PrivacyGuard
        2. Build context from schedule, line status, and relevant memories
        3. Call LLM with enriched prompt
        4. Store conversation as episodic memory
        5. Return structured response
        """
        conversation_id = request.conversation_id or str(uuid.uuid4())
        sources: list[str] = []

        # Step 1: Privacy check and sanitization
        use_local = self._privacy.should_use_local_llm(request.message)
        sanitized_message = self._privacy.sanitize(request.message)

        # Step 2: Build context
        context_parts: list[str] = []

        # 2a: Current schedule context
        schedule_context = await self._build_schedule_context()
        if schedule_context:
            context_parts.append(schedule_context)
            sources.append("current_schedule")

        # 2b: Production line status
        line_context = await self._build_line_status_context()
        if line_context:
            context_parts.append(line_context)
            sources.append("line_status")

        # 2c: Relevant memories from semantic search
        memory_context, memory_sources = await self._build_memory_context(
            sanitized_message
        )
        if memory_context:
            context_parts.append(memory_context)
            sources.extend(memory_sources)

        # 2d: Additional context from request
        if request.context:
            extra = "\n".join(f"- {k}: {v}" for k, v in request.context.items())
            context_parts.append(f"【額外資訊】\n{extra}")

        # Build enriched prompt
        context_block = "\n\n".join(context_parts) if context_parts else "（目前無額外排程資訊）"
        enriched_prompt = (
            f"【背景資訊】\n{context_block}\n\n"
            f"【使用者問題】\n{sanitized_message}"
        )

        # Truncate if too long
        if len(enriched_prompt) > MAX_CONTEXT_TOKENS * 4:
            enriched_prompt = enriched_prompt[: MAX_CONTEXT_TOKENS * 4] + "\n...(內容已截斷)"

        # Step 3: Call LLM
        try:
            llm_response = await self._llm.call(
                prompt=enriched_prompt,
                system=SYSTEM_PROMPT,
                task_type="chat",
                prefer_local=use_local,
            )
            reply = llm_response.content
            metadata: dict[str, Any] = {
                "provider": llm_response.provider,
                "model": llm_response.model,
                "input_tokens": llm_response.input_tokens,
                "output_tokens": llm_response.output_tokens,
                "latency_ms": llm_response.latency_ms,
                "privacy_local": use_local,
            }
        except Exception as exc:
            logger.error("LLM call failed in chat: %s", exc)
            reply = (
                "抱歉，AI助手暫時無法回應。系統將使用基本排程資訊回答。\n\n"
                "建議：請稍後再試，或直接查看排程頁面獲取最新資訊。"
            )
            metadata = {"error": str(exc), "fallback": True}

        # Step 4: Store as episodic memory
        try:
            await self._memory.create_decision(
                decision_type="chat",
                situation=f"使用者詢問：{sanitized_message[:200]}",
                context={"conversation_id": conversation_id},
                chosen_option=reply[:500],
                confidence=0.0,
            )
        except Exception as exc:
            logger.warning("Failed to store chat memory: %s", exc)

        # Step 5: Generate follow-up suggestions
        suggestions = self._generate_suggestions(request.message)

        return ChatResponse(
            reply=reply,
            conversation_id=conversation_id,
            sources=sources,
            suggestions=suggestions,
            metadata=metadata,
        )

    # -------------------------------------------------------------------
    # Context Building
    # -------------------------------------------------------------------

    async def _build_schedule_context(self) -> str:
        """Build context string from current scheduled jobs."""
        stmt = (
            select(ScheduledJob)
            .where(ScheduledJob.status.in_(["planned", "in_progress"]))
            .order_by(ScheduledJob.planned_start)
            .limit(20)
        )
        result = await self.db.execute(stmt)
        jobs = list(result.scalars().all())

        if not jobs:
            return ""

        lines_text: list[str] = []
        for job in jobs:
            start = job.planned_start.strftime("%m/%d %H:%M") if job.planned_start else "?"
            end = job.planned_end.strftime("%m/%d %H:%M") if job.planned_end else "?"
            lines_text.append(
                f"  - 工單 {job.id!s:.8}: 產線{job.production_line_id!s:.8} "
                f"| {start} → {end} | 數量:{job.quantity} | 狀態:{job.status}"
            )

        return f"【目前排程】共 {len(jobs)} 筆工單\n" + "\n".join(lines_text[:15])

    async def _build_line_status_context(self) -> str:
        """Build context string from production line status."""
        stmt = select(ProductionLine).where(ProductionLine.status == "active")
        result = await self.db.execute(stmt)
        lines = list(result.scalars().all())

        if not lines:
            return ""

        lines_text: list[str] = []
        for line in lines:
            lines_text.append(
                f"  - {line.name}: 狀態={line.status}, "
                f"效率={line.efficiency_factor:.0%}"
            )

        return f"【產線狀態】共 {len(lines)} 條產線\n" + "\n".join(lines_text)

    async def _build_memory_context(
        self, query: str
    ) -> tuple[str, list[str]]:
        """Search relevant memories and build context string."""
        sources: list[str] = []

        try:
            hits = await self._memory.search_memories(query, limit=5)
        except Exception as exc:
            logger.warning("Memory search failed: %s", exc)
            return "", sources

        if not hits:
            return "", sources

        memory_texts: list[str] = []
        for hit in hits:
            payload = hit.get("payload", {})
            score = hit.get("score", 0.0)
            category = payload.get("category", "unknown")
            content = payload.get("content", "")

            if content:
                memory_texts.append(
                    f"  - [{category}] (相關度:{score:.2f}) {content[:150]}"
                )
                sources.append(f"memory:{payload.get('memory_id', 'unknown')}")

        if not memory_texts:
            return "", sources

        return (
            f"【相關歷史記錄】找到 {len(memory_texts)} 筆相關決策\n"
            + "\n".join(memory_texts[:5])
        ), sources

    # -------------------------------------------------------------------
    # Suggestion Generation
    # -------------------------------------------------------------------

    @staticmethod
    def _generate_suggestions(message: str) -> list[str]:
        """Generate follow-up action suggestions based on the user's message."""
        suggestions: list[str] = []
        msg_lower = message.lower()

        if any(kw in msg_lower for kw in ["交期", "delivery", "何時", "when"]):
            suggestions.append("查看完整排程甘特圖")
            suggestions.append("模擬急單插入影響")

        if any(kw in msg_lower for kw in ["急單", "rush", "插單"]):
            suggestions.append("執行急單模擬分析")
            suggestions.append("查看受影響訂單")

        if any(kw in msg_lower for kw in ["產線", "line", "設備", "故障"]):
            suggestions.append("查看產線即時狀態")
            suggestions.append("重新排程建議")

        if any(kw in msg_lower for kw in ["排程", "schedule", "重排"]):
            suggestions.append("產生新排程")
            suggestions.append("查看排程品質指標")

        # Always provide at least one suggestion
        if not suggestions:
            suggestions.append("查詢交期預估")
            suggestions.append("查看今日排程")

        return suggestions[:4]
