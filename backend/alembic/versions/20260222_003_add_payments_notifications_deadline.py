"""Add payment_records, notifications tables and task deadline column.

Revision ID: 003
Revises: 20260222_002_add_external_id_and_updated_at
Create Date: 2026-02-22 21:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "20260222_003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Payment records table
    op.create_table(
        "payment_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.String(100), nullable=False),
        sa.Column("total_amount", sa.Float, nullable=False),
        sa.Column("commission_amount", sa.Float, nullable=False),
        sa.Column("commission_rate", sa.Float, nullable=False, server_default="0.15"),
        sa.Column("status", sa.Enum("pending", "paid", "failed", name="paymentstatus"), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", sa.Enum("info", "success", "warning", "error", name="notificationtype"), nullable=False, server_default="info"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add deadline column to tasks (Issue #10)
    op.add_column("tasks", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
    # Add completed_at column to tasks for on-time tracking
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "completed_at")
    op.drop_column("tasks", "deadline")
    op.drop_table("notifications")
    op.drop_table("payment_records")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS notificationtype")
