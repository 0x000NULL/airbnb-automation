"""
Database models for Airbnb/VRBO Hosting Automation.

All models use SQLAlchemy 2.0 style with mapped_column().
"""

from models.automation_config import AutomationConfig, HumanPreference, NotificationMethod
from models.booking import AirbnbBooking, BookingSource
from models.booking_log import BookingLog, BookingLogEvent
from models.property import Property
from models.task import Task, TaskStatus, TaskType
from models.user import User

__all__ = [
    # User
    "User",
    # Property
    "Property",
    # Booking
    "AirbnbBooking",
    "BookingSource",
    # Task
    "Task",
    "TaskType",
    "TaskStatus",
    # Config
    "AutomationConfig",
    "HumanPreference",
    "NotificationMethod",
    # Audit
    "BookingLog",
    "BookingLogEvent",
]
