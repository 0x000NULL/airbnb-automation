"""
Webhook endpoints for external service callbacks.

Handles:
- RentAHuman booking status updates and cancellations
- Stripe payment webhooks
"""

import hashlib
import hmac
import logging
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.deps import DbSession
from config import settings
from models.booking_log import BookingLogEvent
from models.task import Task, TaskStatus
from services.booking_log_service import get_booking_log_service

logger = logging.getLogger(__name__)

router = APIRouter()


class RentAHumanWebhookPayload(BaseModel):
    """Payload from RentAHuman webhook."""

    event: str = Field(..., description="Event type")
    booking_id: str = Field(..., description="Booking ID")
    status: str | None = Field(None, description="New status")
    human_id: str | None = Field(None, description="Human ID")
    human_name: str | None = Field(None, description="Human name")
    reason: str | None = Field(None, description="Cancellation reason")
    completed_at: str | None = Field(None, description="Completion timestamp")
    photos: list[str] | None = Field(None, description="Completion photo URLs")
    feedback: str | None = Field(None, description="Human feedback")
    timestamp: str = Field(..., description="Event timestamp")


def verify_rentahuman_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify RentAHuman webhook signature.

    Uses HMAC-SHA256 to verify the payload hasn't been tampered with.
    """
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


@router.post("/rentahuman")
async def rentahuman_webhook(
    request: Request,
    db: DbSession,
    x_rentahuman_signature: str = Header(None, alias="X-RentAHuman-Signature"),
):
    """
    Handle RentAHuman webhook callbacks.

    Events:
    - booking.confirmed: Human confirmed the booking
    - booking.started: Human started the task
    - booking.completed: Human completed the task
    - booking.cancelled: Human cancelled the booking
    - booking.failed: Task failed
    """
    # Get raw payload for signature verification
    payload_bytes = await request.body()

    # In production, verify signature
    if not settings.is_development:
        webhook_secret = settings.rentahuman_webhook_secret
        if webhook_secret and x_rentahuman_signature:
            if not verify_rentahuman_signature(
                payload_bytes,
                x_rentahuman_signature,
                webhook_secret,
            ):
                logger.warning("Invalid RentAHuman webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )

    # Parse payload
    try:
        payload = RentAHumanWebhookPayload.model_validate_json(payload_bytes)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    logger.info(
        f"RentAHuman webhook received: {payload.event} "
        f"for booking {payload.booking_id}"
    )

    # Find the task with this booking ID
    result = await db.execute(
        select(Task).where(Task.rentahuman_booking_id == payload.booking_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"No task found for booking {payload.booking_id}")
        return {"status": "ignored", "reason": "task_not_found"}

    # Initialize log service
    log_service = get_booking_log_service(db)

    # Handle different event types
    if payload.event == "booking.confirmed":
        task.status = TaskStatus.HUMAN_BOOKED
        if payload.human_name and task.assigned_human:
            task.assigned_human["confirmed"] = True

        await log_service.log_event(
            event=BookingLogEvent.BOOKING_CONFIRMED,
            message=f"Booking confirmed by {payload.human_name}",
            task_id=task.id,
            rentahuman_booking_id=payload.booking_id,
            human_id=payload.human_id,
        )

    elif payload.event == "booking.started":
        task.status = TaskStatus.IN_PROGRESS

        await log_service.log_event(
            event=BookingLogEvent.TASK_STARTED,
            message=f"{payload.human_name} started the task",
            task_id=task.id,
            rentahuman_booking_id=payload.booking_id,
            human_id=payload.human_id,
        )

        # Send notification
        from tasks.notifications import send_status_notification

        send_status_notification.delay(
            str(task.id),
            "human_booked",
            "in_progress",
        )

    elif payload.event == "booking.completed":
        task.status = TaskStatus.COMPLETED

        # Store completion details
        if payload.photos:
            task.completion_photos = payload.photos
        if payload.feedback:
            task.human_feedback = payload.feedback

        await log_service.log_event(
            event=BookingLogEvent.TASK_COMPLETED,
            message=f"Task completed by {payload.human_name}",
            task_id=task.id,
            rentahuman_booking_id=payload.booking_id,
            human_id=payload.human_id,
            details={
                "photos_count": len(payload.photos) if payload.photos else 0,
                "has_feedback": bool(payload.feedback),
            },
            success=True,
        )

        # Process payment
        from services.payment_service import get_payment_service

        payment_service = get_payment_service()
        records = await payment_service.get_records_for_task(task.id)
        for record in records:
            await payment_service.mark_as_paid(record.id)

        # Send notification
        from tasks.notifications import send_status_notification

        send_status_notification.delay(
            str(task.id),
            "in_progress",
            "completed",
        )

    elif payload.event == "booking.cancelled":
        # Log the cancellation
        await log_service.log_cancellation(
            task_id=task.id,
            rentahuman_booking_id=payload.booking_id,
            reason=payload.reason or "No reason provided",
            source="webhook",
        )

        # Check urgency - if task is within 2 hours, send urgent alert
        scheduled_dt = datetime.combine(task.scheduled_date, task.scheduled_time)
        hours_until = (scheduled_dt - datetime.now()).total_seconds() / 3600

        if hours_until <= 2:
            # Urgent cancellation - send alert
            from tasks.notifications import send_cancellation_alert

            send_cancellation_alert.delay(
                str(task.id),
                payload.reason or "Human cancelled",
            )

        # Trigger replacement search
        from tasks.booking_automation import handle_cancellation

        handle_cancellation.delay(str(task.id), payload.reason or "Human cancelled")

        logger.warning(
            f"Booking cancelled for task {task.id}: {payload.reason}"
        )

    elif payload.event == "booking.failed":
        task.status = TaskStatus.FAILED

        await log_service.log_event(
            event=BookingLogEvent.BOOKING_FAILED,
            message=f"Task failed: {payload.reason}",
            task_id=task.id,
            rentahuman_booking_id=payload.booking_id,
            human_id=payload.human_id,
            success=False,
            error_message=payload.reason,
        )

        # Send notification
        from tasks.notifications import send_status_notification

        send_status_notification.delay(
            str(task.id),
            task.status.value,
            "failed",
            payload.reason,
        )

    else:
        logger.info(f"Unhandled webhook event: {payload.event}")
        return {"status": "ignored", "reason": "unknown_event"}

    await db.commit()

    return {
        "status": "processed",
        "event": payload.event,
        "task_id": str(task.id),
    }


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Handle Stripe payment webhooks.

    Events:
    - payment_intent.succeeded: Payment completed
    - payment_intent.payment_failed: Payment failed
    """
    from services.payment_service import get_payment_service

    payment_service = get_payment_service()

    # Get raw payload
    payload = await request.body()

    # Process webhook
    result = await payment_service.process_stripe_webhook(
        payload,
        stripe_signature or "",
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook",
        )

    return {"status": "processed", "event": result.get("type")}


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }
