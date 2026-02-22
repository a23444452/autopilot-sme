"""Memory Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemorySearch(BaseModel):
    """Schema for searching memories."""

    query: str = Field(..., min_length=1, max_length=1000)
    memory_type: str | None = Field(default=None, description="Filter by type: structured, episodic, or semantic")
    category: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class CreateFactRequest(BaseModel):
    """Schema for creating a structured knowledge entry."""

    memory_type: str = Field(default="structured", description="Memory type: structured, episodic, or semantic")
    category: str = Field(default="general", description="Category of the memory entry")
    content: str = Field(..., min_length=1, max_length=5000, description="Content of the memory entry")


class MemoryEntryResponse(BaseModel):
    """Schema for memory entry responses."""

    id: uuid.UUID
    memory_type: str
    category: str
    content: str
    metadata: dict[str, Any] | None
    importance: float
    lifecycle: str
    access_count: int
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DecisionLogResponse(BaseModel):
    """Schema for decision log responses."""

    id: uuid.UUID
    decision_type: str
    situation: str
    context: dict[str, Any] | None
    options_considered: dict[str, Any] | None
    chosen_option: str | None
    outcome: dict[str, Any] | None
    lessons_learned: str | None
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}
