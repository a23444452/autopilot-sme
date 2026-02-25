"""LineCapabilityMatrix SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LineCapabilityMatrix(Base):
    """Maps equipment types on a line to their capability parameters."""

    __tablename__ = "line_capability_matrix"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    production_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Equipment type this entry describes"
    )
    capability_params: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Equipment-specific capability parameters"
    )
    throughput_range: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Min/max throughput range"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
