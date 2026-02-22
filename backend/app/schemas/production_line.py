"""ProductionLine Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProductionLineCreate(BaseModel):
    """Schema for creating a production line."""

    name: str = Field(..., max_length=100)
    description: str | None = None
    capacity_per_hour: int = Field(..., gt=0)
    efficiency_factor: float = Field(default=1.0, gt=0, le=1)
    status: str = Field(default="active", max_length=20)
    allowed_products: list[str] | None = None
    changeover_matrix: dict[str, Any] | None = None


class ProductionLineResponse(BaseModel):
    """Schema for production line responses."""

    id: uuid.UUID
    name: str
    description: str | None
    capacity_per_hour: int
    efficiency_factor: float
    status: str
    allowed_products: list[str] | None
    changeover_matrix: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
