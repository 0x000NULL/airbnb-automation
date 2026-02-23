"""Add ical_url to properties

Revision ID: 004
Revises: 003
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column(
            "ical_url",
            sa.String(length=1024),
            nullable=True,
            comment="iCal feed URL for importing bookings from Airbnb/VRBO",
        ),
    )


def downgrade() -> None:
    op.drop_column("properties", "ical_url")
