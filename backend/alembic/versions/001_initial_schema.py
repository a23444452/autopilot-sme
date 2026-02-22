"""Initial schema.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-02-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all initial tables."""
    # --- products ---
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("standard_cycle_time", sa.Float(), nullable=False, comment="Standard cycle time in minutes per unit"),
        sa.Column("setup_time", sa.Float(), server_default="30.0", nullable=False, comment="Setup time in minutes"),
        sa.Column("yield_rate", sa.Float(), server_default="0.95", nullable=False, comment="Expected yield rate 0-1"),
        sa.Column("learned_cycle_time", sa.Float(), nullable=True, comment="Learned cycle time from actual production data"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )

    # --- production_lines ---
    op.create_table(
        "production_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capacity_per_hour", sa.Integer(), nullable=False, comment="Units produced per hour"),
        sa.Column("efficiency_factor", sa.Float(), server_default="1.0", nullable=False, comment="Efficiency multiplier 0-1"),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("allowed_products", postgresql.JSONB(), nullable=True, comment="List of allowed product SKUs"),
        sa.Column("changeover_matrix", postgresql.JSONB(), nullable=True, comment="Product-to-product changeover times in minutes"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # --- orders ---
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("order_no", sa.String(50), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="5", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no"),
    )

    # --- order_items ---
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
    )

    # --- scheduled_jobs ---
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("production_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("changeover_time", sa.Float(), server_default="0.0", nullable=False, comment="Changeover time in minutes"),
        sa.Column("status", sa.String(20), server_default="planned", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"]),
        sa.ForeignKeyConstraint(["production_line_id"], ["production_lines.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
    )

    # --- memory_entries ---
    op.create_table(
        "memory_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("memory_type", sa.String(20), nullable=False, comment="structured, episodic, or semantic"),
        sa.Column("category", sa.String(50), nullable=False, comment="Category for grouping memories"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("importance", sa.Float(), server_default="0.5", nullable=False, comment="Importance score 0-1"),
        sa.Column("lifecycle", sa.String(20), server_default="hot", nullable=False, comment="hot, warm, or cold"),
        sa.Column("access_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- decision_logs ---
    op.create_table(
        "decision_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("decision_type", sa.String(50), nullable=False, comment="scheduling, rush_order, exception, etc."),
        sa.Column("situation", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=True, comment="Structured context data"),
        sa.Column("options_considered", postgresql.JSONB(), nullable=True, comment="List of options that were evaluated"),
        sa.Column("chosen_option", sa.Text(), nullable=True),
        sa.Column("outcome", postgresql.JSONB(), nullable=True, comment="Outcome details after decision was applied"),
        sa.Column("lessons_learned", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- model_usage_logs ---
    op.create_table(
        "model_usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, comment="anthropic, openai, or ollama"),
        sa.Column("task_type", sa.String(50), nullable=False, comment="scheduling, chat, simulation, etc."),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="success", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table("model_usage_logs")
    op.drop_table("decision_logs")
    op.drop_table("memory_entries")
    op.drop_table("scheduled_jobs")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("production_lines")
    op.drop_table("products")
