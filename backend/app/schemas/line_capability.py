"""LineCapabilityMatrix Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LineCapabilityCreate(BaseModel):
    """Schema for creating a line capability entry."""

    production_line_id: uuid.UUID
    equipment_type: str = Field(..., max_length=50)
    capability_params: dict[str, Any] | None = None
    throughput_range: dict[str, Any] | None = None


class LineCapabilityResponse(BaseModel):
    """Schema for line capability responses."""

    id: uuid.UUID
    production_line_id: uuid.UUID
    equipment_type: str
    capability_params: dict[str, Any] | None
    throughput_range: dict[str, Any] | None
    updated_at: datetime

    model_config = {"from_attributes": True}
