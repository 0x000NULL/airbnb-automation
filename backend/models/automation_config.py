"""
Automation configuration model for host preferences.
"""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User


class HumanPreference(str, enum.Enum):
    """Preference for selecting humans."""

    NEAREST = "nearest"
    CHEAPEST = "cheapest"
    HIGHEST_RATED = "highest_rated"


class NotificationMethod(str, enum.Enum):
    """Notification delivery method."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class AutomationConfig(Base):
    """
    Host's automation configuration and preferences.

    Attributes:
        id: Unique identifier (UUID)
        host_id: Foreign key to User (unique - one config per host)
        auto_book_cleaning: Auto-book cleaning tasks
        auto_book_maintenance: Auto-book maintenance tasks
        auto_book_photography: Auto-book photography tasks
        auto_respond_to_guests: Auto-respond to guest messages
        cleaning_preference: Preference for selecting cleaners
        maintenance_preference: Preference for selecting maintenance workers
        minimum_human_rating: Minimum acceptable human rating
        max_booking_lead_time_days: Max days ahead to book humans
        notification_method: How to notify host of updates
    """

    __tablename__ = "automation_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    auto_book_cleaning: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    auto_book_maintenance: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    auto_book_photography: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    auto_respond_to_guests: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    cleaning_preference: Mapped[HumanPreference] = mapped_column(
        Enum(HumanPreference),
        nullable=False,
        default=HumanPreference.HIGHEST_RATED,
    )
    maintenance_preference: Mapped[HumanPreference] = mapped_column(
        Enum(HumanPreference),
        nullable=False,
        default=HumanPreference.NEAREST,
    )
    minimum_human_rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=4.0,
    )
    max_booking_lead_time_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    notification_method: Mapped[NotificationMethod] = mapped_column(
        Enum(NotificationMethod),
        nullable=False,
        default=NotificationMethod.EMAIL,
    )

    # Relationships
    host: Mapped["User"] = relationship(
        "User",
        back_populates="automation_config",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AutomationConfig for host {self.host_id}>"
