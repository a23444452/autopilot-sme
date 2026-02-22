"""Memory API endpoints for semantic search and structured knowledge."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.qdrant import get_qdrant
from app.schemas.memory import (
    DecisionLogResponse,
    MemoryEntryResponse,
    MemorySearch,
)
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


def _get_memory_service(
    db: AsyncSession = Depends(get_db),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
) -> MemoryService:
    """Dependency to construct a MemoryService."""
    return MemoryService(db=db, qdrant=qdrant)


@router.post("/search", response_model=list[dict[str, Any]])
async def search_memories(
    payload: MemorySearch,
    svc: MemoryService = Depends(_get_memory_service),
) -> list[dict[str, Any]]:
    """Semantic search over memories using vector similarity."""
    return await svc.search_memories(
        query=payload.query,
        memory_type=payload.memory_type,
        category=payload.category,
        limit=payload.limit,
    )


@router.get("/facts", response_model=list[MemoryEntryResponse])
async def list_facts(
    memory_type: str | None = Query(None),
    category: str | None = Query(None),
    lifecycle: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    svc: MemoryService = Depends(_get_memory_service),
) -> list[Any]:
    """List structured knowledge / memory entries with optional filters."""
    return await svc.list_memories(
        memory_type=memory_type,
        category=category,
        lifecycle=lifecycle,
        limit=limit,
        offset=skip,
    )


@router.put("/facts", response_model=MemoryEntryResponse)
async def create_fact(
    memory_type: str = Query("structured"),
    category: str = Query("general"),
    content: str = Query(..., min_length=1),
    svc: MemoryService = Depends(_get_memory_service),
) -> Any:
    """Create a new structured knowledge entry."""
    return await svc.create_memory(
        memory_type=memory_type,
        category=category,
        content=content,
    )
