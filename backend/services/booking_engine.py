"""
Booking engine service.

Matches tasks to humans via RentAHuman and creates bookings.
Includes retry logic, fallbacks, and cost optimization.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from models.automation_config import AutomationConfig, HumanPreference
from models.property import Property
from models.task import Task, TaskStatus, TaskType
from services.rentahuman_client import Booking, Human, RentAHumanClient

logger = logging.getLogger(__name__)


@dataclass
class BookingResult:
    """Result of a booking attempt."""

    success: bool
    booking_id: str | None = None
    human: Human | None = None
    error: str | None = None
    total_cost: float = 0.0


class BookingEngine:
    """
    Engine for matching tasks to humans and creating bookings.

    Features:
    - Multiple retry attempts with exponential backoff
    - Fallback: expand search if no humans available
    - Cost optimization based on urgency
    - Duplicate prevention
    """

    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1.0  # seconds
    SEARCH_RADIUS_EXPANSION = 25  # miles
    BUDGET_EXPANSION_PERCENT = 0.2  # 20%

    def __init__(self, client: RentAHumanClient | None = None):
        """
        Initialize the booking engine.

        Args:
            client: RentAHuman client (creates default if not provided)
        """
        from services.rentahuman_client import get_rentahuman_client

        self.client = client or get_rentahuman_client()

    async def book_task(
        self,
        task: Task,
        prop: Property,
        config: AutomationConfig,
    ) -> BookingResult:
        """
        Book a human for a task.

        Args:
            task: The task to book
            prop: The property for this task
            config: User's automation config

        Returns:
            BookingResult with success status and details
        """
        # Check for duplicate booking
        if task.rentahuman_booking_id:
            logger.warning(f"Task {task.id} already has booking {task.rentahuman_booking_id}")
            return BookingResult(
                success=False,
                error="Task already booked",
            )

        # Get search parameters
        location = prop.full_address
        skill = self._get_skill_for_task_type(task.type)
        budget = task.budget

        # Determine preference based on urgency
        preference = self._get_preference_for_task(task, config)

        # Try to find and book a human
        for attempt in range(self.MAX_RETRIES):
            try:
                result = await self._attempt_booking(
                    task=task,
                    location=location,
                    skill=skill,
                    budget=budget,
                    rating_min=config.minimum_human_rating,
                    preference=preference,
                )

                if result.success:
                    logger.info(
                        f"Successfully booked task {task.id} "
                        f"with human {result.human.name if result.human else 'unknown'}"
                    )
                    return result

                # If no humans found, try fallback
                if "no humans" in (result.error or "").lower():
                    logger.info(f"No humans found, trying fallback for task {task.id}")
                    result = await self._attempt_fallback_booking(
                        task=task,
                        location=location,
                        skill=skill,
                        budget=budget,
                        preference=preference,
                    )
                    if result.success:
                        return result

            except Exception as e:
                logger.error(f"Booking attempt {attempt + 1} failed: {e}")

            # Exponential backoff
            if attempt < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAY_BASE * (2**attempt)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        return BookingResult(
            success=False,
            error=f"Failed after {self.MAX_RETRIES} attempts",
        )

    async def _attempt_booking(
        self,
        task: Task,
        location: str,
        skill: str | None,
        budget: float,
        rating_min: float,
        preference: HumanPreference,
    ) -> BookingResult:
        """Attempt to find and book a human."""
        # Search for humans
        humans = await self.client.search_humans(
            location=location,
            skill=skill,
            budget_max=budget / task.duration_hours,  # Convert to hourly
            rating_min=rating_min,
            limit=20,
        )

        if not humans:
            return BookingResult(
                success=False,
                error="No humans found matching criteria",
            )

        # Rank and select best human
        best_human = self._select_best_human(humans, preference)

        # Create booking
        scheduled_dt = datetime.combine(task.scheduled_date, task.scheduled_time)
        end_dt = scheduled_dt + timedelta(hours=task.duration_hours)

        booking = await self.client.create_booking(
            human_id=best_human.id,
            task_description=task.description,
            start_time=scheduled_dt.isoformat(),
            end_time=end_dt.isoformat(),
            budget=budget,
            special_requests=task.host_notes,
        )

        if not booking:
            return BookingResult(
                success=False,
                error="Failed to create booking",
            )

        return BookingResult(
            success=True,
            booking_id=booking.id,
            human=best_human,
            total_cost=booking.total_cost,
        )

    async def _attempt_fallback_booking(
        self,
        task: Task,
        location: str,
        skill: str | None,
        budget: float,
        preference: HumanPreference,
    ) -> BookingResult:
        """
        Attempt booking with expanded criteria.

        - Expand search radius by 25 miles
        - Increase budget by 20%
        """
        expanded_budget = budget * (1 + self.BUDGET_EXPANSION_PERCENT)

        logger.info(
            f"Fallback: Expanding budget to ${expanded_budget:.2f} "
            f"and searching wider area"
        )

        # Search with expanded criteria (lower rating requirement)
        humans = await self.client.search_humans(
            location=location,
            skill=skill,
            budget_max=expanded_budget / task.duration_hours,
            rating_min=3.5,  # Lower rating requirement
            limit=50,
        )

        if not humans:
            return BookingResult(
                success=False,
                error="No humans found even with expanded search",
            )

        # Select best from expanded results
        best_human = self._select_best_human(humans, preference)

        # Create booking with expanded budget
        scheduled_dt = datetime.combine(task.scheduled_date, task.scheduled_time)
        end_dt = scheduled_dt + timedelta(hours=task.duration_hours)

        booking = await self.client.create_booking(
            human_id=best_human.id,
            task_description=task.description + " [EXPANDED SEARCH]",
            start_time=scheduled_dt.isoformat(),
            end_time=end_dt.isoformat(),
            budget=expanded_budget,
            special_requests=task.host_notes,
        )

        if not booking:
            return BookingResult(
                success=False,
                error="Failed to create fallback booking",
            )

        return BookingResult(
            success=True,
            booking_id=booking.id,
            human=best_human,
            total_cost=booking.total_cost,
        )

    def _select_best_human(
        self,
        humans: list[Human],
        preference: HumanPreference,
    ) -> Human:
        """
        Select the best human based on preference.

        Args:
            humans: List of available humans
            preference: Selection preference

        Returns:
            Best matching human
        """
        if not humans:
            raise ValueError("No humans to select from")

        if preference == HumanPreference.CHEAPEST:
            return min(humans, key=lambda h: h.rate)
        elif preference == HumanPreference.HIGHEST_RATED:
            return max(humans, key=lambda h: (h.rating, h.reviews))
        elif preference == HumanPreference.NEAREST:
            # In a real implementation, would sort by distance
            # For now, prefer first result (API usually returns nearest first)
            return humans[0]
        else:
            # Default to highest rated
            return max(humans, key=lambda h: h.rating)

    def _get_preference_for_task(
        self,
        task: Task,
        config: AutomationConfig,
    ) -> HumanPreference:
        """
        Determine preference based on task type and urgency.

        Rules:
        - Urgent tasks (<24h): prefer highest_rated
        - Non-urgent (>48h): prefer cheapest
        - Otherwise: use user's configured preference
        """
        if task.is_urgent:
            # Urgent: prioritize quality
            return HumanPreference.HIGHEST_RATED

        # Check time until task
        scheduled_dt = datetime.combine(task.scheduled_date, task.scheduled_time)
        hours_until = (scheduled_dt - datetime.now()).total_seconds() / 3600

        if hours_until > 48:
            # Non-urgent: can optimize for cost
            return HumanPreference.CHEAPEST

        # Use configured preference
        if task.type == TaskType.CLEANING:
            return config.cleaning_preference
        elif task.type == TaskType.MAINTENANCE:
            return config.maintenance_preference
        else:
            return config.cleaning_preference  # Default

    def _get_skill_for_task_type(self, task_type: TaskType) -> str | None:
        """Map task type to required skill."""
        skill_map = {
            TaskType.CLEANING: "cleaning",
            TaskType.MAINTENANCE: "handyman",
            TaskType.PHOTOGRAPHY: "photography",
            TaskType.RESTOCKING: "organizing",
            TaskType.COMMUNICATION: None,  # No specific skill needed
        }
        return skill_map.get(task_type)

    async def handle_cancellation(
        self,
        task: Task,
        prop: Property,
        config: AutomationConfig,
    ) -> BookingResult:
        """
        Handle a human cancellation by finding a replacement.

        Args:
            task: The task that needs a new human
            prop: The property
            config: User's automation config

        Returns:
            BookingResult for the replacement booking
        """
        logger.warning(f"Handling cancellation for task {task.id}")

        # Clear previous booking
        old_booking_id = task.rentahuman_booking_id
        task.rentahuman_booking_id = None
        task.assigned_human = None
        task.status = TaskStatus.PENDING

        # Try to book a replacement
        result = await self.book_task(task, prop, config)

        if result.success:
            logger.info(
                f"Replacement found for task {task.id}: "
                f"{result.human.name if result.human else 'unknown'}"
            )
        else:
            logger.error(f"Failed to find replacement for task {task.id}")

        return result


# Default instance
_default_engine: BookingEngine | None = None


def get_booking_engine() -> BookingEngine:
    """Get or create the default booking engine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = BookingEngine()
    return _default_engine
