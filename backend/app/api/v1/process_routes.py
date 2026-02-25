"""Process Routes CRUD API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.process_route import ProcessRoute
from app.schemas.process_route import ProcessRouteCreate, ProcessRouteResponse

router = APIRouter(prefix="/process-routes", tags=["process-routes"])


@router.get("", response_model=list[ProcessRouteResponse])
async def list_process_routes(
    product_id: uuid.UUID | None = Query(None),
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ProcessRoute]:
    """List process routes, optionally filtered by product_id and active status."""
    query = select(ProcessRoute)

    if product_id is not None:
        query = query.where(ProcessRoute.product_id == product_id)

    if active_only:
        query = query.where(ProcessRoute.is_active.is_(True))

    query = query.order_by(ProcessRoute.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=ProcessRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_process_route(
    payload: ProcessRouteCreate,
    db: AsyncSession = Depends(get_db),
) -> ProcessRoute:
    """Create a new process route.

    Automatically deactivates any existing active routes for the same product
    to maintain the invariant: one active route per product.
    """
    await db.execute(
        update(ProcessRoute)
        .where(ProcessRoute.product_id == payload.product_id, ProcessRoute.is_active.is_(True))
        .values(is_active=False)
    )

    route = ProcessRoute(
        product_id=payload.product_id,
        version=payload.version,
        is_active=payload.is_active,
        steps=payload.steps,
        source=payload.source,
        source_file=payload.source_file,
    )
    db.add(route)
    await db.flush()
    await db.refresh(route)
    return route


@router.get("/{route_id}", response_model=ProcessRouteResponse)
async def get_process_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProcessRoute:
    """Get a single process route by ID."""
    result = await db.execute(select(ProcessRoute).where(ProcessRoute.id == route_id))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Process route not found")
    return route


@router.put("/{route_id}", response_model=ProcessRouteResponse)
async def update_process_route(
    route_id: uuid.UUID,
    payload: ProcessRouteCreate,
    db: AsyncSession = Depends(get_db),
) -> ProcessRoute:
    """Update an existing process route."""
    result = await db.execute(select(ProcessRoute).where(ProcessRoute.id == route_id))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Process route not found")

    route.product_id = payload.product_id
    route.version = payload.version
    route.is_active = payload.is_active
    route.steps = payload.steps
    route.source = payload.source
    route.source_file = payload.source_file

    await db.flush()
    await db.refresh(route)
    return route


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a process route."""
    result = await db.execute(select(ProcessRoute).where(ProcessRoute.id == route_id))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Process route not found")
    await db.delete(route)
