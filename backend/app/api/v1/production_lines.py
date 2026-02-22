"""Production Lines CRUD API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.production_line import ProductionLine
from app.schemas.production_line import ProductionLineCreate, ProductionLineResponse

router = APIRouter(prefix="/production-lines", tags=["production-lines"])


@router.get("", response_model=list[ProductionLineResponse])
async def list_production_lines(
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ProductionLine]:
    """List production lines with optional status filter and pagination."""
    query = select(ProductionLine)

    if status_filter is not None:
        query = query.where(ProductionLine.status == status_filter)

    query = query.order_by(ProductionLine.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=ProductionLineResponse, status_code=status.HTTP_201_CREATED)
async def create_production_line(
    payload: ProductionLineCreate,
    db: AsyncSession = Depends(get_db),
) -> ProductionLine:
    """Create a new production line."""
    line = ProductionLine(
        name=payload.name,
        description=payload.description,
        capacity_per_hour=payload.capacity_per_hour,
        efficiency_factor=payload.efficiency_factor,
        status=payload.status,
        allowed_products=payload.allowed_products,
        changeover_matrix=payload.changeover_matrix,
    )
    db.add(line)
    await db.flush()
    await db.refresh(line)
    return line


@router.get("/{line_id}", response_model=ProductionLineResponse)
async def get_production_line(
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProductionLine:
    """Get a single production line by ID."""
    result = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=404, detail="Production line not found")
    return line


@router.put("/{line_id}", response_model=ProductionLineResponse)
async def update_production_line(
    line_id: uuid.UUID,
    payload: ProductionLineCreate,
    db: AsyncSession = Depends(get_db),
) -> ProductionLine:
    """Update an existing production line."""
    result = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=404, detail="Production line not found")

    line.name = payload.name
    line.description = payload.description
    line.capacity_per_hour = payload.capacity_per_hour
    line.efficiency_factor = payload.efficiency_factor
    line.status = payload.status
    line.allowed_products = payload.allowed_products
    line.changeover_matrix = payload.changeover_matrix

    await db.flush()
    await db.refresh(line)
    return line


@router.delete("/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_line(
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a production line."""
    result = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=404, detail="Production line not found")
    await db.delete(line)
