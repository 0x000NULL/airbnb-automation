"""
Property model for Airbnb/VRBO listings.
"""

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Time, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.booking import AirbnbBooking
    from models.task import Task
    from models.user import User


class Property(Base):
    """
    Rental property (Airbnb/VRBO listing).

    Attributes:
        id: Unique identifier (UUID)
        host_id: Foreign key to User
        name: Property name/title
        location: JSON with city, state, zip
        property_type: Type (apartment, house, condo, etc.)
        bedrooms: Number of bedrooms
        bathrooms: Number of bathrooms
        max_guests: Maximum guest capacity
        airbnb_listing_id: Airbnb listing identifier
        vrbo_listing_id: VRBO listing identifier
        default_checkin_time: Standard check-in time
        default_checkout_time: Standard check-out time
        cleaning_budget: Default budget for cleaning tasks
        maintenance_budget: Default budget for maintenance tasks
        preferred_skills: JSON array of preferred human skills
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    location: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="JSON: {city: str, state: str, zip: str}",
    )
    property_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="apartment",
    )
    bedrooms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    bathrooms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    max_guests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )
    airbnb_listing_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    vrbo_listing_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    ical_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="iCal feed URL for importing bookings from Airbnb/VRBO",
    )
    default_checkin_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(15, 0),  # 3:00 PM
    )
    default_checkout_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(11, 0),  # 11:00 AM
    )
    cleaning_budget: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=150.0,
    )
    maintenance_budget: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=200.0,
    )
    preferred_skills: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="JSON array of preferred skill names",
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
    host: Mapped["User"] = relationship(
        "User",
        back_populates="properties",
        lazy="selectin",
    )
    bookings: Mapped[list["AirbnbBooking"]] = relationship(
        "AirbnbBooking",
        back_populates="property",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="property",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def full_address(self) -> str:
        """Get formatted address string."""
        loc = self.location
        return f"{loc.get('city', '')}, {loc.get('state', '')} {loc.get('zip', '')}".strip()

    def __repr__(self) -> str:
        return f"<Property {self.name}>"
