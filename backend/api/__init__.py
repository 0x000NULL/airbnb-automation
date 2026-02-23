"""
API routes aggregation.

All API endpoints are included here and mounted to the main FastAPI app.
"""

from fastapi import APIRouter

from api.analytics import router as analytics_router
from api.auth import router as auth_router
from api.bookings import router as bookings_router
from api.config import router as config_router
from api.humans import router as humans_router
from api.properties import router as properties_router
from api.tasks import router as tasks_router
from api.webhooks import router as webhooks_router

# Main API router
router = APIRouter()

# Include all route modules
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(properties_router, prefix="/properties", tags=["Properties"])
router.include_router(bookings_router, prefix="/bookings", tags=["Bookings"])
router.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
router.include_router(humans_router, prefix="/humans", tags=["Humans"])
router.include_router(config_router, prefix="/config", tags=["Configuration"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
