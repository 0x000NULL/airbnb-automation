"""Initial migration - create all tables

Revision ID: 001
Revises:
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Create properties table
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "location",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="JSON: {city: str, state: str, zip: str}",
        ),
        sa.Column("property_type", sa.String(50), nullable=False, default="apartment"),
        sa.Column("bedrooms", sa.Integer(), nullable=False, default=1),
        sa.Column("bathrooms", sa.Integer(), nullable=False, default=1),
        sa.Column("max_guests", sa.Integer(), nullable=False, default=2),
        sa.Column("airbnb_listing_id", sa.String(100), nullable=True),
        sa.Column("vrbo_listing_id", sa.String(100), nullable=True),
        sa.Column("default_checkin_time", sa.Time(), nullable=False),
        sa.Column("default_checkout_time", sa.Time(), nullable=False),
        sa.Column("cleaning_budget", sa.Float(), nullable=False, default=150.0),
        sa.Column("maintenance_budget", sa.Float(), nullable=False, default=200.0),
        sa.Column(
            "preferred_skills",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="JSON array of preferred skill names",
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
        sa.ForeignKeyConstraint(
            ["host_id"],
            ["users.id"],
            name=op.f("fk_properties_host_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_properties")),
    )
    op.create_index(op.f("ix_properties_host_id"), "properties", ["host_id"])
    op.create_index(
        op.f("ix_properties_airbnb_listing_id"), "properties", ["airbnb_listing_id"]
    )
    op.create_index(
        op.f("ix_properties_vrbo_listing_id"), "properties", ["vrbo_listing_id"]
    )

    # Create bookings table
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guest_name", sa.String(255), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("checkout_date", sa.Date(), nullable=False),
        sa.Column("guest_count", sa.Integer(), nullable=False, default=1),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("total_price", sa.Float(), nullable=False, default=0.0),
        sa.Column(
            "source",
            sa.Enum("airbnb", "vrbo", name="bookingsource"),
            nullable=False,
            default="airbnb",
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_bookings_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
    )
    op.create_index(op.f("ix_bookings_property_id"), "bookings", ["property_id"])
    op.create_index(op.f("ix_bookings_checkin_date"), "bookings", ["checkin_date"])
    op.create_index(op.f("ix_bookings_checkout_date"), "bookings", ["checkout_date"])

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "cleaning",
                "maintenance",
                "photography",
                "communication",
                "restocking",
                name="tasktype",
            ),
            nullable=False,
        ),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("airbnb_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column(
            "required_skills",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="JSON array of required skill names",
        ),
        sa.Column("budget", sa.Float(), nullable=False, default=100.0),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=False),
        sa.Column("duration_hours", sa.Float(), nullable=False, default=2.0),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "human_booked",
                "in_progress",
                "completed",
                "failed",
                name="taskstatus",
            ),
            nullable=False,
            default="pending",
        ),
        sa.Column("rentahuman_booking_id", sa.String(100), nullable=True),
        sa.Column(
            "assigned_human",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="JSON: {id, name, photo, rating, reviews}",
        ),
        sa.Column(
            "checklist",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="JSON array of checklist items",
        ),
        sa.Column("photo_upload_url", sa.String(500), nullable=True),
        sa.Column("host_notes", sa.String(1000), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_tasks_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["airbnb_booking_id"],
            ["bookings.id"],
            name=op.f("fk_tasks_airbnb_booking_id_bookings"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index(op.f("ix_tasks_type"), "tasks", ["type"])
    op.create_index(op.f("ix_tasks_property_id"), "tasks", ["property_id"])
    op.create_index(op.f("ix_tasks_airbnb_booking_id"), "tasks", ["airbnb_booking_id"])
    op.create_index(op.f("ix_tasks_scheduled_date"), "tasks", ["scheduled_date"])
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"])
    op.create_index(
        op.f("ix_tasks_rentahuman_booking_id"), "tasks", ["rentahuman_booking_id"]
    )

    # Create automation_configs table
    op.create_table(
        "automation_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auto_book_cleaning", sa.Boolean(), nullable=False, default=True),
        sa.Column("auto_book_maintenance", sa.Boolean(), nullable=False, default=True),
        sa.Column("auto_book_photography", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "auto_respond_to_guests", sa.Boolean(), nullable=False, default=False
        ),
        sa.Column(
            "cleaning_preference",
            sa.Enum("nearest", "cheapest", "highest_rated", name="humanpreference"),
            nullable=False,
            default="highest_rated",
        ),
        sa.Column(
            "maintenance_preference",
            sa.Enum("nearest", "cheapest", "highest_rated", name="humanpreference"),
            nullable=False,
            default="nearest",
        ),
        sa.Column("minimum_human_rating", sa.Float(), nullable=False, default=4.0),
        sa.Column("max_booking_lead_time_days", sa.Integer(), nullable=False, default=3),
        sa.Column(
            "notification_method",
            sa.Enum("email", "sms", "push", name="notificationmethod"),
            nullable=False,
            default="email",
        ),
        sa.ForeignKeyConstraint(
            ["host_id"],
            ["users.id"],
            name=op.f("fk_automation_configs_host_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_automation_configs")),
        sa.UniqueConstraint("host_id", name=op.f("uq_automation_configs_host_id")),
    )
    op.create_index(
        op.f("ix_automation_configs_host_id"), "automation_configs", ["host_id"]
    )


def downgrade() -> None:
    op.drop_table("automation_configs")
    op.drop_table("tasks")
    op.drop_table("bookings")
    op.drop_table("properties")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS notificationmethod")
    op.execute("DROP TYPE IF EXISTS humanpreference")
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS tasktype")
    op.execute("DROP TYPE IF EXISTS bookingsource")
