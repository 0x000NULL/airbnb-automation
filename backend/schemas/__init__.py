"""
Pydantic schemas for API request/response validation.

All schemas use Pydantic v2 syntax.
"""

from schemas.analytics import AnalyticsSummary, CostAnalysis, HumanPerformance, ROIAnalysis
from schemas.booking import BookingCreate, BookingList, BookingResponse, UpcomingBooking
from schemas.config import AutomationConfigResponse, AutomationConfigUpdate
from schemas.human import HumanList, HumanResponse, HumanSearchParams
from schemas.property import (
    PropertyCreate,
    PropertyList,
    PropertyResponse,
    PropertyUpdate,
)
from schemas.task import TaskCreate, TaskList, TaskResponse, TaskUpdate
from schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

__all__ = [
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    # Property
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyResponse",
    "PropertyList",
    # Booking
    "BookingCreate",
    "BookingResponse",
    "BookingList",
    "UpcomingBooking",
    # Task
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskList",
    # Config
    "AutomationConfigUpdate",
    "AutomationConfigResponse",
    # Human
    "HumanSearchParams",
    "HumanResponse",
    "HumanList",
    # Analytics
    "AnalyticsSummary",
    "CostAnalysis",
    "HumanPerformance",
    "ROIAnalysis",
]
