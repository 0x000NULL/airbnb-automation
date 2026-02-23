"""
User model for host accounts.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    """
    Host user account.

    Attributes:
        id: Unique identifier (UUID)
        email: Email address (unique, used for login)
        hashed_password: Bcrypt-hashed password
        name: Display name
        phone: Phone number for SMS notifications
        is_active: Whether the account is active
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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
    properties: Mapped[list["Property"]] = relationship(
        "Property",
        back_populates="host",
        lazy="selectin",
    )
    automation_config: Mapped["AutomationConfig"] = relationship(
        "AutomationConfig",
        back_populates="host",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


# Import for type hints (avoid circular imports)
from models.automation_config import AutomationConfig
from models.property import Property
