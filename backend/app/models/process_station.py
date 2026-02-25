"""ProcessStation SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcessStation(Base):
    """A physical workstation on a production line."""

    __tablename__ = "process_stations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    production_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    station_order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Sequence order within the production line"
    )
    equipment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="E.g. SMT, reflow, assembly, test"
    )
    standard_cycle_time: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Seconds per unit at this station"
    )
    actual_cycle_time: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Observed cycle time from MES data"
    )
    capabilities: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Station-specific capability parameters"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
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
