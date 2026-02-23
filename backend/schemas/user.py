"""
User-related Pydantic schemas for authentication and user management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    phone: str | None = Field(None, max_length=20, description="Phone number for SMS")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "ethan@example.com",
                "password": "securepassword123",
                "name": "Ethan Aldrich",
                "phone": "+1-555-123-4567",
            }
        }
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "ethan@example.com",
                "password": "securepassword123",
            }
        }
    )


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive data)."""

    id: UUID = Field(..., description="User's unique identifier")
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., description="User's full name")
    phone: str | None = Field(None, description="Phone number")
    is_active: bool = Field(..., description="Whether account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserResponse = Field(..., description="User information")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "ethan@example.com",
                    "name": "Ethan Aldrich",
                    "phone": "+1-555-123-4567",
                    "is_active": True,
                    "created_at": "2026-02-22T12:00:00Z",
                },
            }
        }
    )


class GoogleOAuthRequest(BaseModel):
    """Schema for Google OAuth callback."""

    code: str = Field(..., description="OAuth authorization code")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
