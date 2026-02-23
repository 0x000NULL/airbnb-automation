"""
Booking log service for transaction auditing.

Provides methods to log booking events for debugging,
auditing, and analytics.
"""

import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.booking_log import BookingLog, BookingLogEvent

logger = logging.getLogger(__name__)


class BookingLogService:
    """
    Service for logging booking-related events.

    Provides both async database logging and sync
    in-memory logging for development/testing.
    """

    def __init__(self, session: AsyncSession | None = None):
        """
        Initialize the booking log service.

        Args:
            session: Optional async database session
        """
        self.session = session
        self._in_memory_logs: list[dict] = []

    async def log_event(
        self,
        event: BookingLogEvent,
        message: str,
        task_id: UUID | None = None,
        property_id: UUID | None = None,
        host_id: UUID | None = None,
        rentahuman_booking_id: str | None = None,
        human_id: str | None = None,
        details: dict | None = None,
        success: bool | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
        source: str | None = None,
        attempt_number: int | None = None,
    ) -> BookingLog | None:
        """
        Log a booking event.

        Args:
            event: Type of event
            message: Human-readable description
            task_id: Related task ID
            property_id: Related property ID
            host_id: Related host user ID
            rentahuman_booking_id: RentAHuman booking ID
            human_id: RentAHuman human ID
            details: Additional event details (JSON)
            success: Whether the operation succeeded
            error_message: Error message if failed
            duration_ms: Operation duration in milliseconds
            source: Source of the event (api, celery, webhook, etc.)
            attempt_number: Retry attempt number

        Returns:
            Created BookingLog or None if no session
        """
        log_entry = BookingLog(
            event=event,
            message=message,
            task_id=task_id,
            property_id=property_id,
            host_id=host_id,
            rentahuman_booking_id=rentahuman_booking_id,
            human_id=human_id,
            details=details,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            source=source,
            attempt_number=attempt_number,
        )

        # Log to application logger
        log_level = logging.INFO if success is None or success else logging.WARNING
        logger.log(
            log_level,
            f"[{event.value}] {message} "
            f"(task={task_id}, booking={rentahuman_booking_id})",
        )

        # Store in database if session available
        if self.session:
            self.session.add(log_entry)
            await self.session.flush()
            return log_entry

        # Store in memory for development/testing
        self._in_memory_logs.append({
            "event": event.value,
            "message": message,
            "task_id": str(task_id) if task_id else None,
            "rentahuman_booking_id": rentahuman_booking_id,
            "success": success,
            "created_at": datetime.utcnow().isoformat(),
        })

        return None

    async def log_search(
        self,
        task_id: UUID,
        location: str,
        skill: str | None,
        budget_max: float | None,
        results_count: int,
        duration_ms: int,
    ) -> BookingLog | None:
        """Log a human search event."""
        return await self.log_event(
            event=BookingLogEvent.SEARCH_COMPLETED,
            message=f"Found {results_count} humans in {location}",
            task_id=task_id,
            details={
                "location": location,
                "skill": skill,
                "budget_max": budget_max,
                "results_count": results_count,
            },
            success=results_count > 0,
            duration_ms=duration_ms,
            source="booking_engine",
        )

    async def log_booking_attempt(
        self,
        task_id: UUID,
        human_id: str,
        human_name: str,
        budget: float,
        attempt_number: int,
    ) -> BookingLog | None:
        """Log a booking attempt."""
        return await self.log_event(
            event=BookingLogEvent.BOOKING_ATTEMPTED,
            message=f"Attempting to book {human_name} for ${budget:.2f}",
            task_id=task_id,
            human_id=human_id,
            details={
                "human_name": human_name,
                "budget": budget,
            },
            attempt_number=attempt_number,
            source="booking_engine",
        )

    async def log_booking_success(
        self,
        task_id: UUID,
        rentahuman_booking_id: str,
        human_id: str,
        human_name: str,
        total_cost: float,
        duration_ms: int,
    ) -> BookingLog | None:
        """Log a successful booking."""
        return await self.log_event(
            event=BookingLogEvent.BOOKING_CREATED,
            message=f"Booked {human_name} for ${total_cost:.2f}",
            task_id=task_id,
            rentahuman_booking_id=rentahuman_booking_id,
            human_id=human_id,
            details={
                "human_name": human_name,
                "total_cost": total_cost,
            },
            success=True,
            duration_ms=duration_ms,
            source="booking_engine",
        )

    async def log_booking_failure(
        self,
        task_id: UUID,
        error: str,
        human_id: str | None = None,
        attempt_number: int | None = None,
    ) -> BookingLog | None:
        """Log a failed booking attempt."""
        return await self.log_event(
            event=BookingLogEvent.BOOKING_FAILED,
            message=f"Booking failed: {error}",
            task_id=task_id,
            human_id=human_id,
            success=False,
            error_message=error,
            attempt_number=attempt_number,
            source="booking_engine",
        )

    async def log_cancellation(
        self,
        task_id: UUID,
        rentahuman_booking_id: str,
        reason: str,
        source: str = "webhook",
    ) -> BookingLog | None:
        """Log a booking cancellation."""
        return await self.log_event(
            event=BookingLogEvent.CANCELLATION_RECEIVED,
            message=f"Booking cancelled: {reason}",
            task_id=task_id,
            rentahuman_booking_id=rentahuman_booking_id,
            details={"reason": reason},
            source=source,
        )

    async def log_replacement_search(
        self,
        task_id: UUID,
        original_booking_id: str,
    ) -> BookingLog | None:
        """Log that a replacement search has started."""
        return await self.log_event(
            event=BookingLogEvent.REPLACEMENT_SEARCH,
            message="Searching for replacement human",
            task_id=task_id,
            rentahuman_booking_id=original_booking_id,
            source="booking_engine",
        )

    async def log_replacement_result(
        self,
        task_id: UUID,
        original_booking_id: str,
        new_booking_id: str | None,
        new_human_name: str | None,
        success: bool,
        error: str | None = None,
    ) -> BookingLog | None:
        """Log the result of a replacement search."""
        event = (
            BookingLogEvent.REPLACEMENT_FOUND
            if success
            else BookingLogEvent.REPLACEMENT_FAILED
        )
        message = (
            f"Replacement found: {new_human_name}"
            if success
            else f"Replacement failed: {error}"
        )

        return await self.log_event(
            event=event,
            message=message,
            task_id=task_id,
            rentahuman_booking_id=new_booking_id or original_booking_id,
            details={
                "original_booking_id": original_booking_id,
                "new_booking_id": new_booking_id,
                "new_human_name": new_human_name,
            },
            success=success,
            error_message=error,
            source="booking_engine",
        )

    async def log_fallback_triggered(
        self,
        task_id: UUID,
        original_budget: float,
        expanded_budget: float,
        reason: str,
    ) -> BookingLog | None:
        """Log when fallback search is triggered."""
        return await self.log_event(
            event=BookingLogEvent.FALLBACK_TRIGGERED,
            message=f"Fallback triggered: expanding budget to ${expanded_budget:.2f}",
            task_id=task_id,
            details={
                "original_budget": original_budget,
                "expanded_budget": expanded_budget,
                "reason": reason,
            },
            source="booking_engine",
        )

    def get_in_memory_logs(self) -> list[dict]:
        """Get in-memory logs (for development/testing)."""
        return self._in_memory_logs.copy()


class LoggingTimer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()

    @property
    def duration_ms(self) -> int:
        """Get duration in milliseconds."""
        return int((self.end_time - self.start_time) * 1000)


# Default instance (in-memory only)
_default_service: BookingLogService | None = None


def get_booking_log_service(
    session: AsyncSession | None = None,
) -> BookingLogService:
    """Get or create a booking log service instance."""
    global _default_service
    if session:
        return BookingLogService(session)
    if _default_service is None:
        _default_service = BookingLogService()
    return _default_service
