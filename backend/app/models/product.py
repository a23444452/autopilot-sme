"""Product SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    """Product master data."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_cycle_time: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Standard cycle time in minutes per unit"
    )
    setup_time: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="30.0", comment="Setup time in minutes"
    )
    yield_rate: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.95", comment="Expected yield rate 0-1"
    )
    learned_cycle_time: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Learned cycle time from actual production data"
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
