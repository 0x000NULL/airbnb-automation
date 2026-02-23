"""
Celery configuration for background task processing.

Tasks:
- Polling: Sync bookings from Airbnb/VRBO every 15 minutes
- Task generation: Create tasks when new bookings detected
- Booking automation: Auto-book humans for pending tasks
- Status checking: Poll RentAHuman for status updates
- Notifications: Send email/SMS on status changes
"""

from celery import Celery
from celery.schedules import crontab

from config import settings

# Create Celery app
celery_app = Celery(
    "airbnb_automation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "tasks.polling",
        "tasks.task_generation",
        "tasks.booking_automation",
        "tasks.status_check",
        "tasks.notifications",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Los_Angeles",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    # Task routing
    task_routes={
        "tasks.polling.*": {"queue": "polling"},
        "tasks.task_generation.*": {"queue": "default"},
        "tasks.booking_automation.*": {"queue": "booking"},
        "tasks.status_check.*": {"queue": "default"},
        "tasks.notifications.*": {"queue": "notifications"},
    },
    # Beat schedule for periodic tasks
    beat_schedule={
        # Poll Airbnb bookings every 15 minutes
        "poll-airbnb-bookings": {
            "task": "tasks.polling.poll_airbnb_bookings",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "polling"},
        },
        # Poll VRBO bookings every 15 minutes (offset by 7 minutes)
        "poll-vrbo-bookings": {
            "task": "tasks.polling.poll_vrbo_bookings",
            "schedule": crontab(minute="7,22,37,52"),
            "options": {"queue": "polling"},
        },
        # Auto-book pending tasks every 30 minutes
        "auto-book-pending-tasks": {
            "task": "tasks.booking_automation.auto_book_pending_tasks",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "booking"},
        },
        # Check booking statuses every hour
        "check-booking-statuses": {
            "task": "tasks.status_check.check_booking_statuses",
            "schedule": crontab(minute="0"),
            "options": {"queue": "default"},
        },
        # Daily summary report at 8 AM
        "daily-summary-report": {
            "task": "tasks.notifications.send_daily_summary",
            "schedule": crontab(hour="8", minute="0"),
            "options": {"queue": "notifications"},
        },
    },
)


def get_celery_app() -> Celery:
    """Get the configured Celery app instance."""
    return celery_app
