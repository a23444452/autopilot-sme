"""Line Capabilities CRUD and product-to-line matching API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.line_capability import LineCapabilityMatrix
from app.models.production_line import ProductionLine
from app.schemas.line_capability import LineCapabilityCreate, LineCapabilityResponse

router = APIRouter(tags=["matching"])

# --- Line Capabilities CRUD ---

capabilities_router = APIRouter(prefix="/line-capabilities", tags=["line-capabilities"])


@capabilities_router.get("", response_model=list[LineCapabilityResponse])
async def list_line_capabilities(
    production_line_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[LineCapabilityMatrix]:
    """List line capabilities, optionally filtered by production_line_id."""
    query = select(LineCapabilityMatrix)

    if production_line_id is not None:
        query = query.where(LineCapabilityMatrix.production_line_id == production_line_id)

    query = query.order_by(LineCapabilityMatrix.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@capabilities_router.post("", response_model=LineCapabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_line_capability(
    payload: LineCapabilityCreate,
    db: AsyncSession = Depends(get_db),
) -> LineCapabilityMatrix:
    """Create a new line capability entry."""
    cap = LineCapabilityMatrix(
        production_line_id=payload.production_line_id,
        equipment_type=payload.equipment_type,
        capability_params=payload.capability_params,
        throughput_range=payload.throughput_range,
    )
    db.add(cap)
    await db.flush()
    await db.refresh(cap)
    return cap


@capabilities_router.get("/{capability_id}", response_model=LineCapabilityResponse)
async def get_line_capability(
    capability_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LineCapabilityMatrix:
    """Get a single line capability by ID."""
    result = await db.execute(
        select(LineCapabilityMatrix).where(LineCapabilityMatrix.id == capability_id)
    )
    cap = result.scalar_one_or_none()
    if cap is None:
        raise HTTPException(status_code=404, detail="Line capability not found")
    return cap


@capabilities_router.delete("/{capability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_line_capability(
    capability_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a line capability entry."""
    result = await db.execute(
        select(LineCapabilityMatrix).where(LineCapabilityMatrix.id == capability_id)
    )
    cap = result.scalar_one_or_none()
    if cap is None:
        raise HTTPException(status_code=404, detail="Line capability not found")
    await db.delete(cap)


# --- Product-to-Line Matching ---

matching_router = APIRouter(prefix="/matching", tags=["matching"])


@matching_router.get("/product-lines")
async def match_product_to_lines(
    product_id: uuid.UUID = Query(...),
    equipment_types: list[str] = Query(..., alias="equipment_types"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Find active production lines that support ALL required equipment types.

    Returns lines where the line_capability_matrix contains entries
    covering every requested equipment type.
    """
    lines_result = await db.execute(
        select(ProductionLine).where(ProductionLine.status == "active")
    )
    active_lines = list(lines_result.scalars().all())

    matched: list[dict] = []
    required_set = set(equipment_types)

    for line in active_lines:
        caps_result = await db.execute(
            select(LineCapabilityMatrix.equipment_type).where(
                LineCapabilityMatrix.production_line_id == line.id
            )
        )
        line_types = {row[0] for row in caps_result.all()}

        if required_set.issubset(line_types):
            matched.append({
                "production_line_id": str(line.id),
                "name": line.name,
                "matched_types": sorted(required_set & line_types),
                "all_types": sorted(line_types),
            })

    return matched


# Combine into a single router for registration
router.include_router(capabilities_router)
router.include_router(matching_router)
