"""
Booking log model for transaction auditing.

Tracks all booking-related events for debugging,
auditing, and analytics purposes.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class BookingLogEvent(str, Enum):
    """Types of booking events."""

    SEARCH_INITIATED = "search_initiated"
    SEARCH_COMPLETED = "search_completed"
    BOOKING_ATTEMPTED = "booking_attempted"
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_FAILED = "booking_failed"
    BOOKING_CANCELLED = "booking_cancelled"
    CANCELLATION_RECEIVED = "cancellation_received"
    REPLACEMENT_SEARCH = "replacement_search"
    REPLACEMENT_FOUND = "replacement_found"
    REPLACEMENT_FAILED = "replacement_failed"
    STATUS_UPDATED = "status_updated"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    FALLBACK_TRIGGERED = "fallback_triggered"
    RETRY_INITIATED = "retry_initiated"


class BookingLog(Base):
    """
    Audit log for booking-related events.

    Tracks all actions for debugging, compliance,
    and analytics purposes.
    """

    __tablename__ = "booking_logs"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Related entities
    task_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    host_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # External IDs
    rentahuman_booking_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    human_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Event details
    event: Mapped[BookingLogEvent] = mapped_column(
        SqlEnum(BookingLogEvent),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Tracking
    success: Mapped[bool | None] = mapped_column(
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    # Metadata
    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    attempt_number: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<BookingLog {self.event.value} task={self.task_id}>"
