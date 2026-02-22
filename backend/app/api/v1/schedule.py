"""Schedule API endpoints for generating and viewing production schedules."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.schedule import ScheduledJob
from app.schemas.schedule import ScheduledJobResponse, ScheduleRequest, ScheduleResult
from app.services.scheduler import SchedulerService, SchedulingError

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/generate", response_model=ScheduleResult)
async def generate_schedule(
    payload: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
) -> ScheduleResult:
    """Trigger schedule generation using the three-phase scheduling engine.

    Accepts optional order IDs, horizon, and strategy parameters.
    Returns generated jobs with metrics and warnings.
    """
    try:
        service = SchedulerService(db)
        result = await service.generate_schedule(payload)
        return result
    except SchedulingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/current", response_model=list[ScheduledJobResponse])
async def get_current_schedule(
    status_filter: str | None = Query(None, alias="status"),
    production_line_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduledJob]:
    """Get the current schedule with planned/in-progress jobs.

    Supports optional filtering by status and production line.
    """
    query = (
        select(ScheduledJob)
        .options(selectinload(ScheduledJob.product))
        .order_by(ScheduledJob.planned_start)
    )

    if status_filter is not None:
        query = query.where(ScheduledJob.status == status_filter)
    else:
        query = query.where(ScheduledJob.status.in_(["planned", "in_progress"]))

    if production_line_id is not None:
        query = query.where(ScheduledJob.production_line_id == production_line_id)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
