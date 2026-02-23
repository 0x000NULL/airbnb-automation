"""
Human-related Pydantic schemas (for RentAHuman integration).
"""

from pydantic import BaseModel, ConfigDict, Field


class HumanSearchParams(BaseModel):
    """Schema for human search parameters."""

    location: str = Field(..., min_length=1, description="City, state or ZIP code")
    skill: str | None = Field(None, description="Skill filter (cleaning, handyman, etc)")
    availability: str | None = Field(
        None, description="Availability filter (available, next_24h, next_week)"
    )
    budget_max: float | None = Field(None, ge=0, description="Maximum hourly rate")
    rating_min: float | None = Field(
        None, ge=3.0, le=5.0, description="Minimum rating"
    )
    limit: int = Field(default=10, ge=1, le=100, description="Max results")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "Las Vegas, NV",
                "skill": "cleaning",
                "availability": "available",
                "budget_max": 50.0,
                "rating_min": 4.0,
                "limit": 10,
            }
        }
    )


class HumanResponse(BaseModel):
    """Schema for human profile response."""

    id: str = Field(..., description="Human unique identifier")
    name: str = Field(..., description="Human's name")
    skills: list[str] = Field(..., description="List of skills")
    location: str = Field(..., description="Human's location")
    rate: float = Field(..., description="Hourly rate (USD)")
    currency: str = Field(default="USD", description="Rate currency")
    rating: float = Field(..., description="Average rating")
    reviews: int = Field(..., description="Number of reviews")
    availability: str = Field(..., description="Current availability")
    bio: str = Field(..., description="Bio/description")
    photo_url: str | None = Field(None, description="Profile photo URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "human_001",
                "name": "Maria Garcia",
                "skills": ["cleaning", "organizing"],
                "location": "Las Vegas, NV",
                "rate": 25.0,
                "currency": "USD",
                "rating": 4.8,
                "reviews": 127,
                "availability": "available",
                "bio": "Professional cleaner with 8 years experience",
                "photo_url": "https://example.com/photos/maria.jpg",
            }
        }
    )


class HumanList(BaseModel):
    """Schema for list of humans."""

    humans: list[HumanResponse] = Field(..., description="List of humans")
    total: int = Field(..., description="Total count of humans")


class HumanReview(BaseModel):
    """Schema for a human's review."""

    id: str = Field(..., description="Review ID")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating")
    comment: str = Field(..., description="Review comment")
    reviewer_name: str = Field(..., description="Reviewer's name")
    date: str = Field(..., description="Review date")
    task_type: str | None = Field(None, description="Type of task reviewed")


class HumanReviewList(BaseModel):
    """Schema for list of reviews."""

    reviews: list[HumanReview] = Field(..., description="List of reviews")
    total: int = Field(..., description="Total count of reviews")
    average_rating: float = Field(..., description="Average rating")


class HumanAvailability(BaseModel):
    """Schema for human availability."""

    human_id: str = Field(..., description="Human ID")
    available: bool = Field(..., description="Whether currently available")
    next_available: str | None = Field(None, description="Next available date/time")
    booked_slots: list[dict] = Field(
        default_factory=list, description="Currently booked time slots"
    )


class Skill(BaseModel):
    """Schema for a skill."""

    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")


class SkillList(BaseModel):
    """Schema for list of skills."""

    skills: list[dict[str, str]] = Field(..., description="List of skills")
    total: int = Field(..., description="Total count of skills")
