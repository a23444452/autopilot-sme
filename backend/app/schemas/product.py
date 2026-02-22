"""Product Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Schema for creating a product."""

    sku: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    description: str | None = None
    standard_cycle_time: float = Field(..., gt=0, description="Cycle time in minutes per unit")
    setup_time: float = Field(default=30.0, ge=0, description="Setup time in minutes")
    yield_rate: float = Field(default=0.95, gt=0, le=1, description="Expected yield rate 0-1")


class ProductResponse(BaseModel):
    """Schema for product responses."""

    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    standard_cycle_time: float
    setup_time: float
    yield_rate: float
    learned_cycle_time: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
