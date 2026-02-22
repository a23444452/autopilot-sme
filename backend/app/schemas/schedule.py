"""Schedule Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ScheduleRequest(BaseModel):
    """Schema for requesting schedule generation."""

    order_ids: list[uuid.UUID] = Field(default_factory=list, description="Specific orders to schedule; empty means all pending")
    horizon_days: int = Field(default=7, ge=1, le=90, description="Planning horizon in days")
    strategy: str = Field(default="balanced", description="Scheduling strategy: balanced, rush, or efficiency")


class ScheduledJobResponse(BaseModel):
    """Schema for a scheduled job response."""

    id: uuid.UUID
    order_item_id: uuid.UUID
    production_line_id: uuid.UUID
    product_id: uuid.UUID
    planned_start: datetime
    planned_end: datetime
    quantity: int
    changeover_time: float
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleResult(BaseModel):
    """Schema for schedule generation results."""

    jobs: list[ScheduledJobResponse] = Field(default_factory=list)
    total_jobs: int = 0
    total_changeover_minutes: float = 0.0
    utilization_pct: float = Field(default=0.0, description="Average line utilization percentage")
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
