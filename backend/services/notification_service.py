"""
Notification service for email and SMS notifications.

Uses SendGrid for email and Twilio for SMS.
Falls back to logging if services are not configured.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from config import settings

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""

    TASK_CREATED = "task_created"
    HUMAN_BOOKED = "human_booked"
    TASK_IN_PROGRESS = "task_in_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    BOOKING_CANCELLED = "booking_cancelled"
    NEW_BOOKING = "new_booking"


@dataclass
class NotificationContext:
    """Context for notification templates."""

    recipient_name: str
    recipient_email: str | None = None
    recipient_phone: str | None = None
    property_name: str | None = None
    task_type: str | None = None
    human_name: str | None = None
    scheduled_date: str | None = None
    extra_data: dict | None = None


class NotificationService:
    """
    Service for sending notifications via email and SMS.

    Falls back to logging if external services are not configured.
    """

    def __init__(self):
        """Initialize notification service with API clients."""
        self.sendgrid_configured = bool(settings.sendgrid_api_key)
        self.twilio_configured = bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_phone_number
        )

        if self.sendgrid_configured:
            try:
                from sendgrid import SendGridAPIClient

                self.sendgrid_client = SendGridAPIClient(settings.sendgrid_api_key)
                logger.info("SendGrid client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize SendGrid: {e}")
                self.sendgrid_configured = False

        if self.twilio_configured:
            try:
                from twilio.rest import Client as TwilioClient

                self.twilio_client = TwilioClient(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token,
                )
                logger.info("Twilio client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Twilio: {e}")
                self.twilio_configured = False

    async def send_notification(
        self,
        notification_type: NotificationType,
        context: NotificationContext,
        method: str = "email",  # "email", "sms", or "both"
    ) -> bool:
        """
        Send a notification.

        Args:
            notification_type: Type of notification
            context: Notification context
            method: Delivery method

        Returns:
            True if notification was sent successfully
        """
        subject, body = self._get_notification_content(notification_type, context)

        success = True

        if method in ("email", "both") and context.recipient_email:
            email_success = await self.send_email(
                to_email=context.recipient_email,
                subject=subject,
                body=body,
            )
            success = success and email_success

        if method in ("sms", "both") and context.recipient_phone:
            sms_success = await self.send_sms(
                to_phone=context.recipient_phone,
                message=self._truncate_for_sms(body),
            )
            success = success and sms_success

        return success

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> bool:
        """
        Send an email notification.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body

        Returns:
            True if sent successfully
        """
        if not self.sendgrid_configured:
            logger.info(f"[EMAIL MOCK] To: {to_email}")
            logger.info(f"[EMAIL MOCK] Subject: {subject}")
            logger.info(f"[EMAIL MOCK] Body: {body[:200]}...")
            return True

        try:
            from sendgrid.helpers.mail import Content, Email, Mail, To

            message = Mail(
                from_email=Email(settings.sendgrid_from_email),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", body),
            )

            if html_body:
                message.add_content(Content("text/html", html_body))

            response = self.sendgrid_client.send(message)

            if response.status_code in (200, 201, 202):
                logger.info(f"Email sent to {to_email}: {subject}")
                return True
            else:
                logger.error(
                    f"Email failed: {response.status_code} - {response.body}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_sms(self, to_phone: str, message: str) -> bool:
        """
        Send an SMS notification.

        Args:
            to_phone: Recipient phone number
            message: SMS message (will be truncated if too long)

        Returns:
            True if sent successfully
        """
        if not self.twilio_configured:
            logger.info(f"[SMS MOCK] To: {to_phone}")
            logger.info(f"[SMS MOCK] Message: {message}")
            return True

        try:
            sms = self.twilio_client.messages.create(
                body=message,
                from_=settings.twilio_phone_number,
                to=to_phone,
            )

            logger.info(f"SMS sent to {to_phone}: {sms.sid}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    def _get_notification_content(
        self,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> tuple[str, str]:
        """Get subject and body for a notification type."""
        templates = {
            NotificationType.TASK_CREATED: (
                f"New {context.task_type} task for {context.property_name}",
                f"Hi {context.recipient_name},\n\n"
                f"A new {context.task_type} task has been created for "
                f"{context.property_name}.\n"
                f"Scheduled: {context.scheduled_date}\n\n"
                f"We'll automatically book a human for this task.",
            ),
            NotificationType.HUMAN_BOOKED: (
                f"Human booked for {context.property_name}",
                f"Hi {context.recipient_name},\n\n"
                f"Good news! {context.human_name} has been booked for "
                f"your {context.task_type} task at {context.property_name}.\n"
                f"Scheduled: {context.scheduled_date}",
            ),
            NotificationType.TASK_IN_PROGRESS: (
                f"Task started at {context.property_name}",
                f"Hi {context.recipient_name},\n\n"
                f"{context.human_name} has started the {context.task_type} "
                f"task at {context.property_name}.",
            ),
            NotificationType.TASK_COMPLETED: (
                f"Task completed at {context.property_name}",
                f"Hi {context.recipient_name},\n\n"
                f"Great news! The {context.task_type} task at "
                f"{context.property_name} has been completed by "
                f"{context.human_name}.",
            ),
            NotificationType.TASK_FAILED: (
                f"Task issue at {context.property_name}",
                f"Hi {context.recipient_name},\n\n"
                f"We encountered an issue with the {context.task_type} task "
                f"at {context.property_name}. Please check the dashboard "
                f"for details.",
            ),
            NotificationType.BOOKING_CANCELLED: (
                f"Booking cancelled - {context.property_name}",
                f"Hi {context.recipient_name},\n\n"
                f"Unfortunately, {context.human_name} has cancelled the "
                f"booking for {context.property_name}. We're searching "
                f"for a replacement.",
            ),
            NotificationType.NEW_BOOKING: (
                f"New guest booking at {context.property_name}",
                f"Hi {context.recipient_name},\n\n"
                f"You have a new guest booking at {context.property_name}.\n"
                f"We'll automatically schedule the necessary tasks.",
            ),
        }

        return templates.get(
            notification_type,
            ("Notification", f"Hi {context.recipient_name}, you have a new notification."),
        )

    def _truncate_for_sms(self, message: str, max_length: int = 160) -> str:
        """Truncate a message for SMS."""
        if len(message) <= max_length:
            return message
        return message[: max_length - 3] + "..."


# Default instance
_default_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get or create the default notification service instance."""
    global _default_service
    if _default_service is None:
        _default_service = NotificationService()
    return _default_service
