"""ProductionLine SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductionLine(Base):
    """Manufacturing production line."""

    __tablename__ = "production_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity_per_hour: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Units produced per hour"
    )
    efficiency_factor: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0", comment="Efficiency multiplier 0-1"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    allowed_products: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="List of allowed product SKUs"
    )
    changeover_matrix: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Product-to-product changeover times in minutes",
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
