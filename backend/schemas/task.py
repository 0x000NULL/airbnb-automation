"""
Task-related Pydantic schemas.
"""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.task import TaskStatus, TaskType


class TaskCreate(BaseModel):
    """Schema for creating a task manually."""

    type: TaskType = Field(..., description="Task type")
    property_id: UUID = Field(..., description="Property ID")
    airbnb_booking_id: UUID | None = Field(None, description="Associated booking ID")
    description: str = Field(
        ..., min_length=1, max_length=1000, description="Task description"
    )
    required_skills: list[str] = Field(
        default_factory=list, description="Required skills"
    )
    budget: float = Field(default=100.0, ge=0, description="Task budget (USD)")
    scheduled_date: date = Field(..., description="Scheduled date")
    scheduled_time: time = Field(..., description="Scheduled time")
    duration_hours: float = Field(default=2.0, ge=0.5, le=24, description="Duration")
    checklist: list[str] = Field(default_factory=list, description="Checklist items")
    host_notes: str | None = Field(None, max_length=1000, description="Host notes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "cleaning",
                "property_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Turnover cleaning for 2BR apartment",
                "required_skills": ["cleaning", "organizing"],
                "budget": 150.0,
                "scheduled_date": "2026-03-01",
                "scheduled_time": "11:00",
                "duration_hours": 3.0,
                "checklist": [
                    "Vacuum all rooms",
                    "Clean bathrooms",
                    "Change linens",
                    "Restock supplies",
                ],
                "host_notes": "Guest had a pet, extra attention to carpet",
            }
        }
    )


class TaskUpdate(BaseModel):
    """Schema for updating a task (all fields optional)."""

    description: str | None = Field(None, min_length=1, max_length=1000)
    required_skills: list[str] | None = None
    budget: float | None = Field(None, ge=0)
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    duration_hours: float | None = Field(None, ge=0.5, le=24)
    checklist: list[str] | None = None
    host_notes: str | None = Field(None, max_length=1000)
    status: TaskStatus | None = None


class AssignedHumanSchema(BaseModel):
    """Schema for assigned human details."""

    id: str = Field(..., description="Human ID from RentAHuman")
    name: str = Field(..., description="Human's name")
    photo: str | None = Field(None, description="Profile photo URL")
    rating: float = Field(..., description="Human's rating")
    reviews: int = Field(..., description="Number of reviews")


class TaskResponse(BaseModel):
    """Schema for task response."""

    id: UUID = Field(..., description="Task unique identifier")
    type: TaskType = Field(..., description="Task type")
    property_id: UUID = Field(..., description="Property ID")
    airbnb_booking_id: UUID | None = Field(None, description="Associated booking ID")
    description: str = Field(..., description="Task description")
    required_skills: list = Field(..., description="Required skills")
    budget: float = Field(..., description="Task budget")
    scheduled_date: date = Field(..., description="Scheduled date")
    scheduled_time: time = Field(..., description="Scheduled time")
    duration_hours: float = Field(..., description="Duration in hours")
    status: TaskStatus = Field(..., description="Current status")
    rentahuman_booking_id: str | None = Field(None, description="RentAHuman booking ID")
    assigned_human: dict | None = Field(None, description="Assigned human details")
    checklist: list = Field(..., description="Checklist items")
    photo_upload_url: str | None = Field(None, description="Photo upload URL")
    host_notes: str | None = Field(None, description="Host notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_urgent: bool = Field(..., description="Whether task is urgent")

    model_config = ConfigDict(from_attributes=True)


class TaskList(BaseModel):
    """Schema for list of tasks."""

    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total count of tasks")


class TaskBookRequest(BaseModel):
    """Schema for manually triggering task booking."""

    human_id: str | None = Field(
        None, description="Specific human ID to book (optional)"
    )
    special_requests: str | None = Field(
        None, max_length=500, description="Special requests for the human"
    )


class TaskStatusResponse(BaseModel):
    """Schema for task status with human details."""

    task_id: UUID = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Current status")
    rentahuman_booking_id: str | None = Field(None, description="RentAHuman booking ID")
    assigned_human: AssignedHumanSchema | None = Field(
        None, description="Assigned human"
    )
    completion_photos: list[str] = Field(
        default_factory=list, description="Completion photo URLs"
    )
    human_feedback: str | None = Field(None, description="Feedback from human")
