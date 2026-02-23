"""Add external_id to bookings and updated_at to users

Revision ID: 002
Revises: 001
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add external_id column to bookings table for Airbnb/VRBO deduplication
    op.add_column(
        "bookings",
        sa.Column(
            "external_id",
            sa.String(100),
            nullable=True,
            comment="External ID from Airbnb/VRBO for deduplication",
        ),
    )
    op.create_index(
        op.f("ix_bookings_external_id"),
        "bookings",
        ["external_id"],
    )

    # Add updated_at column to users table
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Remove updated_at from users
    op.drop_column("users", "updated_at")

    # Remove external_id from bookings
    op.drop_index(op.f("ix_bookings_external_id"), table_name="bookings")
    op.drop_column("bookings", "external_id")
