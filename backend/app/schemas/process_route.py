"""ProcessRoute Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


RouteSource = Literal["manual", "spec_parsed", "mes_learned"]


class ProcessRouteCreate(BaseModel):
    """Schema for creating a process route."""

    product_id: uuid.UUID
    version: int = Field(default=1, ge=1)
    is_active: bool = True
    steps: list[dict[str, Any]] = Field(
        ..., min_length=1, description="Ordered list of process steps"
    )
    source: RouteSource = "manual"
    source_file: str | None = Field(None, max_length=255)


class ProcessRouteResponse(BaseModel):
    """Schema for process route responses."""

    id: uuid.UUID
    product_id: uuid.UUID
    version: int
    is_active: bool
    steps: list[dict[str, Any]]
    source: str
    source_file: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
