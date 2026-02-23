"""
Property-related Pydantic schemas.
"""

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LocationSchema(BaseModel):
    """Schema for property location."""

    city: str = Field(..., min_length=1, max_length=100, description="City name")
    state: str = Field(..., min_length=2, max_length=50, description="State/province")
    zip: str = Field(..., min_length=3, max_length=20, description="ZIP/postal code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "Las Vegas",
                "state": "NV",
                "zip": "89101",
            }
        }
    )


class PropertyCreate(BaseModel):
    """Schema for creating a new property."""

    name: str = Field(..., min_length=1, max_length=255, description="Property name")
    location: LocationSchema = Field(..., description="Property location")
    property_type: str = Field(
        default="apartment",
        description="Property type (apartment, house, condo, etc.)",
    )
    bedrooms: int = Field(default=1, ge=0, le=20, description="Number of bedrooms")
    bathrooms: int = Field(default=1, ge=1, le=20, description="Number of bathrooms")
    max_guests: int = Field(default=2, ge=1, le=50, description="Maximum guest capacity")
    airbnb_listing_id: str | None = Field(None, description="Airbnb listing ID")
    vrbo_listing_id: str | None = Field(None, description="VRBO listing ID")
    default_checkin_time: time = Field(
        default=time(15, 0), description="Default check-in time"
    )
    default_checkout_time: time = Field(
        default=time(11, 0), description="Default check-out time"
    )
    cleaning_budget: float = Field(
        default=150.0, ge=0, description="Default cleaning budget (USD)"
    )
    maintenance_budget: float = Field(
        default=200.0, ge=0, description="Default maintenance budget (USD)"
    )
    preferred_skills: list[str] = Field(
        default_factory=list, description="Preferred human skills"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Luxury Strip View Apartment",
                "location": {"city": "Las Vegas", "state": "NV", "zip": "89109"},
                "property_type": "apartment",
                "bedrooms": 2,
                "bathrooms": 2,
                "max_guests": 4,
                "airbnb_listing_id": "12345678",
                "default_checkin_time": "15:00",
                "default_checkout_time": "11:00",
                "cleaning_budget": 150.0,
                "maintenance_budget": 200.0,
                "preferred_skills": ["cleaning", "organizing"],
            }
        }
    )


class PropertyUpdate(BaseModel):
    """Schema for updating a property (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    location: LocationSchema | None = None
    property_type: str | None = None
    bedrooms: int | None = Field(None, ge=0, le=20)
    bathrooms: int | None = Field(None, ge=1, le=20)
    max_guests: int | None = Field(None, ge=1, le=50)
    airbnb_listing_id: str | None = None
    vrbo_listing_id: str | None = None
    default_checkin_time: time | None = None
    default_checkout_time: time | None = None
    cleaning_budget: float | None = Field(None, ge=0)
    maintenance_budget: float | None = Field(None, ge=0)
    preferred_skills: list[str] | None = None


class PropertyResponse(BaseModel):
    """Schema for property response."""

    id: UUID = Field(..., description="Property unique identifier")
    host_id: UUID = Field(..., description="Host user ID")
    name: str = Field(..., description="Property name")
    location: dict = Field(..., description="Property location")
    property_type: str = Field(..., description="Property type")
    bedrooms: int = Field(..., description="Number of bedrooms")
    bathrooms: int = Field(..., description="Number of bathrooms")
    max_guests: int = Field(..., description="Maximum guest capacity")
    airbnb_listing_id: str | None = Field(None, description="Airbnb listing ID")
    vrbo_listing_id: str | None = Field(None, description="VRBO listing ID")
    default_checkin_time: time = Field(..., description="Default check-in time")
    default_checkout_time: time = Field(..., description="Default check-out time")
    cleaning_budget: float = Field(..., description="Cleaning budget")
    maintenance_budget: float = Field(..., description="Maintenance budget")
    preferred_skills: list = Field(..., description="Preferred skills")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class PropertyList(BaseModel):
    """Schema for list of properties."""

    properties: list[PropertyResponse] = Field(..., description="List of properties")
    total: int = Field(..., description="Total count of properties")


class ConnectPlatformRequest(BaseModel):
    """Schema for connecting Airbnb/VRBO listing."""

    listing_id: str = Field(..., min_length=1, description="Platform listing ID")
