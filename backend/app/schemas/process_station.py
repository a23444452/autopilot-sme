"""ProcessStation Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProcessStationCreate(BaseModel):
    """Schema for creating a process station."""

    production_line_id: uuid.UUID
    name: str = Field(..., max_length=100)
    station_order: int = Field(..., ge=1, description="Sequence order on the line")
    equipment_type: str = Field(..., max_length=50)
    standard_cycle_time: float = Field(..., gt=0, description="Seconds per unit")
    actual_cycle_time: float | None = Field(None, gt=0)
    capabilities: dict[str, Any] | None = None
    status: str = Field(default="active", max_length=20)


class ProcessStationResponse(BaseModel):
    """Schema for process station responses."""

    id: uuid.UUID
    production_line_id: uuid.UUID
    name: str
    station_order: int
    equipment_type: str
    standard_cycle_time: float
    actual_cycle_time: float | None
    capabilities: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
