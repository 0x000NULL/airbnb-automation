"""
Task model for automated property management tasks.
"""

import enum
import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Time, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.booking import AirbnbBooking
    from models.property import Property


class TaskType(str, enum.Enum):
    """Type of property management task."""

    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"
    PHOTOGRAPHY = "photography"
    COMMUNICATION = "communication"
    RESTOCKING = "restocking"


class TaskStatus(str, enum.Enum):
    """Status of a task in the automation pipeline."""

    PENDING = "pending"
    HUMAN_BOOKED = "human_booked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    """
    Property management task (auto-generated or manual).

    Attributes:
        id: Unique identifier (UUID)
        type: Task type (cleaning, maintenance, etc.)
        property_id: Foreign key to Property
        airbnb_booking_id: Optional foreign key to Booking
        description: Task description
        required_skills: JSON array of required skills
        budget: Budget for this task
        scheduled_date: Date the task should be performed
        scheduled_time: Time the task should start
        duration_hours: Expected duration in hours
        status: Current task status
        rentahuman_booking_id: RentAHuman booking ID (if booked)
        assigned_human: JSON with human details (name, photo, rating)
        checklist: JSON array of checklist items
        photo_upload_url: S3 URL for completion photos
        host_notes: Notes from the host
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    type: Mapped[TaskType] = mapped_column(
        Enum(TaskType),
        nullable=False,
        index=True,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    airbnb_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    required_skills: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="JSON array of required skill names",
    )
    budget: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
    )
    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    scheduled_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    duration_hours: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=2.0,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
    )
    rentahuman_booking_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    assigned_human: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON: {id, name, photo, rating, reviews}",
    )
    checklist: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="JSON array of checklist items",
    )
    photo_upload_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    host_notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Task deadline for on-time tracking",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the task was actually completed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    property: Mapped["Property"] = relationship(
        "Property",
        back_populates="tasks",
        lazy="selectin",
    )
    booking: Mapped["AirbnbBooking | None"] = relationship(
        "AirbnbBooking",
        back_populates="tasks",
        lazy="selectin",
    )

    @property
    def is_urgent(self) -> bool:
        """Check if task is urgent (scheduled within 24 hours)."""
        from datetime import datetime, timedelta

        scheduled_datetime = datetime.combine(self.scheduled_date, self.scheduled_time)
        return scheduled_datetime - datetime.now() < timedelta(hours=24)

    def __repr__(self) -> str:
        return f"<Task {self.type.value} @ {self.scheduled_date}>"
