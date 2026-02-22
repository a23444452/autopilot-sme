"""Compliance API endpoints for usage stats and audit logs."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.compliance import UsageStats
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])


def _get_compliance_service(
    db: AsyncSession = Depends(get_db),
) -> ComplianceService:
    """Dependency to construct a ComplianceService."""
    return ComplianceService(db=db)


@router.get("/usage", response_model=UsageStats)
async def get_usage(
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    svc: ComplianceService = Depends(_get_compliance_service),
) -> UsageStats:
    """Get aggregated model usage statistics for a given period."""
    return await svc.get_usage_stats(
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/decisions", response_model=list[dict[str, Any]])
async def list_decisions(
    decision_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    svc: ComplianceService = Depends(_get_compliance_service),
) -> list[Any]:
    """List decision audit logs with optional type filter."""
    decisions = await svc.list_decisions(
        decision_type=decision_type,
        limit=limit,
        offset=skip,
    )
    # Return as dicts since DecisionLog model has from_attributes
    return [
        {
            "id": str(d.id),
            "decision_type": d.decision_type,
            "situation": d.situation,
            "context": d.context,
            "options_considered": d.options_considered,
            "chosen_option": d.chosen_option,
            "outcome": d.outcome,
            "lessons_learned": d.lessons_learned,
            "confidence": d.confidence,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in decisions
    ]
