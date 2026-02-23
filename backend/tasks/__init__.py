"""
Celery tasks for automation.

Modules:
- polling: Periodic sync of bookings from Airbnb/VRBO
- task_generation: Create tasks when new bookings detected
- booking_automation: Auto-book humans for pending tasks
- status_check: Poll RentAHuman for status updates
- notifications: Send email/SMS notifications
"""

from tasks.booking_automation import auto_book_pending_tasks, book_task_human
from tasks.notifications import (
    send_booking_notification,
    send_daily_summary,
    send_status_notification,
)
from tasks.polling import poll_airbnb_bookings, poll_vrbo_bookings
from tasks.status_check import check_booking_status, check_booking_statuses
from tasks.task_generation import generate_tasks_for_booking, generate_tasks_for_property

__all__ = [
    # Polling
    "poll_airbnb_bookings",
    "poll_vrbo_bookings",
    # Task generation
    "generate_tasks_for_booking",
    "generate_tasks_for_property",
    # Booking automation
    "auto_book_pending_tasks",
    "book_task_human",
    # Status check
    "check_booking_statuses",
    "check_booking_status",
    # Notifications
    "send_status_notification",
    "send_booking_notification",
    "send_daily_summary",
]
