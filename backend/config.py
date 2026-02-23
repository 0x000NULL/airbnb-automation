"""
Application configuration using Pydantic Settings.

All configuration is loaded from environment variables with sensible defaults
for development. In production, set proper values via environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Literal["development", "production", "testing"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://airbnb:airbnb_secret@localhost:5432/airbnb_automation"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery (uses Redis as broker and backend)
    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL (Redis)."""
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        """Celery result backend URL (Redis)."""
        return self.redis_url

    # JWT Authentication
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # RentAHuman API
    rentahuman_api_key: str = ""
    rentahuman_base_url: str = "https://api.rentahuman.ai"
    rentahuman_mock_mode: bool = True
    rentahuman_webhook_secret: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # SendGrid Email
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "noreply@yourapp.com"

    # Twilio SMS
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Stripe Payments
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # DigitalOcean Spaces (S3-compatible storage)
    do_spaces_key: str = ""
    do_spaces_secret: str = ""
    do_spaces_region: str = "nyc3"
    do_spaces_bucket: str = "airbnb-automation-photos"
    do_spaces_endpoint: str = "https://nyc3.digitaloceanspaces.com"

    # AWS S3 (legacy, kept for compatibility)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_s3_region: str = "us-west-2"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"

    @property
    def notifications_enabled(self) -> bool:
        """Check if notification services are configured."""
        return bool(self.sendgrid_api_key) or bool(self.twilio_account_sid)

    @property
    def stripe_enabled(self) -> bool:
        """Check if Stripe is configured."""
        return bool(self.stripe_secret_key)

    @property
    def do_spaces_enabled(self) -> bool:
        """Check if DigitalOcean Spaces is configured."""
        return bool(self.do_spaces_key) and bool(self.do_spaces_secret)

    @property
    def s3_enabled(self) -> bool:
        """Check if S3 is configured."""
        return bool(self.aws_access_key_id) and bool(self.aws_s3_bucket)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
