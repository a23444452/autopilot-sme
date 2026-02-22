"""Compliance service for model usage tracking, cost calculation, and audit logging.

Provides:
- Model usage tracking: persist every LLM call to the database
- Cost calculation per provider/model
- Decision audit logging
- Usage statistics aggregation for compliance dashboard
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ModelUsageLog
from app.models.memory import DecisionLog
from app.schemas.compliance import ComplianceReport, UsageStats

logger = logging.getLogger(__name__)

# Cost per 1M tokens by provider/model (input, output) in USD
COST_TABLE: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-opus-4-6": (5.0, 25.0),
    # OpenAI
    "gpt-4.1": (2.0, 8.0),
    "gpt-4.1-mini": (0.4, 1.6),
    "gpt-4.1-nano": (0.1, 0.4),
    # Ollama (local — no cost)
    "llama3.1:8b": (0.0, 0.0),
    "mistral:7b": (0.0, 0.0),
    "qwen2.5:7b": (0.0, 0.0),
}


class ComplianceService:
    """Tracks model usage, calculates costs, and manages audit logs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -------------------------------------------------------------------
    # Model Usage Tracking
    # -------------------------------------------------------------------

    async def log_usage(
        self,
        model_name: str,
        provider: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: str = "success",
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelUsageLog:
        """Persist a single LLM call record to the database."""
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(model_name, input_tokens, output_tokens)

        log = ModelUsageLog(
            model_name=model_name,
            provider=provider,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            metadata=metadata,
        )
        self.db.add(log)
        await self.db.flush()

        logger.info(
            "Logged usage: model=%s provider=%s tokens=%d cost=$%.6f task=%s",
            model_name, provider, total_tokens, cost, task_type,
        )
        return log

    # -------------------------------------------------------------------
    # Cost Calculation
    # -------------------------------------------------------------------

    @staticmethod
    def _calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost for a model call based on token counts."""
        rates = COST_TABLE.get(model_name, (0.0, 0.0))
        input_cost = (input_tokens / 1_000_000) * rates[0]
        output_cost = (output_tokens / 1_000_000) * rates[1]
        return round(input_cost + output_cost, 8)

    # -------------------------------------------------------------------
    # Usage Statistics
    # -------------------------------------------------------------------

    async def get_usage_stats(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> UsageStats:
        """Aggregate usage statistics for a given period."""
        stmt = select(ModelUsageLog)
        if period_start:
            stmt = stmt.where(ModelUsageLog.created_at >= period_start)
        if period_end:
            stmt = stmt.where(ModelUsageLog.created_at <= period_end)

        result = await self.db.execute(stmt)
        logs = list(result.scalars().all())

        if not logs:
            return UsageStats(
                period_start=period_start,
                period_end=period_end,
            )

        total_calls = len(logs)
        total_tokens = sum(l.total_tokens for l in logs)
        total_cost = sum(l.cost_usd for l in logs)
        avg_latency = sum(l.latency_ms for l in logs) / total_calls if total_calls else 0.0
        error_count = sum(1 for l in logs if l.status != "success")

        # Group by provider
        calls_by_provider: dict[str, int] = {}
        for l in logs:
            calls_by_provider[l.provider] = calls_by_provider.get(l.provider, 0) + 1

        # Group by task type
        calls_by_task: dict[str, int] = {}
        for l in logs:
            calls_by_task[l.task_type] = calls_by_task.get(l.task_type, 0) + 1

        return UsageStats(
            total_calls=total_calls,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            avg_latency_ms=round(avg_latency, 1),
            calls_by_provider=calls_by_provider,
            calls_by_task_type=calls_by_task,
            error_rate=round(error_count / total_calls, 4) if total_calls else 0.0,
            period_start=period_start,
            period_end=period_end,
        )

    async def get_model_breakdown(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get per-model usage breakdown."""
        stmt = select(
            ModelUsageLog.model_name,
            ModelUsageLog.provider,
            func.count().label("call_count"),
            func.sum(ModelUsageLog.total_tokens).label("total_tokens"),
            func.sum(ModelUsageLog.cost_usd).label("total_cost"),
            func.avg(ModelUsageLog.latency_ms).label("avg_latency"),
        ).group_by(ModelUsageLog.model_name, ModelUsageLog.provider)

        if period_start:
            stmt = stmt.where(ModelUsageLog.created_at >= period_start)
        if period_end:
            stmt = stmt.where(ModelUsageLog.created_at <= period_end)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "model_name": row.model_name,
                "provider": row.provider,
                "call_count": row.call_count,
                "total_tokens": row.total_tokens or 0,
                "total_cost_usd": round(float(row.total_cost or 0), 6),
                "avg_latency_ms": round(float(row.avg_latency or 0), 1),
            }
            for row in rows
        ]

    # -------------------------------------------------------------------
    # Decision Audit Logging
    # -------------------------------------------------------------------

    async def log_decision(
        self,
        decision_type: str,
        situation: str,
        chosen_option: str,
        confidence: float,
        context: dict[str, Any] | None = None,
        options_considered: dict[str, Any] | None = None,
    ) -> DecisionLog:
        """Create an audit-trail decision log entry."""
        decision = DecisionLog(
            decision_type=decision_type,
            situation=situation,
            context=context,
            options_considered=options_considered,
            chosen_option=chosen_option,
            confidence=confidence,
        )
        self.db.add(decision)
        await self.db.flush()

        logger.info(
            "Logged decision: type=%s confidence=%.2f",
            decision_type, confidence,
        )
        return decision

    async def list_decisions(
        self,
        decision_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DecisionLog]:
        """List decision audit logs with optional type filter."""
        stmt = select(DecisionLog).order_by(DecisionLog.created_at.desc())
        if decision_type:
            stmt = stmt.where(DecisionLog.decision_type == decision_type)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Compliance Report Generation
    # -------------------------------------------------------------------

    async def generate_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> ComplianceReport:
        """Generate a full compliance report for a period."""
        stats = await self.get_usage_stats(period_start, period_end)
        breakdown = await self.get_model_breakdown(period_start, period_end)

        # Check for policy violations
        violations: list[str] = []
        if stats.error_rate > 0.1:
            violations.append(
                f"錯誤率 {stats.error_rate:.1%} 超過 10% 閾值"
            )
        if stats.total_cost_usd > 100.0:
            violations.append(
                f"期間總成本 ${stats.total_cost_usd:.2f} 超過 $100 預算警告線"
            )

        # Generate recommendations
        recommendations: list[str] = []
        if stats.calls_by_provider.get("ollama", 0) == 0 and stats.total_calls > 0:
            recommendations.append(
                "建議啟用本地 Ollama 模型以降低成本和延遲"
            )
        if stats.avg_latency_ms > 5000:
            recommendations.append(
                "平均延遲偏高，建議優先使用較快的模型（如 gpt-4.1-mini）"
            )

        report_id = f"RPT-{period_start.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

        return ComplianceReport(
            report_id=report_id,
            generated_at=datetime.now(timezone.utc),
            period_start=period_start,
            period_end=period_end,
            usage_stats=stats,
            model_breakdown=breakdown,
            policy_violations=violations,
            recommendations=recommendations,
        )
