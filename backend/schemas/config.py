"""
Automation configuration Pydantic schemas.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.automation_config import HumanPreference, NotificationMethod


class AutomationConfigUpdate(BaseModel):
    """Schema for updating automation configuration."""

    auto_book_cleaning: bool | None = Field(
        None, description="Auto-book cleaning tasks"
    )
    auto_book_maintenance: bool | None = Field(
        None, description="Auto-book maintenance tasks"
    )
    auto_book_photography: bool | None = Field(
        None, description="Auto-book photography tasks"
    )
    auto_respond_to_guests: bool | None = Field(
        None, description="Auto-respond to guest messages"
    )
    cleaning_preference: HumanPreference | None = Field(
        None, description="Preference for selecting cleaners"
    )
    maintenance_preference: HumanPreference | None = Field(
        None, description="Preference for selecting maintenance workers"
    )
    minimum_human_rating: float | None = Field(
        None, ge=3.0, le=5.0, description="Minimum acceptable rating"
    )
    max_booking_lead_time_days: int | None = Field(
        None, ge=1, le=30, description="Max days ahead to book"
    )
    notification_method: NotificationMethod | None = Field(
        None, description="Notification method"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "auto_book_cleaning": True,
                "auto_book_maintenance": True,
                "auto_book_photography": False,
                "auto_respond_to_guests": False,
                "cleaning_preference": "highest_rated",
                "maintenance_preference": "nearest",
                "minimum_human_rating": 4.0,
                "max_booking_lead_time_days": 3,
                "notification_method": "email",
            }
        }
    )


class AutomationConfigResponse(BaseModel):
    """Schema for automation configuration response."""

    id: UUID = Field(..., description="Configuration ID")
    host_id: UUID = Field(..., description="Host user ID")
    auto_book_cleaning: bool = Field(..., description="Auto-book cleaning tasks")
    auto_book_maintenance: bool = Field(..., description="Auto-book maintenance tasks")
    auto_book_photography: bool = Field(..., description="Auto-book photography tasks")
    auto_respond_to_guests: bool = Field(
        ..., description="Auto-respond to guest messages"
    )
    cleaning_preference: HumanPreference = Field(
        ..., description="Preference for cleaners"
    )
    maintenance_preference: HumanPreference = Field(
        ..., description="Preference for maintenance"
    )
    minimum_human_rating: float = Field(..., description="Minimum rating")
    max_booking_lead_time_days: int = Field(..., description="Max lead time days")
    notification_method: NotificationMethod = Field(
        ..., description="Notification method"
    )

    model_config = ConfigDict(from_attributes=True)


class TurnoverTemplateResponse(BaseModel):
    """Schema for turnover task template."""

    task_type: str = Field(default="cleaning", description="Task type")
    description_template: str = Field(..., description="Description template")
    default_duration_hours: float = Field(..., description="Default duration")
    default_checklist: list[str] = Field(..., description="Default checklist items")
    required_skills: list[str] = Field(..., description="Required skills")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_type": "cleaning",
                "description_template": "Turnover cleaning for {property_name}: checkout at {checkout_time}, checkin at {checkin_time}",
                "default_duration_hours": 3.0,
                "default_checklist": [
                    "Vacuum all rooms",
                    "Mop hard floors",
                    "Clean all bathrooms",
                    "Change bed linens",
                    "Empty trash",
                    "Clean kitchen appliances",
                    "Wipe down surfaces",
                    "Restock toiletries",
                ],
                "required_skills": ["cleaning"],
            }
        }
    )


class MaintenanceTemplateResponse(BaseModel):
    """Schema for maintenance task template."""

    task_type: str = Field(default="maintenance", description="Task type")
    description_template: str = Field(..., description="Description template")
    default_duration_hours: float = Field(..., description="Default duration")
    default_checklist: list[str] = Field(..., description="Default checklist items")
    required_skills: list[str] = Field(..., description="Required skills")
