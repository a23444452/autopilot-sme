"""Add process_stations, process_routes, line_capability_matrix tables.

Revision ID: 002_process_stations_routes
Revises: 001_initial_schema
Create Date: 2026-02-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002_process_stations_routes"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create process_stations, process_routes, and line_capability_matrix."""

    # --- process_stations ---
    op.create_table(
        "process_stations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("production_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "station_order",
            sa.Integer(),
            nullable=False,
            comment="Sequence order within the production line",
        ),
        sa.Column(
            "equipment_type",
            sa.String(50),
            nullable=False,
            comment="E.g. SMT, reflow, assembly, test",
        ),
        sa.Column(
            "standard_cycle_time",
            sa.Float(),
            nullable=False,
            comment="Seconds per unit at this station",
        ),
        sa.Column(
            "actual_cycle_time",
            sa.Float(),
            nullable=True,
            comment="Observed cycle time from MES data",
        ),
        sa.Column(
            "capabilities",
            postgresql.JSONB(),
            nullable=True,
            comment="Station-specific capability parameters",
        ),
        sa.Column(
            "status", sa.String(20), server_default="active", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["production_line_id"],
            ["production_lines.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_process_stations_line_id", "process_stations", ["production_line_id"]
    )
    op.create_index(
        "ix_process_stations_equipment_type", "process_stations", ["equipment_type"]
    )

    # --- process_routes ---
    op.create_table(
        "process_routes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "version",
            sa.Integer(),
            server_default="1",
            nullable=False,
            comment="Route version; only one is_active per product",
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "steps",
            postgresql.JSONB(),
            nullable=False,
            comment="[{station_order, equipment_type, cycle_time_sec}, ...]",
        ),
        sa.Column(
            "source",
            sa.String(20),
            server_default="manual",
            nullable=False,
            comment="manual | spec_parsed | mes_learned",
        ),
        sa.Column("source_file", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_process_routes_product_id", "process_routes", ["product_id"]
    )
    op.create_index(
        "ix_process_routes_is_active", "process_routes", ["product_id", "is_active"]
    )

    # --- line_capability_matrix ---
    op.create_table(
        "line_capability_matrix",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("production_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "equipment_type",
            sa.String(50),
            nullable=False,
            comment="Equipment type this entry describes",
        ),
        sa.Column(
            "capability_params",
            postgresql.JSONB(),
            nullable=True,
            comment="Equipment-specific capability parameters",
        ),
        sa.Column(
            "throughput_range",
            postgresql.JSONB(),
            nullable=True,
            comment="Min/max throughput range",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["production_line_id"],
            ["production_lines.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_line_capability_line_equipment",
        "line_capability_matrix",
        ["production_line_id", "equipment_type"],
    )


def downgrade() -> None:
    """Drop new tables in reverse dependency order."""
    op.drop_index("ix_line_capability_line_equipment", "line_capability_matrix")
    op.drop_table("line_capability_matrix")

    op.drop_index("ix_process_routes_is_active", "process_routes")
    op.drop_index("ix_process_routes_product_id", "process_routes")
    op.drop_table("process_routes")

    op.drop_index("ix_process_stations_equipment_type", "process_stations")
    op.drop_index("ix_process_stations_line_id", "process_stations")
    op.drop_table("process_stations")
