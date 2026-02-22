"""Chat Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Schema for a chat message request."""

    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Schema for a chat message response."""

    reply: str
    conversation_id: str
    sources: list[str] = Field(default_factory=list, description="Referenced data sources")
    suggestions: list[str] = Field(default_factory=list, description="Follow-up suggestions")
    metadata: dict[str, Any] = Field(default_factory=dict)
