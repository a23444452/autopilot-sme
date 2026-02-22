"""Simulation API endpoints for rush order and delivery date estimation."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.simulator import RushOrderInput, SimulationError, SimulatorService

router = APIRouter(prefix="/simulate", tags=["simulate"])


class RushOrderRequest(BaseModel):
    """Request schema for rush order simulation."""

    product_id: uuid.UUID
    quantity: int = Field(..., ge=1)
    target_date: datetime
    priority: int = Field(default=1, ge=1, le=5)


class DeliveryEstimateRequest(BaseModel):
    """Request schema for delivery date estimation."""

    product_id: uuid.UUID
    quantity: int = Field(..., ge=1)


class DeliveryEstimateResponse(BaseModel):
    """Response schema for delivery date estimation."""

    product_id: uuid.UUID
    quantity: int
    estimated_completion: datetime
    confidence: float = Field(description="Confidence score 0-100")
    earliest: datetime
    latest: datetime
    notes: list[str] = Field(default_factory=list)


@router.post("/rush-order")
async def simulate_rush_order(
    payload: RushOrderRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Simulate inserting a rush order into the current schedule.

    Returns 2-3 feasible scenarios with impact analysis including
    affected orders, overtime costs, and recommendations.
    """
    try:
        service = SimulatorService(db)
        result = await service.simulate_rush_order(
            RushOrderInput(
                product_id=payload.product_id,
                quantity=payload.quantity,
                target_date=payload.target_date,
                priority=payload.priority,
            )
        )
        return result
    except SimulationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/delivery", response_model=DeliveryEstimateResponse)
async def estimate_delivery(
    payload: DeliveryEstimateRequest,
    db: AsyncSession = Depends(get_db),
) -> DeliveryEstimateResponse:
    """Estimate delivery date for a given product and quantity.

    Uses the current schedule state and production capacity to estimate
    earliest, latest, and most likely completion dates with confidence.
    """
    from sqlalchemy import select

    from app.models.product import Product
    from app.models.production_line import ProductionLine
    from app.models.schedule import ScheduledJob
    from app.services.scheduler import SchedulerService

    # Fetch product
    result = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Calculate production time
    cycle_time = product.learned_cycle_time or product.standard_cycle_time
    effective_qty = payload.quantity / max(product.yield_rate, 0.01)
    production_hours = (effective_qty * cycle_time) / 60.0 + product.setup_time / 60.0

    # Find earliest available line
    lines_result = await db.execute(
        select(ProductionLine).where(ProductionLine.status == "active")
    )
    lines = list(lines_result.scalars().all())

    if not lines:
        raise HTTPException(
            status_code=422, detail="No active production lines available"
        )

    now = datetime.now(timezone.utc)
    notes: list[str] = []

    # Find the earliest line availability
    earliest_start = now
    for line in lines:
        jobs_result = await db.execute(
            select(ScheduledJob)
            .where(
                ScheduledJob.production_line_id == line.id,
                ScheduledJob.status.in_(["planned", "in_progress"]),
            )
            .order_by(ScheduledJob.planned_end.desc())
            .limit(1)
        )
        last_job = jobs_result.scalar_one_or_none()
        line_available = last_job.planned_end if last_job else now
        if line_available < earliest_start or earliest_start == now:
            earliest_start = line_available

    aligned_start = SchedulerService._align_to_work_start(earliest_start)
    from app.services.simulator import SimulatorService as SimSvc

    estimated_end = SimSvc._advance_work_hours(aligned_start, production_hours)

    # Confidence based on data quality
    confidence = 75.0
    if product.learned_cycle_time:
        confidence = 90.0
        notes.append("Using learned cycle time from historical data")
    else:
        notes.append("Using standard cycle time (no historical data yet)")

    # Earliest: optimistic (no changeover, immediate start)
    optimistic_start = SchedulerService._align_to_work_start(now)
    earliest_end = SimSvc._advance_work_hours(optimistic_start, production_hours * 0.9)

    # Latest: pessimistic (changeover + queue delay)
    latest_end = SimSvc._advance_work_hours(aligned_start, production_hours * 1.3)

    return DeliveryEstimateResponse(
        product_id=payload.product_id,
        quantity=payload.quantity,
        estimated_completion=estimated_end,
        confidence=confidence,
        earliest=earliest_end,
        latest=latest_end,
        notes=notes,
    )
