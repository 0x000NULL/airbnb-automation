"""
FastAPI application entry point.

Airbnb/VRBO Hosting Automation - AI-powered hosting assistant that automatically
hires humans via RentAHuman API for property management tasks.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js frontend
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import and include routers
from api import router as api_router

app.include_router(api_router)


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
