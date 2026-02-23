"""
Task generator service.

Automatically generates property management tasks from bookings.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID

from models.booking import AirbnbBooking
from models.property import Property
from models.task import TaskStatus, TaskType

logger = logging.getLogger(__name__)


@dataclass
class GeneratedTask:
    """Represents a task to be created."""

    type: TaskType
    property_id: UUID
    booking_id: UUID | None
    description: str
    required_skills: list[str]
    budget: float
    scheduled_date: date
    scheduled_time: time
    duration_hours: float
    checklist: list[str]
    is_tight_turnover: bool = False
    host_notes: str | None = None


class TaskGenerator:
    """
    Generates property management tasks from bookings.

    Rules:
    - Every checkout -> CLEANING task
    - Every checkin -> COMMUNICATION task (24h before)
    - Gap < 5h between checkout/checkin -> tight turnover
    - Guest count > 80% capacity -> RESTOCKING task
    """

    # Duration by bedroom count (hours)
    CLEANING_DURATION = {
        1: 2.0,
        2: 3.0,
        3: 4.0,
        4: 5.0,  # 4+ bedrooms
    }

    # Default checklists by task type
    DEFAULT_CHECKLISTS = {
        TaskType.CLEANING: [
            "Vacuum all floors and carpets",
            "Mop hard floors",
            "Clean and sanitize bathrooms",
            "Change all bed linens",
            "Make beds properly",
            "Empty all trash cans",
            "Clean kitchen appliances",
            "Wipe down all surfaces",
            "Clean mirrors and glass",
            "Restock toiletries",
            "Check for damage",
            "Set thermostat",
        ],
        TaskType.RESTOCKING: [
            "Check toilet paper supply",
            "Check paper towels",
            "Check dish soap",
            "Check laundry detergent",
            "Check coffee/tea supplies",
            "Check basic pantry items",
            "Replace any damaged items",
        ],
        TaskType.COMMUNICATION: [
            "Send welcome message",
            "Include check-in instructions",
            "Provide WiFi password",
            "Share local recommendations",
            "Confirm check-in time",
        ],
    }

    def __init__(self, buffer_percentage: float = 0.1):
        """
        Initialize the task generator.

        Args:
            buffer_percentage: Budget buffer (default 10%)
        """
        self.buffer_percentage = buffer_percentage

    def generate_from_booking(
        self,
        booking: AirbnbBooking,
        prop: Property,
        next_booking: AirbnbBooking | None = None,
    ) -> list[GeneratedTask]:
        """
        Generate all tasks for a booking.

        Args:
            booking: The booking to generate tasks for
            prop: The property for this booking
            next_booking: Optional next booking (to detect tight turnovers)

        Returns:
            List of GeneratedTask objects
        """
        tasks: list[GeneratedTask] = []

        # Check for tight turnover
        is_tight_turnover = False
        if next_booking:
            gap = self._calculate_turnover_gap(
                booking.checkout_date,
                prop.default_checkout_time,
                next_booking.checkin_date,
                prop.default_checkin_time,
            )
            is_tight_turnover = gap.total_seconds() / 3600 < 5  # Less than 5 hours

        # Generate CLEANING task for checkout
        cleaning_task = self._generate_cleaning_task(
            booking, prop, is_tight_turnover
        )
        tasks.append(cleaning_task)

        # Generate COMMUNICATION task for checkin (24h before)
        communication_task = self._generate_communication_task(booking, prop)
        tasks.append(communication_task)

        # Generate RESTOCKING task if high occupancy
        if booking.guest_count > prop.max_guests * 0.8:
            restocking_task = self._generate_restocking_task(booking, prop)
            tasks.append(restocking_task)

        logger.info(
            f"Generated {len(tasks)} tasks for booking {booking.id} "
            f"(tight_turnover={is_tight_turnover})"
        )

        return tasks

    def _generate_cleaning_task(
        self,
        booking: AirbnbBooking,
        prop: Property,
        is_tight_turnover: bool,
    ) -> GeneratedTask:
        """Generate a cleaning task for checkout."""
        # Calculate duration based on bedrooms
        bedrooms = min(prop.bedrooms, 4)  # Cap at 4 for lookup
        duration = self.CLEANING_DURATION.get(bedrooms, 5.0)

        # Add extra time for tight turnovers
        if is_tight_turnover:
            duration *= 0.9  # Faster but still thorough

        # Calculate budget with buffer
        budget = prop.cleaning_budget * (1 + self.buffer_percentage)

        description = (
            f"Turnover cleaning for {prop.name}: "
            f"{prop.bedrooms}BR/{prop.bathrooms}BA. "
            f"Checkout at {prop.default_checkout_time.strftime('%I:%M %p')}."
        )

        if is_tight_turnover:
            description += " TIGHT TURNOVER - prioritize speed."

        if booking.notes:
            description += f" Guest notes: {booking.notes}"

        return GeneratedTask(
            type=TaskType.CLEANING,
            property_id=prop.id,
            booking_id=booking.id,
            description=description,
            required_skills=["cleaning"],
            budget=budget,
            scheduled_date=booking.checkout_date,
            scheduled_time=prop.default_checkout_time,
            duration_hours=duration,
            checklist=self.DEFAULT_CHECKLISTS[TaskType.CLEANING].copy(),
            is_tight_turnover=is_tight_turnover,
            host_notes=(
                "Tight turnover - prioritize highest-rated cleaner"
                if is_tight_turnover
                else None
            ),
        )

    def _generate_communication_task(
        self,
        booking: AirbnbBooking,
        prop: Property,
    ) -> GeneratedTask:
        """Generate a communication task for checkin (24h before)."""
        # Schedule 24 hours before checkin
        scheduled_date = booking.checkin_date - timedelta(days=1)
        if scheduled_date < date.today():
            scheduled_date = date.today()

        description = (
            f"Send welcome message to {booking.guest_name} for "
            f"{prop.name}. Check-in: {booking.checkin_date.strftime('%B %d')} "
            f"at {prop.default_checkin_time.strftime('%I:%M %p')}."
        )

        return GeneratedTask(
            type=TaskType.COMMUNICATION,
            property_id=prop.id,
            booking_id=booking.id,
            description=description,
            required_skills=[],  # Can be automated
            budget=0.0,  # Usually automated/free
            scheduled_date=scheduled_date,
            scheduled_time=time(9, 0),  # 9 AM
            duration_hours=0.25,  # 15 minutes
            checklist=self.DEFAULT_CHECKLISTS[TaskType.COMMUNICATION].copy(),
        )

    def _generate_restocking_task(
        self,
        booking: AirbnbBooking,
        prop: Property,
    ) -> GeneratedTask:
        """Generate a restocking task for high-occupancy stays."""
        # Schedule on checkout day, after cleaning
        checkout_dt = datetime.combine(
            booking.checkout_date, prop.default_checkout_time
        )

        # Calculate cleaning duration to schedule restocking after
        bedrooms = min(prop.bedrooms, 4)
        cleaning_duration = self.CLEANING_DURATION.get(bedrooms, 5.0)

        restocking_time = (
            checkout_dt + timedelta(hours=cleaning_duration)
        ).time()

        description = (
            f"Restock supplies for {prop.name}. "
            f"High occupancy stay ({booking.guest_count} guests). "
            f"Check all consumables and replace as needed."
        )

        return GeneratedTask(
            type=TaskType.RESTOCKING,
            property_id=prop.id,
            booking_id=booking.id,
            description=description,
            required_skills=["organizing"],
            budget=50.0,  # Fixed budget for restocking
            scheduled_date=booking.checkout_date,
            scheduled_time=restocking_time,
            duration_hours=1.0,
            checklist=self.DEFAULT_CHECKLISTS[TaskType.RESTOCKING].copy(),
        )

    def _calculate_turnover_gap(
        self,
        checkout_date: date,
        checkout_time: time,
        checkin_date: date,
        checkin_time: time,
    ) -> timedelta:
        """Calculate the time gap between checkout and next checkin."""
        checkout_dt = datetime.combine(checkout_date, checkout_time)
        checkin_dt = datetime.combine(checkin_date, checkin_time)
        return checkin_dt - checkout_dt


# Default instance
_default_generator: TaskGenerator | None = None


def get_task_generator() -> TaskGenerator:
    """Get or create the default task generator instance."""
    global _default_generator
    if _default_generator is None:
        _default_generator = TaskGenerator()
    return _default_generator
