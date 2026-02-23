"""
Notification tasks.

Sends email and SMS notifications for task status changes,
booking confirmations, and daily summaries.
"""

import logging
from datetime import date, datetime, timedelta
from uuid import UUID

from celery_config import celery_app
from database import async_session_maker
from models.automation_config import AutomationConfig, NotificationMethod
from models.property import Property
from models.task import Task, TaskStatus
from models.user import User
from services.notification_service import (
    NotificationContext,
    NotificationService,
    NotificationType,
    get_notification_service,
)
from sqlalchemy import func, select

logger = logging.getLogger(__name__)


async def _get_task_with_context(
    session, task_id: UUID
) -> tuple[Task | None, Property | None, User | None, AutomationConfig | None]:
    """Get task with all related context."""
    # Get task
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        return None, None, None, None

    # Get property
    result = await session.execute(
        select(Property).where(Property.id == task.property_id)
    )
    prop = result.scalar_one_or_none()

    if not prop:
        return task, None, None, None

    # Get user (host)
    result = await session.execute(select(User).where(User.id == prop.host_id))
    user = result.scalar_one_or_none()

    # Get config
    result = await session.execute(
        select(AutomationConfig).where(AutomationConfig.host_id == prop.host_id)
    )
    config = result.scalar_one_or_none()

    return task, prop, user, config


def _get_notification_method(
    config: AutomationConfig | None,
) -> str:
    """Get preferred notification method from config."""
    if not config:
        return "email"

    method_map = {
        NotificationMethod.EMAIL: "email",
        NotificationMethod.SMS: "sms",
        NotificationMethod.PUSH: "email",  # Fallback to email
    }
    return method_map.get(config.notification_method, "email")


@celery_app.task(
    name="tasks.notifications.send_status_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_status_notification(
    self,
    task_id: str,
    old_status: str,
    new_status: str,
    extra_message: str | None = None,
) -> dict:
    """
    Send notification for a task status change.

    Args:
        task_id: UUID of the task
        old_status: Previous status
        new_status: New status
        extra_message: Optional additional message

    Returns:
        Notification result
    """
    import asyncio

    async def _send():
        service = get_notification_service()

        async with async_session_maker() as session:
            try:
                task, prop, user, config = await _get_task_with_context(
                    session, UUID(task_id)
                )

                if not task or not prop or not user:
                    return {"error": "Task, property, or user not found"}

                # Determine notification type
                status_to_type = {
                    "human_booked": NotificationType.HUMAN_BOOKED,
                    "in_progress": NotificationType.TASK_IN_PROGRESS,
                    "completed": NotificationType.TASK_COMPLETED,
                    "failed": NotificationType.TASK_FAILED,
                }

                notification_type = status_to_type.get(
                    new_status, NotificationType.TASK_CREATED
                )

                # Build context
                context = NotificationContext(
                    recipient_name=user.name,
                    recipient_email=user.email,
                    recipient_phone=user.phone,
                    property_name=prop.name,
                    task_type=task.type.value,
                    human_name=(
                        task.assigned_human.get("name")
                        if task.assigned_human
                        else None
                    ),
                    scheduled_date=task.scheduled_date.strftime("%B %d, %Y"),
                    extra_data={"old_status": old_status, "message": extra_message},
                )

                # Get notification method
                method = _get_notification_method(config)

                # Send notification
                success = await service.send_notification(
                    notification_type=notification_type,
                    context=context,
                    method=method,
                )

                return {
                    "task_id": task_id,
                    "notification_type": notification_type.value,
                    "method": method,
                    "success": success,
                }

            except Exception as e:
                logger.error(
                    f"Error sending status notification for task {task_id}: {e}"
                )
                return {"error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_send())


@celery_app.task(
    name="tasks.notifications.send_booking_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_booking_notification(
    self,
    task_id: str,
    human_name: str,
) -> dict:
    """
    Send notification when a human is booked for a task.

    Args:
        task_id: UUID of the task
        human_name: Name of the booked human

    Returns:
        Notification result
    """
    import asyncio

    async def _send():
        service = get_notification_service()

        async with async_session_maker() as session:
            try:
                task, prop, user, config = await _get_task_with_context(
                    session, UUID(task_id)
                )

                if not task or not prop or not user:
                    return {"error": "Task, property, or user not found"}

                context = NotificationContext(
                    recipient_name=user.name,
                    recipient_email=user.email,
                    recipient_phone=user.phone,
                    property_name=prop.name,
                    task_type=task.type.value,
                    human_name=human_name,
                    scheduled_date=task.scheduled_date.strftime("%B %d, %Y"),
                )

                method = _get_notification_method(config)

                success = await service.send_notification(
                    notification_type=NotificationType.HUMAN_BOOKED,
                    context=context,
                    method=method,
                )

                return {
                    "task_id": task_id,
                    "human_name": human_name,
                    "method": method,
                    "success": success,
                }

            except Exception as e:
                logger.error(
                    f"Error sending booking notification for task {task_id}: {e}"
                )
                return {"error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_send())


@celery_app.task(
    name="tasks.notifications.send_daily_summary",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def send_daily_summary(self) -> dict:
    """
    Send daily summary to all hosts.

    Includes:
    - Today's tasks
    - Upcoming tasks this week
    - Recent completions
    - Any issues requiring attention

    Returns:
        Summary of notifications sent
    """
    import asyncio

    async def _send():
        service = get_notification_service()
        results = {
            "hosts_notified": 0,
            "errors": [],
        }

        async with async_session_maker() as session:
            try:
                # Get all active users
                result = await session.execute(
                    select(User).where(User.is_active.is_(True))
                )
                users = list(result.scalars().all())

                for user in users:
                    try:
                        # Get user's properties
                        result = await session.execute(
                            select(Property).where(Property.host_id == user.id)
                        )
                        properties = list(result.scalars().all())

                        if not properties:
                            continue

                        property_ids = [p.id for p in properties]

                        # Get today's tasks
                        today = date.today()
                        result = await session.execute(
                            select(Task).where(
                                Task.property_id.in_(property_ids),
                                Task.scheduled_date == today,
                            )
                        )
                        todays_tasks = list(result.scalars().all())

                        # Get this week's upcoming tasks
                        week_end = today + timedelta(days=7)
                        result = await session.execute(
                            select(Task).where(
                                Task.property_id.in_(property_ids),
                                Task.scheduled_date > today,
                                Task.scheduled_date <= week_end,
                                Task.status == TaskStatus.PENDING,
                            )
                        )
                        upcoming_tasks = list(result.scalars().all())

                        # Get tasks needing attention (failed or pending too long)
                        result = await session.execute(
                            select(Task).where(
                                Task.property_id.in_(property_ids),
                                Task.status.in_(
                                    [TaskStatus.FAILED, TaskStatus.PENDING]
                                ),
                                Task.scheduled_date <= today,
                            )
                        )
                        attention_tasks = list(result.scalars().all())

                        # Build summary email
                        summary_lines = [
                            f"Hi {user.name},\n",
                            f"Here's your daily property summary for {today.strftime('%B %d, %Y')}:\n",
                        ]

                        if todays_tasks:
                            summary_lines.append(f"\nToday's Tasks ({len(todays_tasks)}):")
                            for task in todays_tasks[:5]:
                                prop_name = next(
                                    (p.name for p in properties if p.id == task.property_id),
                                    "Unknown",
                                )
                                summary_lines.append(
                                    f"  - {task.type.value.title()} at {prop_name} "
                                    f"({task.status.value})"
                                )
                            if len(todays_tasks) > 5:
                                summary_lines.append(
                                    f"  ... and {len(todays_tasks) - 5} more"
                                )

                        if upcoming_tasks:
                            summary_lines.append(
                                f"\nUpcoming This Week ({len(upcoming_tasks)}):"
                            )
                            for task in upcoming_tasks[:3]:
                                prop_name = next(
                                    (p.name for p in properties if p.id == task.property_id),
                                    "Unknown",
                                )
                                summary_lines.append(
                                    f"  - {task.scheduled_date.strftime('%a %m/%d')}: "
                                    f"{task.type.value.title()} at {prop_name}"
                                )

                        if attention_tasks:
                            summary_lines.append(
                                f"\nNeeds Attention ({len(attention_tasks)}):"
                            )
                            for task in attention_tasks[:3]:
                                prop_name = next(
                                    (p.name for p in properties if p.id == task.property_id),
                                    "Unknown",
                                )
                                summary_lines.append(
                                    f"  - {task.type.value.title()} at {prop_name} "
                                    f"(status: {task.status.value})"
                                )

                        summary_lines.append(
                            "\nView all tasks at: https://your-dashboard.com/tasks"
                        )

                        # Send email
                        success = await service.send_email(
                            to_email=user.email,
                            subject=f"Daily Summary - {today.strftime('%B %d')}",
                            body="\n".join(summary_lines),
                        )

                        if success:
                            results["hosts_notified"] += 1

                    except Exception as e:
                        results["errors"].append(
                            {"user_id": str(user.id), "error": str(e)}
                        )

            except Exception as e:
                logger.error(f"Error sending daily summaries: {e}")
                results["errors"].append({"error": str(e)})

        logger.info(f"Daily summaries sent to {results['hosts_notified']} hosts")
        return results

    return asyncio.get_event_loop().run_until_complete(_send())


@celery_app.task(name="tasks.notifications.send_cancellation_alert")
def send_cancellation_alert(task_id: str, reason: str) -> dict:
    """
    Send urgent alert when a human cancels close to task time.

    Args:
        task_id: UUID of the task
        reason: Cancellation reason

    Returns:
        Notification result
    """
    import asyncio

    async def _send():
        service = get_notification_service()

        async with async_session_maker() as session:
            try:
                task, prop, user, config = await _get_task_with_context(
                    session, UUID(task_id)
                )

                if not task or not prop or not user:
                    return {"error": "Task, property, or user not found"}

                context = NotificationContext(
                    recipient_name=user.name,
                    recipient_email=user.email,
                    recipient_phone=user.phone,
                    property_name=prop.name,
                    task_type=task.type.value,
                    human_name=(
                        task.assigned_human.get("name")
                        if task.assigned_human
                        else "Unknown"
                    ),
                    scheduled_date=task.scheduled_date.strftime("%B %d, %Y"),
                    extra_data={"reason": reason},
                )

                # Send both email and SMS for urgent cancellations
                email_success = await service.send_notification(
                    notification_type=NotificationType.BOOKING_CANCELLED,
                    context=context,
                    method="email",
                )

                sms_success = True
                if user.phone:
                    sms_success = await service.send_notification(
                        notification_type=NotificationType.BOOKING_CANCELLED,
                        context=context,
                        method="sms",
                    )

                return {
                    "task_id": task_id,
                    "email_sent": email_success,
                    "sms_sent": sms_success if user.phone else None,
                }

            except Exception as e:
                logger.error(
                    f"Error sending cancellation alert for task {task_id}: {e}"
                )
                return {"error": str(e)}

    return asyncio.get_event_loop().run_until_complete(_send())
