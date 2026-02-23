"""
Status check tasks.

Polls RentAHuman API for booking status updates.
Updates task statuses and triggers notifications on changes.
"""

import logging
from uuid import UUID

from celery_config import celery_app
from database import async_session_maker
from models.task import Task, TaskStatus
from services.rentahuman_client import get_rentahuman_client
from sqlalchemy import select

logger = logging.getLogger(__name__)


# Map RentAHuman statuses to internal TaskStatus
STATUS_MAP = {
    "pending": TaskStatus.HUMAN_BOOKED,
    "confirmed": TaskStatus.HUMAN_BOOKED,
    "in_progress": TaskStatus.IN_PROGRESS,
    "completed": TaskStatus.COMPLETED,
    "cancelled": TaskStatus.PENDING,  # Will trigger rebooking
    "failed": TaskStatus.FAILED,
}


@celery_app.task(
    name="tasks.status_check.check_booking_statuses",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def check_booking_statuses(self) -> dict:
    """
    Check status of all active bookings.

    Polls RentAHuman API for status updates and updates local tasks.

    Returns:
        Summary of status checks
    """
    import asyncio

    async def _check():
        client = get_rentahuman_client()
        results = {
            "bookings_checked": 0,
            "status_changes": 0,
            "completions": 0,
            "cancellations": 0,
            "errors": [],
        }

        async with async_session_maker() as session:
            # Get tasks with active bookings
            result = await session.execute(
                select(Task).where(
                    Task.rentahuman_booking_id.isnot(None),
                    Task.status.in_(
                        [TaskStatus.HUMAN_BOOKED, TaskStatus.IN_PROGRESS]
                    ),
                )
            )
            tasks = list(result.scalars().all())

            logger.info(f"Checking status of {len(tasks)} active bookings")

            for task in tasks:
                results["bookings_checked"] += 1

                try:
                    # Get booking status from RentAHuman
                    booking = await client.get_booking_status(
                        task.rentahuman_booking_id
                    )

                    if not booking:
                        logger.warning(
                            f"Booking {task.rentahuman_booking_id} not found"
                        )
                        continue

                    # Map to internal status
                    new_status = STATUS_MAP.get(booking.get("status"), task.status)

                    if new_status != task.status:
                        old_status = task.status
                        task.status = new_status
                        results["status_changes"] += 1

                        logger.info(
                            f"Task {task.id} status changed: "
                            f"{old_status.value} -> {new_status.value}"
                        )

                        # Track specific transitions
                        if new_status == TaskStatus.COMPLETED:
                            results["completions"] += 1

                            # Mark payment as ready for collection
                            from services.payment_service import get_payment_service

                            payment_service = get_payment_service()
                            records = await payment_service.get_records_for_task(
                                task.id
                            )
                            for record in records:
                                await payment_service.mark_as_paid(record.id)

                        elif new_status == TaskStatus.PENDING:
                            # Cancellation - trigger rebooking
                            results["cancellations"] += 1

                            from tasks.booking_automation import handle_cancellation

                            handle_cancellation.delay(str(task.id))

                        # Send notification
                        from tasks.notifications import send_status_notification

                        send_status_notification.delay(
                            str(task.id),
                            old_status.value,
                            new_status.value,
                        )

                except Exception as e:
                    logger.error(
                        f"Error checking status for booking "
                        f"{task.rentahuman_booking_id}: {e}"
                    )
                    results["errors"].append(
                        {
                            "task_id": str(task.id),
                            "booking_id": task.rentahuman_booking_id,
                            "error": str(e),
                        }
                    )

            await session.commit()

        logger.info(
            f"Status check complete: {results['status_changes']} changes, "
            f"{results['completions']} completions, "
            f"{results['cancellations']} cancellations"
        )

        return results

    return asyncio.get_event_loop().run_until_complete(_check())


@celery_app.task(
    name="tasks.status_check.check_booking_status",
    bind=True,
    max_retries=5,
    default_retry_delay=60,
)
def check_booking_status(self, task_id: str) -> dict:
    """
    Check status of a specific booking.

    Args:
        task_id: UUID of the task

    Returns:
        Current booking status
    """
    import asyncio

    async def _check():
        client = get_rentahuman_client()

        async with async_session_maker() as session:
            try:
                # Get task
                result = await session.execute(
                    select(Task).where(Task.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()

                if not task:
                    return {"error": "Task not found"}

                if not task.rentahuman_booking_id:
                    return {"error": "No booking associated with task"}

                # Get booking status
                booking = await client.get_booking_status(
                    task.rentahuman_booking_id
                )

                if not booking:
                    return {
                        "error": "Booking not found",
                        "booking_id": task.rentahuman_booking_id,
                    }

                # Update status if changed
                new_status = STATUS_MAP.get(booking.get("status"), task.status)
                old_status = task.status

                if new_status != old_status:
                    task.status = new_status
                    await session.commit()

                    # Trigger notification
                    from tasks.notifications import send_status_notification

                    send_status_notification.delay(
                        str(task.id),
                        old_status.value,
                        new_status.value,
                    )

                return {
                    "task_id": task_id,
                    "booking_id": task.rentahuman_booking_id,
                    "rentahuman_status": booking.get("status"),
                    "internal_status": new_status.value,
                    "status_changed": new_status != old_status,
                    "human_name": task.assigned_human.get("name")
                    if task.assigned_human
                    else None,
                }

            except Exception as e:
                logger.error(f"Error checking status for task {task_id}: {e}")
                return {"error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_check())


@celery_app.task(name="tasks.status_check.verify_completion")
def verify_completion(task_id: str) -> dict:
    """
    Verify a task completion and process final steps.

    Called after a task is marked complete to:
    - Verify completion with RentAHuman
    - Process payment
    - Update analytics

    Args:
        task_id: UUID of the task

    Returns:
        Verification result
    """
    import asyncio

    async def _verify():
        client = get_rentahuman_client()

        async with async_session_maker() as session:
            try:
                # Get task
                result = await session.execute(
                    select(Task).where(Task.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()

                if not task:
                    return {"error": "Task not found"}

                if task.status != TaskStatus.COMPLETED:
                    return {"error": "Task not marked as completed"}

                # Verify with RentAHuman
                booking = await client.get_booking_status(
                    task.rentahuman_booking_id
                )

                verified = booking and booking.get("status") == "completed"

                if verified:
                    # Process payment
                    from services.payment_service import get_payment_service

                    payment_service = get_payment_service()
                    records = await payment_service.get_records_for_task(task.id)

                    for record in records:
                        await payment_service.mark_as_paid(record.id)

                    logger.info(
                        f"Task {task_id} completion verified and payment processed"
                    )

                    return {
                        "task_id": task_id,
                        "verified": True,
                        "payment_processed": True,
                    }

                return {
                    "task_id": task_id,
                    "verified": False,
                    "rentahuman_status": booking.get("status") if booking else "unknown",
                }

            except Exception as e:
                logger.error(f"Error verifying completion for task {task_id}: {e}")
                return {"error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_verify())
