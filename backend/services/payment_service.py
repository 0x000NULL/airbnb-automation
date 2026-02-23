"""
Payment service for commission tracking and Stripe integration.

Handles:
- Commission calculation (15% on RentAHuman bookings)
- Payment record storage
- Stripe integration (skeleton for future implementation)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class PaymentRecord:
    """Represents a payment/commission record."""

    id: UUID
    task_id: UUID
    booking_id: str  # RentAHuman booking ID
    total_amount: float
    commission_amount: float
    commission_rate: float
    status: str  # pending, paid, failed
    created_at: datetime
    paid_at: datetime | None = None


@dataclass
class CommissionSummary:
    """Summary of commissions for a period."""

    total_bookings: int
    total_booking_value: float
    total_commission: float
    pending_commission: float
    paid_commission: float
    average_booking_value: float


class PaymentService:
    """
    Service for payment and commission tracking.

    Commission rate: 15% of RentAHuman booking costs
    """

    COMMISSION_RATE = 0.15  # 15%

    def __init__(self):
        """Initialize payment service."""
        self.stripe_configured = bool(settings.stripe_secret_key)

        if self.stripe_configured:
            try:
                import stripe

                stripe.api_key = settings.stripe_secret_key
                self.stripe = stripe
                logger.info("Stripe client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Stripe: {e}")
                self.stripe_configured = False

        # In-memory storage for demo (would use database in production)
        self._payment_records: dict[UUID, PaymentRecord] = {}

    def calculate_commission(self, booking_cost: float) -> float:
        """
        Calculate commission for a booking.

        Args:
            booking_cost: Total cost of the RentAHuman booking

        Returns:
            Commission amount (15% of booking cost)
        """
        return round(booking_cost * self.COMMISSION_RATE, 2)

    async def create_payment_record(
        self,
        task_id: UUID,
        booking_id: str,
        total_amount: float,
    ) -> PaymentRecord:
        """
        Create a payment record for a completed booking.

        Args:
            task_id: Internal task UUID
            booking_id: RentAHuman booking ID
            total_amount: Total booking amount

        Returns:
            Created PaymentRecord
        """
        commission = self.calculate_commission(total_amount)

        record = PaymentRecord(
            id=uuid4(),
            task_id=task_id,
            booking_id=booking_id,
            total_amount=total_amount,
            commission_amount=commission,
            commission_rate=self.COMMISSION_RATE,
            status="pending",
            created_at=datetime.now(),
        )

        self._payment_records[record.id] = record

        logger.info(
            f"Payment record created: {record.id} "
            f"(amount=${total_amount:.2f}, commission=${commission:.2f})"
        )

        return record

    async def get_payment_record(self, record_id: UUID) -> PaymentRecord | None:
        """Get a payment record by ID."""
        return self._payment_records.get(record_id)

    async def get_records_for_task(self, task_id: UUID) -> list[PaymentRecord]:
        """Get all payment records for a task."""
        return [r for r in self._payment_records.values() if r.task_id == task_id]

    async def mark_as_paid(self, record_id: UUID) -> PaymentRecord | None:
        """Mark a payment record as paid."""
        record = self._payment_records.get(record_id)
        if record:
            record.status = "paid"
            record.paid_at = datetime.now()
            logger.info(f"Payment record {record_id} marked as paid")
        return record

    async def get_commission_summary(
        self,
        host_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CommissionSummary:
        """
        Get commission summary for a host.

        Args:
            host_id: Host's user ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            CommissionSummary with aggregated data
        """
        # In production, would filter by host_id and dates
        records = list(self._payment_records.values())

        if start_date:
            records = [r for r in records if r.created_at >= start_date]
        if end_date:
            records = [r for r in records if r.created_at <= end_date]

        total_bookings = len(records)
        total_booking_value = sum(r.total_amount for r in records)
        total_commission = sum(r.commission_amount for r in records)
        pending_commission = sum(
            r.commission_amount for r in records if r.status == "pending"
        )
        paid_commission = sum(
            r.commission_amount for r in records if r.status == "paid"
        )
        average_booking_value = (
            total_booking_value / total_bookings if total_bookings > 0 else 0.0
        )

        return CommissionSummary(
            total_bookings=total_bookings,
            total_booking_value=round(total_booking_value, 2),
            total_commission=round(total_commission, 2),
            pending_commission=round(pending_commission, 2),
            paid_commission=round(paid_commission, 2),
            average_booking_value=round(average_booking_value, 2),
        )

    async def create_stripe_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        metadata: dict | None = None,
    ) -> dict | None:
        """
        Create a Stripe payment intent.

        Args:
            amount: Amount in dollars
            currency: Currency code
            metadata: Additional metadata

        Returns:
            Payment intent object or None if Stripe not configured
        """
        if not self.stripe_configured:
            logger.info(
                f"[STRIPE MOCK] Creating payment intent: ${amount:.2f} {currency}"
            )
            return {
                "id": f"pi_mock_{uuid4().hex[:8]}",
                "amount": int(amount * 100),
                "currency": currency,
                "status": "requires_payment_method",
                "client_secret": f"pi_mock_secret_{uuid4().hex[:16]}",
            }

        try:
            intent = self.stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe uses cents
                currency=currency,
                metadata=metadata or {},
            )

            logger.info(f"Created Stripe payment intent: {intent.id}")
            return {
                "id": intent.id,
                "amount": intent.amount,
                "currency": intent.currency,
                "status": intent.status,
                "client_secret": intent.client_secret,
            }

        except Exception as e:
            logger.error(f"Failed to create Stripe payment intent: {e}")
            return None

    async def process_stripe_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> dict | None:
        """
        Process a Stripe webhook event.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            Processed event data or None if invalid
        """
        if not self.stripe_configured:
            logger.warning("Stripe not configured, cannot process webhook")
            return None

        try:
            event = self.stripe.Webhook.construct_event(
                payload,
                signature,
                settings.stripe_webhook_secret,
            )

            logger.info(f"Received Stripe webhook: {event.type}")

            # Handle different event types
            if event.type == "payment_intent.succeeded":
                # Mark corresponding payment record as paid
                payment_intent = event.data.object
                logger.info(f"Payment succeeded: {payment_intent.id}")
                # TODO: Update payment record based on metadata

            elif event.type == "payment_intent.payment_failed":
                payment_intent = event.data.object
                logger.warning(f"Payment failed: {payment_intent.id}")
                # TODO: Handle failed payment

            return {"type": event.type, "id": event.id}

        except Exception as e:
            logger.error(f"Failed to process Stripe webhook: {e}")
            return None


# Default instance
_default_service: PaymentService | None = None


def get_payment_service() -> PaymentService:
    """Get or create the default payment service instance."""
    global _default_service
    if _default_service is None:
        _default_service = PaymentService()
    return _default_service
