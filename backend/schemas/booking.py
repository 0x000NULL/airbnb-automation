"""
Booking-related Pydantic schemas.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.booking import BookingSource


class BookingCreate(BaseModel):
    """Schema for creating a booking (usually synced from Airbnb/VRBO)."""

    property_id: UUID = Field(..., description="Property ID")
    guest_name: str = Field(..., min_length=1, max_length=255, description="Guest name")
    checkin_date: date = Field(..., description="Check-in date")
    checkout_date: date = Field(..., description="Check-out date")
    guest_count: int = Field(default=1, ge=1, description="Number of guests")
    notes: str | None = Field(None, max_length=1000, description="Special requests")
    total_price: float = Field(default=0.0, ge=0, description="Total booking price")
    source: BookingSource = Field(
        default=BookingSource.AIRBNB, description="Booking source"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "property_id": "123e4567-e89b-12d3-a456-426614174000",
                "guest_name": "John Smith",
                "checkin_date": "2026-03-01",
                "checkout_date": "2026-03-05",
                "guest_count": 2,
                "notes": "Late arrival after 10pm",
                "total_price": 750.00,
                "source": "airbnb",
            }
        }
    )


class BookingResponse(BaseModel):
    """Schema for booking response."""

    id: UUID = Field(..., description="Booking unique identifier")
    property_id: UUID = Field(..., description="Property ID")
    guest_name: str = Field(..., description="Guest name")
    checkin_date: date = Field(..., description="Check-in date")
    checkout_date: date = Field(..., description="Check-out date")
    guest_count: int = Field(..., description="Number of guests")
    notes: str | None = Field(None, description="Special requests")
    total_price: float = Field(..., description="Total booking price")
    source: BookingSource = Field(..., description="Booking source")
    synced_at: datetime = Field(..., description="Last sync timestamp")
    duration_nights: int = Field(..., description="Number of nights")

    model_config = ConfigDict(from_attributes=True)


class BookingList(BaseModel):
    """Schema for list of bookings."""

    bookings: list[BookingResponse] = Field(..., description="List of bookings")
    total: int = Field(..., description="Total count of bookings")


class UpcomingBooking(BaseModel):
    """Schema for upcoming booking with property details."""

    id: UUID = Field(..., description="Booking unique identifier")
    property_id: UUID = Field(..., description="Property ID")
    property_name: str = Field(..., description="Property name")
    guest_name: str = Field(..., description="Guest name")
    checkin_date: date = Field(..., description="Check-in date")
    checkout_date: date = Field(..., description="Check-out date")
    guest_count: int = Field(..., description="Number of guests")
    days_until_checkin: int = Field(..., description="Days until check-in")
    tasks_pending: int = Field(..., description="Number of pending tasks")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "property_id": "987e6543-e21b-12d3-a456-426614174000",
                "property_name": "Luxury Strip View Apartment",
                "guest_name": "John Smith",
                "checkin_date": "2026-03-01",
                "checkout_date": "2026-03-05",
                "guest_count": 2,
                "days_until_checkin": 7,
                "tasks_pending": 2,
            }
        }
    )
