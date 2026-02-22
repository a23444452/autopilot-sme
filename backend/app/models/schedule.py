"""ScheduledJob SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScheduledJob(Base):
    """A scheduled production job assigned to a production line."""

    __tablename__ = "scheduled_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id"),
        nullable=False,
    )
    production_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_lines.id"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=False,
    )
    planned_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    planned_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    changeover_time: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.0", comment="Changeover time in minutes"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="planned"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    order_item: Mapped["OrderItem"] = relationship()
    production_line: Mapped["ProductionLine"] = relationship()
    product: Mapped["Product"] = relationship()
