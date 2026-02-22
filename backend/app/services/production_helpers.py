"""Shared production scheduling helpers.

Provides common utilities used by both SchedulerService and SimulatorService:
- Product/line compatibility checks
- Changeover time lookup
- Work-hour alignment and advancement
- Active production line fetching
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.production_line import ProductionLine

# Working hours configuration (sourced from Settings, configurable via env vars)
DEFAULT_WORK_START_HOUR = settings.WORK_START_HOUR
DEFAULT_WORK_END_HOUR = settings.WORK_END_HOUR
DEFAULT_HOURS_PER_DAY = DEFAULT_WORK_END_HOUR - DEFAULT_WORK_START_HOUR
DEFAULT_MAX_OVERTIME_HOURS = settings.MAX_OVERTIME_HOURS


def is_product_allowed(product_sku: str, line: ProductionLine) -> bool:
    """Check if a product is allowed on a production line."""
    if line.allowed_products is None:
        return True
    allowed = line.allowed_products
    if isinstance(allowed, list):
        return product_sku in allowed
    if isinstance(allowed, dict) and "skus" in allowed:
        return product_sku in allowed["skus"]
    return True


def get_changeover_time(
    from_sku: str | None, to_sku: str, line: ProductionLine
) -> float:
    """Get changeover time in minutes between two products on a line."""
    if from_sku is None or from_sku == to_sku:
        return 0.0

    matrix = line.changeover_matrix
    if matrix and isinstance(matrix, dict):
        key = f"{from_sku}->{to_sku}"
        if key in matrix:
            return float(matrix[key])
        reverse_key = f"{to_sku}->{from_sku}"
        if reverse_key in matrix:
            return float(matrix[reverse_key])
        if "default" in matrix:
            return float(matrix["default"])

    # Default changeover: 30 minutes
    return 30.0


async def fetch_active_lines(db: AsyncSession) -> list[ProductionLine]:
    """Fetch all active production lines."""
    result = await db.execute(
        select(ProductionLine).where(ProductionLine.status == "active")
    )
    return list(result.scalars().all())


def _skip_to_next_workday(dt: datetime) -> datetime:
    """Advance to the start of the next working day (skip weekends)."""
    result = (dt + timedelta(days=1)).replace(
        hour=DEFAULT_WORK_START_HOUR, minute=0, second=0, microsecond=0
    )
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


def align_to_work_start(dt: datetime) -> datetime:
    """Align a datetime to the next available work start time."""
    result = dt.replace(minute=0, second=0, microsecond=0)
    if result.hour < DEFAULT_WORK_START_HOUR:
        result = result.replace(hour=DEFAULT_WORK_START_HOUR)
    elif result.hour >= DEFAULT_WORK_END_HOUR:
        result = _skip_to_next_workday(result)
    # Skip weekends
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


def calculate_job_overtime(start: datetime, end: datetime) -> float:
    """Calculate overtime hours for a job spanning start to end."""
    overtime = 0.0
    current = start
    while current < end:
        day_end_regular = current.replace(
            hour=DEFAULT_WORK_END_HOUR, minute=0, second=0, microsecond=0
        )
        if current >= day_end_regular:
            next_day = _skip_to_next_workday(current)
            ot_end = min(end, next_day)
            overtime += (ot_end - current).total_seconds() / 3600.0
            current = next_day
        else:
            current = min(end, day_end_regular)
    return max(overtime, 0.0)


def advance_work_hours(start: datetime, hours: float) -> datetime:
    """Advance a datetime by a number of working hours, respecting work schedule."""
    remaining = hours
    current = start

    while remaining > 0:
        # Normalize: skip to work start if before hours or on weekend
        if current.hour >= DEFAULT_WORK_END_HOUR:
            current = _skip_to_next_workday(current)

        if current.hour < DEFAULT_WORK_START_HOUR:
            current = current.replace(
                hour=DEFAULT_WORK_START_HOUR, minute=0, second=0, microsecond=0
            )

        while current.weekday() >= 5:
            current += timedelta(days=1)

        day_end = current.replace(
            hour=DEFAULT_WORK_END_HOUR, minute=0, second=0, microsecond=0
        )
        available = (day_end - current).total_seconds() / 3600.0

        if available <= 0:
            current = _skip_to_next_workday(current)
            continue

        if remaining <= available:
            current = current + timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= available
            current = _skip_to_next_workday(current)

    return current
