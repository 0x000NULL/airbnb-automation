"""
FastAPI application entry point.

Airbnb/VRBO Hosting Automation - AI-powered hosting assistant that automatically
hires humans via RentAHuman API for property management tasks.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Rate limiter (Issue #3)
limiter = Limiter(key_func=get_remote_address)

# Default JWT secret that must be changed in production
_DEFAULT_JWT_SECRET = "your-super-secret-jwt-key-change-in-production"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan events.

    Handles startup and shutdown tasks like database connections,
    cache warming, etc.
    """
    # Startup
    logger.info("Starting Airbnb Automation API...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"RentAHuman Mock Mode: {settings.rentahuman_mock_mode}")

    # Issue #1: Reject default JWT secret in non-development environments
    if settings.jwt_secret_key == _DEFAULT_JWT_SECRET and not settings.is_development:
        raise RuntimeError(
            "FATAL: Default JWT secret key detected in non-development environment. "
            "Set a secure JWT_SECRET_KEY in your environment variables."
        )
    elif settings.jwt_secret_key == _DEFAULT_JWT_SECRET:
        logger.warning(
            "⚠️  Using default JWT secret key. This is only acceptable in development."
        )

    # Issue #7-8: Warn when mock mode is active for Airbnb/VRBO services
    if settings.rentahuman_mock_mode:
        logger.warning(
            "⚠️  Airbnb/VRBO services are running in MOCK MODE. "
            "Set RENTAHUMAN_MOCK_MODE=false and configure real API credentials for production."
        )

    # Issue #12: Warn when Stripe is in mock mode
    if not settings.stripe_enabled:
        logger.warning(
            "⚠️  Stripe is NOT configured — payments will use mock mode. "
            "Set STRIPE_SECRET_KEY for real payment processing."
        )

    # Issue #11: Mount local uploads directory for dev/mock storage
    import os
    upload_dir = "/tmp/airbnb-automation/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    yield

    # Shutdown
    logger.info("Shutting down Airbnb Automation API...")


# Create FastAPI application
app = FastAPI(
    title="Airbnb/VRBO Hosting Automation API",
    description=(
        "AI-powered hosting assistant that automatically hires humans via RentAHuman API "
        "for property management tasks including cleaning, maintenance, photography, "
        "and guest communication."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Issue #2: Environment-conditional CORS
if settings.is_production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3100",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3100",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3100",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3100",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Import and include routers
from api import router as api_router

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Airbnb/VRBO Hosting Automation API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )
