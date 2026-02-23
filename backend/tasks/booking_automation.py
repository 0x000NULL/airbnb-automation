"""
Booking automation tasks.

Automatically books humans for pending tasks via RentAHuman API.
Includes retry logic, fallback strategies, and cost optimization.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from celery_config import celery_app
from database import async_session_maker
from models.automation_config import AutomationConfig
from models.property import Property
from models.task import Task, TaskStatus, TaskType
from models.user import User
from services.booking_engine import BookingEngine, get_booking_engine
from services.payment_service import get_payment_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _get_pending_tasks(session: AsyncSession) -> list[Task]:
    """Get all pending tasks that need booking."""
    # Only get tasks scheduled within the booking lead time
    max_date = datetime.now().date() + timedelta(days=7)

    result = await session.execute(
        select(Task)
        .where(
            Task.status == TaskStatus.PENDING,
            Task.scheduled_date <= max_date,
            Task.rentahuman_booking_id.is_(None),
        )
        .order_by(Task.scheduled_date, Task.scheduled_time)
    )
    return list(result.scalars().all())


async def _get_task_context(
    session: AsyncSession, task: Task
) -> tuple[Property | None, AutomationConfig | None]:
    """Get property and automation config for a task."""
    # Get property
    result = await session.execute(
        select(Property).where(Property.id == task.property_id)
    )
    prop = result.scalar_one_or_none()

    if not prop:
        return None, None

    # Get automation config
    result = await session.execute(
        select(AutomationConfig).where(AutomationConfig.host_id == prop.host_id)
    )
    config = result.scalar_one_or_none()

    return prop, config


def _should_auto_book(task: Task, config: AutomationConfig | None) -> bool:
    """Check if this task should be auto-booked based on config."""
    if not config:
        return False

    if task.type == TaskType.CLEANING:
        return config.auto_book_cleaning
    elif task.type == TaskType.MAINTENANCE:
        return config.auto_book_maintenance
    elif task.type == TaskType.PHOTOGRAPHY:
        return config.auto_book_photography
    elif task.type == TaskType.COMMUNICATION:
        return config.auto_respond_to_guests
    elif task.type == TaskType.RESTOCKING:
        return config.auto_book_cleaning  # Follows cleaning setting

    return False


@celery_app.task(
    name="tasks.booking_automation.auto_book_pending_tasks",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def auto_book_pending_tasks(self) -> dict:
    """
    Process all pending tasks and attempt to book humans.

    Returns:
        Summary of booking results
    """
    import asyncio

    async def _process():
        engine = get_booking_engine()
        payment_service = get_payment_service()

        results = {
            "tasks_processed": 0,
            "bookings_created": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

        async with async_session_maker() as session:
            pending_tasks = await _get_pending_tasks(session)
            logger.info(f"Found {len(pending_tasks)} pending tasks to process")

            for task in pending_tasks:
                results["tasks_processed"] += 1

                try:
                    prop, config = await _get_task_context(session, task)

                    if not prop:
                        logger.warning(f"Property not found for task {task.id}")
                        results["skipped"] += 1
                        continue

                    # Check if auto-booking is enabled for this task type
                    if not _should_auto_book(task, config):
                        logger.debug(
                            f"Auto-booking disabled for {task.type.value} tasks"
                        )
                        results["skipped"] += 1
                        continue

                    # Use default config if none exists
                    if not config:
                        config = AutomationConfig(host_id=prop.host_id)

                    # Attempt to book
                    booking_result = await engine.book_task(task, prop, config)

                    if booking_result.success:
                        # Update task with booking info
                        task.rentahuman_booking_id = booking_result.booking_id
                        task.assigned_human = {
                            "id": booking_result.human.id,
                            "name": booking_result.human.name,
                            "rating": booking_result.human.rating,
                            "phone": booking_result.human.phone,
                        }
                        task.status = TaskStatus.HUMAN_BOOKED

                        # Create payment record
                        await payment_service.create_payment_record(
                            task_id=task.id,
                            booking_id=booking_result.booking_id,
                            total_amount=booking_result.total_cost,
                        )

                        results["bookings_created"] += 1

                        logger.info(
                            f"Booked {booking_result.human.name} for task {task.id} "
                            f"(${booking_result.total_cost:.2f})"
                        )

                        # Send notification
                        from tasks.notifications import send_booking_notification

                        send_booking_notification.delay(
                            str(task.id),
                            booking_result.human.name,
                        )

                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {
                                "task_id": str(task.id),
                                "error": booking_result.error,
                            }
                        )
                        logger.warning(
                            f"Failed to book for task {task.id}: {booking_result.error}"
                        )

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(
                        {"task_id": str(task.id), "error": str(e)}
                    )
                    logger.error(f"Error processing task {task.id}: {e}")

            await session.commit()

        logger.info(
            f"Auto-booking complete: {results['bookings_created']} bookings, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )

        return results

    return asyncio.get_event_loop().run_until_complete(_process())


@celery_app.task(
    name="tasks.booking_automation.book_task_human",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def book_task_human(self, task_id: str, human_id: str | None = None) -> dict:
    """
    Book a human for a specific task.

    Args:
        task_id: UUID of the task
        human_id: Optional specific human to book

    Returns:
        Booking result
    """
    import asyncio

    async def _book():
        engine = get_booking_engine()
        payment_service = get_payment_service()

        async with async_session_maker() as session:
            try:
                # Get task
                result = await session.execute(
                    select(Task).where(Task.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()

                if not task:
                    return {"success": False, "error": "Task not found"}

                if task.status != TaskStatus.PENDING:
                    return {
                        "success": False,
                        "error": f"Task status is {task.status.value}, not pending",
                    }

                # Get context
                prop, config = await _get_task_context(session, task)

                if not prop:
                    return {"success": False, "error": "Property not found"}

                if not config:
                    config = AutomationConfig(host_id=prop.host_id)

                # Book human
                booking_result = await engine.book_task(task, prop, config)

                if booking_result.success:
                    task.rentahuman_booking_id = booking_result.booking_id
                    task.assigned_human = {
                        "id": booking_result.human.id,
                        "name": booking_result.human.name,
                        "rating": booking_result.human.rating,
                        "phone": booking_result.human.phone,
                    }
                    task.status = TaskStatus.HUMAN_BOOKED

                    await payment_service.create_payment_record(
                        task_id=task.id,
                        booking_id=booking_result.booking_id,
                        total_amount=booking_result.total_cost,
                    )

                    await session.commit()

                    from tasks.notifications import send_booking_notification

                    send_booking_notification.delay(
                        str(task.id),
                        booking_result.human.name,
                    )

                    return {
                        "success": True,
                        "booking_id": booking_result.booking_id,
                        "human_name": booking_result.human.name,
                        "total_cost": booking_result.total_cost,
                    }

                return {
                    "success": False,
                    "error": booking_result.error,
                }

            except Exception as e:
                logger.error(f"Error booking human for task {task_id}: {e}")
                return {"success": False, "error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_book())


@celery_app.task(name="tasks.booking_automation.handle_cancellation")
def handle_cancellation(task_id: str, reason: str = "Human cancelled") -> dict:
    """
    Handle a human cancellation by finding a replacement.

    Args:
        task_id: UUID of the task
        reason: Cancellation reason

    Returns:
        Replacement booking result
    """
    import asyncio

    async def _handle():
        engine = get_booking_engine()

        async with async_session_maker() as session:
            try:
                # Get task
                result = await session.execute(
                    select(Task).where(Task.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()

                if not task:
                    return {"success": False, "error": "Task not found"}

                prop, config = await _get_task_context(session, task)

                if not prop:
                    return {"success": False, "error": "Property not found"}

                if not config:
                    config = AutomationConfig(host_id=prop.host_id)

                # Log cancellation
                logger.warning(
                    f"Handling cancellation for task {task_id}: {reason}"
                )

                # Try to find replacement
                replacement_result = await engine.handle_cancellation(
                    task, prop, config
                )

                if replacement_result.success:
                    task.rentahuman_booking_id = replacement_result.booking_id
                    task.assigned_human = {
                        "id": replacement_result.human.id,
                        "name": replacement_result.human.name,
                        "rating": replacement_result.human.rating,
                        "phone": replacement_result.human.phone,
                    }
                    task.status = TaskStatus.HUMAN_BOOKED

                    await session.commit()

                    # Send notification about replacement
                    from tasks.notifications import send_status_notification

                    send_status_notification.delay(
                        str(task.id),
                        "cancelled",
                        "human_booked",
                        f"Replacement booked: {replacement_result.human.name}",
                    )

                    return {
                        "success": True,
                        "replacement_found": True,
                        "new_human_name": replacement_result.human.name,
                        "new_booking_id": replacement_result.booking_id,
                    }

                # No replacement found
                task.status = TaskStatus.PENDING
                task.rentahuman_booking_id = None
                task.assigned_human = None

                await session.commit()

                from tasks.notifications import send_status_notification

                send_status_notification.delay(
                    str(task.id),
                    "human_booked",
                    "pending",
                    "Human cancelled - searching for replacement",
                )

                return {
                    "success": False,
                    "replacement_found": False,
                    "error": replacement_result.error,
                }

            except Exception as e:
                logger.error(f"Error handling cancellation for task {task_id}: {e}")
                return {"success": False, "error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_handle())
