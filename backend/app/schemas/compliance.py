"""Compliance Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UsageStats(BaseModel):
    """Aggregated model usage statistics."""

    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    calls_by_provider: dict[str, int] = Field(default_factory=dict)
    calls_by_task_type: dict[str, int] = Field(default_factory=dict)
    error_rate: float = 0.0
    period_start: datetime | None = None
    period_end: datetime | None = None


class ComplianceReport(BaseModel):
    """Compliance report for AI model usage."""

    model_config = {"protected_namespaces": ()}

    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    usage_stats: UsageStats
    model_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    policy_violations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
