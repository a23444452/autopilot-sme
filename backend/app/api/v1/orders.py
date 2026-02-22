"""Orders CRUD API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    due_date_from: datetime | None = Query(None),
    due_date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[Order]:
    """List orders with optional status/date filters and pagination."""
    query = select(Order).options(selectinload(Order.items))

    if status_filter is not None:
        query = query.where(Order.status == status_filter)
    if due_date_from is not None:
        query = query.where(Order.due_date >= due_date_from)
    if due_date_to is not None:
        query = query.where(Order.due_date <= due_date_to)

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Create a new order with optional line items."""
    order = Order(
        order_no=payload.order_no,
        customer_name=payload.customer_name,
        due_date=payload.due_date,
        priority=payload.priority,
        notes=payload.notes,
    )
    for item in payload.items:
        order.items.append(
            OrderItem(product_id=item.product_id, quantity=item.quantity)
        )
    db.add(order)
    await db.flush()
    await db.refresh(order, attribute_names=["items"])
    return order


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Get a single order by ID."""
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: uuid.UUID,
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Update an existing order, replacing its items."""
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order.order_no = payload.order_no
    order.customer_name = payload.customer_name
    order.due_date = payload.due_date
    order.priority = payload.priority
    order.notes = payload.notes

    # Replace items
    order.items.clear()
    for item in payload.items:
        order.items.append(
            OrderItem(product_id=item.product_id, quantity=item.quantity)
        )

    await db.flush()
    await db.refresh(order, attribute_names=["items"])
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an order and its items."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
