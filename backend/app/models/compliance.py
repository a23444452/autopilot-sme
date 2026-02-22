"""ModelUsageLog SQLAlchemy model for compliance tracking."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelUsageLog(Base):
    """Tracks every LLM model call for compliance and cost analysis."""

    __tablename__ = "model_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="anthropic, openai, or ollama"
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="scheduling, chat, simulation, etc."
    )
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.0"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="success"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
