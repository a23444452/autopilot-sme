"""MemoryEntry and DecisionLog SQLAlchemy models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MemoryEntry(Base):
    """Three-tier memory system entry (structured/episodic/semantic)."""

    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    memory_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="structured, episodic, or semantic"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Category for grouping memories"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    importance: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.5", comment="Importance score 0-1"
    )
    lifecycle: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="hot", comment="hot, warm, or cold"
    )
    access_count: Mapped[int] = mapped_column(
        nullable=False, server_default="0"
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DecisionLog(Base):
    """Episodic memory: records of AI-assisted decisions."""

    __tablename__ = "decision_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    decision_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="scheduling, rush_order, exception, etc."
    )
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Structured context data"
    )
    options_considered: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="List of options that were evaluated"
    )
    chosen_option: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Outcome details after decision was applied"
    )
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
