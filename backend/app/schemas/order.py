"""Order and OrderItem Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    """Schema for creating an order item."""

    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    """Schema for order item responses."""

    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    """Schema for creating an order."""

    order_no: str = Field(..., max_length=50)
    customer_name: str = Field(..., max_length=200)
    due_date: datetime
    priority: int = Field(default=5, ge=1, le=5)
    notes: str | None = None
    items: list[OrderItemCreate] = Field(default_factory=list)


class OrderResponse(BaseModel):
    """Schema for order responses."""

    id: uuid.UUID
    order_no: str
    customer_name: str
    due_date: datetime
    priority: int
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
