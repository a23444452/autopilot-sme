"""Process Stations CRUD API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.process_station import ProcessStation
from app.schemas.process_station import ProcessStationCreate, ProcessStationResponse

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[ProcessStationResponse])
async def list_stations(
    production_line_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ProcessStation]:
    """List process stations, optionally filtered by production_line_id."""
    query = select(ProcessStation)

    if production_line_id is not None:
        query = query.where(ProcessStation.production_line_id == production_line_id)

    query = query.order_by(ProcessStation.station_order).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=ProcessStationResponse, status_code=status.HTTP_201_CREATED)
async def create_station(
    payload: ProcessStationCreate,
    db: AsyncSession = Depends(get_db),
) -> ProcessStation:
    """Create a new process station."""
    station = ProcessStation(
        production_line_id=payload.production_line_id,
        name=payload.name,
        station_order=payload.station_order,
        equipment_type=payload.equipment_type,
        standard_cycle_time=payload.standard_cycle_time,
        actual_cycle_time=payload.actual_cycle_time,
        capabilities=payload.capabilities,
        status=payload.status,
    )
    db.add(station)
    await db.flush()
    await db.refresh(station)
    return station


@router.get("/{station_id}", response_model=ProcessStationResponse)
async def get_station(
    station_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProcessStation:
    """Get a single process station by ID."""
    result = await db.execute(select(ProcessStation).where(ProcessStation.id == station_id))
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(status_code=404, detail="Process station not found")
    return station


@router.put("/{station_id}", response_model=ProcessStationResponse)
async def update_station(
    station_id: uuid.UUID,
    payload: ProcessStationCreate,
    db: AsyncSession = Depends(get_db),
) -> ProcessStation:
    """Update an existing process station."""
    result = await db.execute(select(ProcessStation).where(ProcessStation.id == station_id))
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(status_code=404, detail="Process station not found")

    station.production_line_id = payload.production_line_id
    station.name = payload.name
    station.station_order = payload.station_order
    station.equipment_type = payload.equipment_type
    station.standard_cycle_time = payload.standard_cycle_time
    station.actual_cycle_time = payload.actual_cycle_time
    station.capabilities = payload.capabilities
    station.status = payload.status

    await db.flush()
    await db.refresh(station)
    return station


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(
    station_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a process station."""
    result = await db.execute(select(ProcessStation).where(ProcessStation.id == station_id))
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(status_code=404, detail="Process station not found")
    await db.delete(station)
