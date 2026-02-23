"""
Payment service for commission tracking and Stripe integration.

Handles:
- Commission calculation (15% on RentAHuman bookings)
- Payment record storage (database-backed)
- Stripe integration (skeleton for future implementation)
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.payment import PaymentRecord, PaymentStatus

logger = logging.getLogger(__name__)


class CommissionSummary:
    """Summary of commissions for a period."""

    def __init__(
        self,
        total_bookings: int = 0,
        total_booking_value: float = 0.0,
        total_commission: float = 0.0,
        pending_commission: float = 0.0,
        paid_commission: float = 0.0,
        average_booking_value: float = 0.0,
    ):
        self.total_bookings = total_bookings
        self.total_booking_value = total_booking_value
        self.total_commission = total_commission
        self.pending_commission = pending_commission
        self.paid_commission = paid_commission
        self.average_booking_value = average_booking_value


class PaymentService:
    """
    Service for payment and commission tracking.

    Commission rate: 15% of RentAHuman booking costs.
    All records are persisted to the database.
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
        else:
            logger.warning(
                "⚠️  Stripe not configured — payment intents will use mock mode. "
                "Set STRIPE_SECRET_KEY for real payment processing."
            )

    def calculate_commission(self, booking_cost: float) -> float:
        """Calculate commission for a booking (15%)."""
        return round(booking_cost * self.COMMISSION_RATE, 2)

    async def create_payment_record(
        self,
        db: AsyncSession,
        task_id: UUID,
        booking_id: str,
        total_amount: float,
    ) -> PaymentRecord:
        """Create a payment record in the database."""
        commission = self.calculate_commission(total_amount)

        record = PaymentRecord(
            id=uuid4(),
            task_id=task_id,
            booking_id=booking_id,
            total_amount=total_amount,
            commission_amount=commission,
            commission_rate=self.COMMISSION_RATE,
            status=PaymentStatus.PENDING,
        )

        db.add(record)
        await db.flush()

        logger.info(
            f"Payment record created: {record.id} "
            f"(amount=${total_amount:.2f}, commission=${commission:.2f})"
        )

        return record

    async def get_payment_record(self, db: AsyncSession, record_id: UUID) -> PaymentRecord | None:
        """Get a payment record by ID."""
        result = await db.execute(select(PaymentRecord).where(PaymentRecord.id == record_id))
        return result.scalar_one_or_none()

    async def get_records_for_task(self, db: AsyncSession, task_id: UUID) -> list[PaymentRecord]:
        """Get all payment records for a task."""
        result = await db.execute(
            select(PaymentRecord).where(PaymentRecord.task_id == task_id)
        )
        return list(result.scalars().all())

    async def mark_as_paid(self, db: AsyncSession, record_id: UUID) -> PaymentRecord | None:
        """Mark a payment record as paid."""
        record = await self.get_payment_record(db, record_id)
        if record:
            record.status = PaymentStatus.PAID
            record.paid_at = datetime.now(timezone.utc)
            await db.flush()
            logger.info(f"Payment record {record_id} marked as paid")
        return record

    async def get_commission_summary(
        self,
        db: AsyncSession,
        host_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CommissionSummary:
        """Get commission summary from the database."""
        query = select(PaymentRecord)
        filters = []
        if start_date:
            filters.append(PaymentRecord.created_at >= start_date)
        if end_date:
            filters.append(PaymentRecord.created_at <= end_date)
        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        records = list(result.scalars().all())

        total_bookings = len(records)
        total_booking_value = sum(r.total_amount for r in records)
        total_commission = sum(r.commission_amount for r in records)
        pending_commission = sum(r.commission_amount for r in records if r.status == PaymentStatus.PENDING)
        paid_commission = sum(r.commission_amount for r in records if r.status == PaymentStatus.PAID)
        average_booking_value = total_booking_value / total_bookings if total_bookings > 0 else 0.0

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
        """Create a Stripe payment intent."""
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
                amount=int(amount * 100),
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
        """Process a Stripe webhook event."""
        if not self.stripe_configured:
            logger.warning("Stripe not configured, cannot process webhook")
            return None

        try:
            event = self.stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret,
            )
            logger.info(f"Received Stripe webhook: {event.type}")

            if event.type == "payment_intent.succeeded":
                payment_intent = event.data.object
                logger.info(f"Payment succeeded: {payment_intent.id}")
            elif event.type == "payment_intent.payment_failed":
                payment_intent = event.data.object
                logger.warning(f"Payment failed: {payment_intent.id}")

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
