"""
Async RentAHuman API Client.

Provides asynchronous methods to interact with the RentAHuman API
for searching humans and creating bookings.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class Human:
    """Represents a human available for hire."""

    id: str
    name: str
    skills: list[str]
    location: str
    rate: float
    currency: str = "USD"
    rating: float = 4.5
    reviews: int = 0
    availability: str = "available"
    bio: str = ""
    photo_url: str | None = None


@dataclass
class Booking:
    """Represents a RentAHuman booking."""

    id: str
    human_id: str
    human_name: str
    task_description: str
    start_time: str
    end_time: str
    budget: float
    status: str  # pending, confirmed, in_progress, completed, cancelled
    total_cost: float = 0.0


class RentAHumanClient:
    """
    Async client for RentAHuman API.

    Supports both real API calls and mock mode for development/testing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        mock_mode: bool | None = None,
    ):
        """
        Initialize the RentAHuman client.

        Args:
            api_key: RentAHuman API key (defaults to settings)
            base_url: RentAHuman API base URL (defaults to settings)
            mock_mode: Enable mock mode for testing (defaults to settings)
        """
        self.api_key = api_key or settings.rentahuman_api_key
        self.base_url = base_url or settings.rentahuman_base_url
        self.mock_mode = (
            mock_mode if mock_mode is not None else settings.rentahuman_mock_mode
        )
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AirbnbAutomation/1.0",
        }

    async def search_humans(
        self,
        location: str,
        skill: str | None = None,
        availability: str | None = None,
        budget_max: float | None = None,
        rating_min: float | None = 3.0,
        limit: int = 10,
    ) -> list[Human]:
        """
        Search for available humans by location and criteria.

        Args:
            location: City, state or ZIP code (e.g., "Las Vegas, NV")
            skill: Skill filter (e.g., "cleaning", "handyman")
            availability: "available", "next_24h", "next_week", "flexible"
            budget_max: Maximum hourly rate in USD
            rating_min: Minimum rating (3.0-5.0)
            limit: Maximum results (1-100)

        Returns:
            List of Human objects matching criteria
        """
        if self.mock_mode:
            return self._mock_search_humans(location, skill, budget_max, rating_min)

        params = {
            "location": location,
            "limit": min(limit, 100),
        }
        if skill:
            params["skill"] = skill
        if availability:
            params["availability"] = availability
        if budget_max:
            params["budget_max"] = budget_max
        if rating_min:
            params["rating_min"] = rating_min

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/humans/search",
                    params=params,
                    headers=self._get_headers(),
                )
                response.raise_for_status()

                data = response.json()
                humans = [Human(**h) for h in data.get("humans", [])]

                logger.info(
                    f"Found {len(humans)} humans in {location} "
                    f"(skill={skill}, budget_max={budget_max})"
                )
                return humans

        except httpx.HTTPError as e:
            logger.error(f"Error searching humans: {e}")
            return []

    async def create_booking(
        self,
        human_id: str,
        task_description: str,
        start_time: str,
        end_time: str,
        budget: float,
        special_requests: str | None = None,
    ) -> Booking | None:
        """
        Create a booking for a human.

        Args:
            human_id: ID of the human to book
            task_description: Detailed description of the task
            start_time: ISO 8601 datetime (e.g., "2026-02-25T09:00:00Z")
            end_time: ISO 8601 datetime
            budget: Maximum budget in USD
            special_requests: Special instructions

        Returns:
            Booking object if successful, None otherwise
        """
        if self.mock_mode:
            return self._mock_create_booking(human_id, task_description, budget)

        payload = {
            "human_id": human_id,
            "task_description": task_description,
            "start_time": start_time,
            "end_time": end_time,
            "budget": budget,
        }
        if special_requests:
            payload["special_requests"] = special_requests

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/bookings",
                        json=payload,
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()

                    data = response.json()
                    booking = Booking(**data)

                    logger.info(
                        f"Booking created: {booking.id} for human {booking.human_name}"
                    )
                    return booking

            except httpx.HTTPError as e:
                logger.warning(
                    f"Booking attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    import asyncio

                    await asyncio.sleep(self.retry_delay * (2**attempt))

        logger.error(f"Failed to create booking after {self.max_retries} attempts")
        return None

    async def get_booking_status(self, booking_id: str) -> dict[str, Any] | None:
        """
        Get the status of a booking.

        Args:
            booking_id: ID of the booking to check

        Returns:
            Booking details dictionary, or None if error
        """
        if self.mock_mode:
            return self._mock_get_booking_status(booking_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/bookings/{booking_id}",
                    headers=self._get_headers(),
                )
                response.raise_for_status()

                data = response.json()
                logger.info(f"Booking {booking_id} status: {data.get('status')}")
                return data

        except httpx.HTTPError as e:
            logger.error(f"Error getting booking status: {e}")
            return None

    async def list_skills(self) -> list[dict[str, str]]:
        """
        Get list of all available skills.

        Returns:
            List of skill dictionaries with name and description
        """
        if self.mock_mode:
            return self._mock_list_skills()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/skills",
                    headers=self._get_headers(),
                )
                response.raise_for_status()

                data = response.json()
                logger.info(f"Found {len(data)} available skills")
                return data

        except httpx.HTTPError as e:
            logger.error(f"Error listing skills: {e}")
            return []

    async def cancel_booking(
        self, booking_id: str, reason: str | None = None
    ) -> bool:
        """
        Cancel an existing booking.

        Args:
            booking_id: ID of the booking to cancel
            reason: Reason for cancellation

        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode:
            logger.info(f"Mock: Booking {booking_id} cancelled")
            return True

        payload = {}
        if reason:
            payload["reason"] = reason

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/bookings/{booking_id}/cancel",
                    json=payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()

                logger.info(f"Booking {booking_id} cancelled")
                return True

        except httpx.HTTPError as e:
            logger.error(f"Error cancelling booking: {e}")
            return False

    async def get_human(self, human_id: str) -> Human | None:
        """
        Get a specific human's profile.

        Args:
            human_id: ID of the human

        Returns:
            Human object if found, None otherwise
        """
        if self.mock_mode:
            return self._mock_get_human(human_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/humans/{human_id}",
                    headers=self._get_headers(),
                )
                response.raise_for_status()

                data = response.json()
                return Human(**data)

        except httpx.HTTPError as e:
            logger.error(f"Error getting human: {e}")
            return None

    # Mock methods for testing/development
    def _mock_search_humans(
        self,
        location: str,
        skill: str | None = None,
        budget_max: float | None = None,
        rating_min: float | None = None,
    ) -> list[Human]:
        """Mock search results for testing."""
        mock_humans = [
            Human(
                id="human_001",
                name="Maria Garcia",
                skills=["cleaning", "organizing"],
                location=location,
                rate=25.0,
                rating=4.8,
                reviews=127,
                bio="Professional cleaner with 8 years experience",
            ),
            Human(
                id="human_002",
                name="John Smith",
                skills=["handyman", "maintenance", "repairs"],
                location=location,
                rate=35.0,
                rating=4.6,
                reviews=89,
                bio="Licensed handyman, all repairs welcome",
            ),
            Human(
                id="human_003",
                name="Alex Chen",
                skills=["photography", "videography"],
                location=location,
                rate=50.0,
                rating=4.9,
                reviews=156,
                bio="Professional photographer, Airbnb listing specialist",
            ),
            Human(
                id="human_004",
                name="Sarah Johnson",
                skills=["cleaning", "deep_cleaning"],
                location=location,
                rate=30.0,
                rating=4.7,
                reviews=203,
                availability="next_24h",
                bio="Deep cleaning specialist",
            ),
            Human(
                id="human_005",
                name="Mike Williams",
                skills=["handyman", "plumbing", "electrical"],
                location=location,
                rate=45.0,
                rating=4.5,
                reviews=67,
                bio="Certified electrician and plumber",
            ),
        ]

        # Apply filters
        if skill:
            mock_humans = [
                h for h in mock_humans if skill.lower() in [s.lower() for s in h.skills]
            ]
        if budget_max:
            mock_humans = [h for h in mock_humans if h.rate <= budget_max]
        if rating_min:
            mock_humans = [h for h in mock_humans if h.rating >= rating_min]

        logger.info(f"Mock: Found {len(mock_humans)} humans")
        return mock_humans

    def _mock_create_booking(
        self, human_id: str, task_description: str, budget: float
    ) -> Booking:
        """Mock booking creation for testing."""
        booking = Booking(
            id=f"booking_{datetime.now().timestamp()}",
            human_id=human_id,
            human_name="Mock Human",
            task_description=task_description,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            budget=budget,
            status="confirmed",
            total_cost=budget * 0.95,  # 5% platform fee
        )
        logger.info(f"Mock: Booking created {booking.id}")
        return booking

    def _mock_get_booking_status(self, booking_id: str) -> dict[str, Any]:
        """Mock booking status check."""
        return {
            "id": booking_id,
            "status": "confirmed",
            "human_name": "Mock Human",
            "task": "Mock task",
            "total_cost": 150.0,
            "completion_photos": [],
            "human_feedback": None,
        }

    def _mock_list_skills(self) -> list[dict[str, str]]:
        """Mock skills list."""
        return [
            {"name": "cleaning", "description": "Household and commercial cleaning"},
            {"name": "handyman", "description": "General repairs and maintenance"},
            {"name": "photography", "description": "Professional photography services"},
            {"name": "moving", "description": "Moving and packing assistance"},
            {"name": "organizing", "description": "Organizing and decluttering"},
            {"name": "deep_cleaning", "description": "Deep cleaning services"},
            {"name": "plumbing", "description": "Plumbing repairs"},
            {"name": "electrical", "description": "Electrical work"},
        ]

    def _mock_get_human(self, human_id: str) -> Human:
        """Mock get human."""
        return Human(
            id=human_id,
            name="Mock Human",
            skills=["cleaning"],
            location="Las Vegas, NV",
            rate=25.0,
            rating=4.5,
            reviews=50,
            bio="Mock human for testing",
        )


# Create a default client instance
_default_client: RentAHumanClient | None = None


def get_rentahuman_client() -> RentAHumanClient:
    """Get or create the default RentAHuman client instance."""
    global _default_client
    if _default_client is None:
        _default_client = RentAHumanClient()
    return _default_client
