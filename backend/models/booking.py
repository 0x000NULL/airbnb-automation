"""
Booking model for Airbnb/VRBO reservations.
"""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.property import Property
    from models.task import Task


class BookingSource(str, enum.Enum):
    """Source platform for the booking."""

    AIRBNB = "airbnb"
    VRBO = "vrbo"


class AirbnbBooking(Base):
    """
    Guest booking/reservation from Airbnb or VRBO.

    Attributes:
        id: Unique identifier (UUID)
        property_id: Foreign key to Property
        guest_name: Guest's name
        checkin_date: Check-in date
        checkout_date: Check-out date
        guest_count: Number of guests
        notes: Special requests or notes
        total_price: Total booking price
        source: Booking source (AIRBNB or VRBO)
        synced_at: Last sync timestamp from source platform
    """

    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="External ID from Airbnb/VRBO for deduplication",
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    guest_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    checkin_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    checkout_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    guest_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    total_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    source: Mapped[BookingSource] = mapped_column(
        Enum(BookingSource),
        nullable=False,
        default=BookingSource.AIRBNB,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    property_rel: Mapped["Property"] = relationship(
        "Property",
        back_populates="bookings",
        lazy="selectin",
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="booking",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def duration_nights(self) -> int:
        """Calculate number of nights for the booking."""
        return (self.checkout_date - self.checkin_date).days

    def __repr__(self) -> str:
        return f"<Booking {self.guest_name} @ {self.checkin_date}>"
