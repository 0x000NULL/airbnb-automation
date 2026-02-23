"""
Task generation tasks.

Automatically creates property management tasks from bookings:
- CLEANING task on checkout
- COMMUNICATION task 24h before checkin
- RESTOCKING task for high-occupancy stays
"""

import logging
from uuid import UUID

from celery_config import celery_app
from database import async_session_maker
from models.booking import AirbnbBooking
from models.property import Property
from models.task import Task, TaskStatus
from services.task_generator import GeneratedTask, get_task_generator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _get_booking_with_property(
    session: AsyncSession, booking_id: UUID
) -> tuple[AirbnbBooking | None, Property | None]:
    """Get a booking and its associated property."""
    result = await session.execute(
        select(AirbnbBooking).where(AirbnbBooking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        return None, None

    result = await session.execute(
        select(Property).where(Property.id == booking.property_id)
    )
    prop = result.scalar_one_or_none()

    return booking, prop


async def _get_next_booking(
    session: AsyncSession, property_id: UUID, after_date
) -> AirbnbBooking | None:
    """Get the next booking after a given date for a property."""
    result = await session.execute(
        select(AirbnbBooking)
        .where(
            AirbnbBooking.property_id == property_id,
            AirbnbBooking.checkin_date > after_date,
        )
        .order_by(AirbnbBooking.checkin_date)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _task_exists(
    session: AsyncSession,
    property_id: UUID,
    booking_id: UUID,
    task_type: str,
) -> bool:
    """Check if a task already exists for this booking."""
    result = await session.execute(
        select(Task).where(
            Task.property_id == property_id,
            Task.airbnb_booking_id == booking_id,
            Task.type == task_type,
        )
    )
    return result.scalar_one_or_none() is not None


async def _save_generated_task(
    session: AsyncSession, generated: GeneratedTask
) -> Task:
    """Save a generated task to the database."""
    task = Task(
        type=generated.type,
        property_id=generated.property_id,
        airbnb_booking_id=generated.booking_id,
        description=generated.description,
        required_skills=generated.required_skills,
        budget=generated.budget,
        scheduled_date=generated.scheduled_date,
        scheduled_time=generated.scheduled_time,
        duration_hours=generated.duration_hours,
        checklist=generated.checklist,
        host_notes=generated.host_notes,
        status=TaskStatus.PENDING,
    )
    session.add(task)
    await session.flush()
    return task


@celery_app.task(
    name="tasks.task_generation.generate_tasks_for_booking",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def generate_tasks_for_booking(self, booking_id: str) -> dict:
    """
    Generate all tasks for a booking.

    Args:
        booking_id: UUID of the booking

    Returns:
        Summary of generated tasks
    """
    import asyncio

    async def _generate():
        generator = get_task_generator()
        results = {
            "booking_id": booking_id,
            "tasks_created": 0,
            "task_types": [],
            "errors": [],
        }

        async with async_session_maker() as session:
            try:
                booking, prop = await _get_booking_with_property(
                    session, UUID(booking_id)
                )

                if not booking or not prop:
                    results["errors"].append("Booking or property not found")
                    return results

                # Get next booking for tight turnover detection
                next_booking = await _get_next_booking(
                    session, prop.id, booking.checkout_date
                )

                # Generate tasks
                generated_tasks = generator.generate_from_booking(
                    booking=booking,
                    prop=prop,
                    next_booking=next_booking,
                )

                # Save each generated task
                for generated in generated_tasks:
                    # Skip if task already exists
                    if await _task_exists(
                        session,
                        generated.property_id,
                        generated.booking_id,
                        generated.type,
                    ):
                        logger.info(
                            f"Task {generated.type.value} already exists for booking {booking_id}"
                        )
                        continue

                    task = await _save_generated_task(session, generated)
                    results["tasks_created"] += 1
                    results["task_types"].append(generated.type.value)

                    logger.info(
                        f"Created {generated.type.value} task for booking {booking_id}"
                    )

                await session.commit()

                # Trigger auto-booking if tasks were created
                if results["tasks_created"] > 0:
                    from tasks.booking_automation import auto_book_pending_tasks

                    auto_book_pending_tasks.apply_async(countdown=5)

            except Exception as e:
                logger.error(f"Error generating tasks for booking {booking_id}: {e}")
                results["errors"].append(str(e))
                await session.rollback()

        return results

    return asyncio.get_event_loop().run_until_complete(_generate())


@celery_app.task(name="tasks.task_generation.generate_tasks_for_property")
def generate_tasks_for_property(property_id: str) -> dict:
    """
    Generate tasks for all bookings of a property.

    Useful for initial setup or manual regeneration.

    Args:
        property_id: UUID of the property

    Returns:
        Summary of generated tasks
    """
    import asyncio

    async def _generate():
        results = {
            "property_id": property_id,
            "bookings_processed": 0,
            "total_tasks_created": 0,
            "errors": [],
        }

        async with async_session_maker() as session:
            try:
                # Get property
                result = await session.execute(
                    select(Property).where(Property.id == UUID(property_id))
                )
                prop = result.scalar_one_or_none()

                if not prop:
                    results["errors"].append("Property not found")
                    return results

                # Get all bookings
                result = await session.execute(
                    select(AirbnbBooking)
                    .where(AirbnbBooking.property_id == prop.id)
                    .order_by(AirbnbBooking.checkin_date)
                )
                bookings = list(result.scalars().all())

                # Generate tasks for each booking
                generator = get_task_generator()

                for i, booking in enumerate(bookings):
                    results["bookings_processed"] += 1

                    # Get next booking for tight turnover
                    next_booking = bookings[i + 1] if i + 1 < len(bookings) else None

                    generated_tasks = generator.generate_from_booking(
                        booking=booking,
                        prop=prop,
                        next_booking=next_booking,
                    )

                    for generated in generated_tasks:
                        if await _task_exists(
                            session,
                            generated.property_id,
                            generated.booking_id,
                            generated.type,
                        ):
                            continue

                        await _save_generated_task(session, generated)
                        results["total_tasks_created"] += 1

                await session.commit()

                logger.info(
                    f"Generated {results['total_tasks_created']} tasks "
                    f"for {results['bookings_processed']} bookings at {prop.name}"
                )

            except Exception as e:
                logger.error(
                    f"Error generating tasks for property {property_id}: {e}"
                )
                results["errors"].append(str(e))
                await session.rollback()

        return results

    return asyncio.get_event_loop().run_until_complete(_generate())


@celery_app.task(name="tasks.task_generation.regenerate_task")
def regenerate_task(task_id: str) -> dict:
    """
    Regenerate a specific task (e.g., after booking change).

    Args:
        task_id: UUID of the task to regenerate

    Returns:
        Updated task info
    """
    import asyncio

    async def _regenerate():
        async with async_session_maker() as session:
            try:
                # Get existing task
                result = await session.execute(
                    select(Task).where(Task.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()

                if not task:
                    return {"error": "Task not found"}

                if task.status != TaskStatus.PENDING:
                    return {"error": "Can only regenerate pending tasks"}

                # Get booking and property
                booking, prop = await _get_booking_with_property(
                    session, task.airbnb_booking_id
                )

                if not booking or not prop:
                    return {"error": "Booking or property not found"}

                # Get next booking
                next_booking = await _get_next_booking(
                    session, prop.id, booking.checkout_date
                )

                # Regenerate
                generator = get_task_generator()
                generated_tasks = generator.generate_from_booking(
                    booking=booking,
                    prop=prop,
                    next_booking=next_booking,
                )

                # Find matching task type
                for generated in generated_tasks:
                    if generated.type == task.type:
                        # Update task fields
                        task.description = generated.description
                        task.budget = generated.budget
                        task.scheduled_date = generated.scheduled_date
                        task.scheduled_time = generated.scheduled_time
                        task.duration_hours = generated.duration_hours
                        task.checklist = generated.checklist
                        task.host_notes = generated.host_notes

                        await session.commit()

                        return {
                            "task_id": task_id,
                            "updated": True,
                            "new_budget": generated.budget,
                            "new_scheduled_date": str(generated.scheduled_date),
                        }

                return {"error": "No matching task type found"}

            except Exception as e:
                logger.error(f"Error regenerating task {task_id}: {e}")
                return {"error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_regenerate())
