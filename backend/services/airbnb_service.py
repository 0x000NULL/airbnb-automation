"""
Airbnb API integration service.

Since there's no official public Airbnb API, this service provides:
1. Mock data for development/testing
2. Selenium scraper skeleton for potential real implementation
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class AirbnbBookingData:
    """Raw booking data from Airbnb."""

    external_id: str  # Airbnb's booking ID
    guest_name: str
    checkin_date: date
    checkout_date: date
    guest_count: int
    total_price: float
    notes: str | None = None


class AirbnbService:
    """
    Service for fetching booking data from Airbnb.

    Provides mock data by default. Real implementation would use
    official API (if available) or web scraping as fallback.
    """

    def __init__(self, mock_mode: bool = True):
        """
        Initialize the Airbnb service.

        Args:
            mock_mode: Use mock data instead of real API calls
        """
        self.mock_mode = mock_mode
        self._mock_bookings_cache: dict[str, list[AirbnbBookingData]] = {}

    async def fetch_bookings(
        self,
        listing_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AirbnbBookingData]:
        """
        Fetch bookings for a listing.

        Args:
            listing_id: Airbnb listing ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of booking data
        """
        if self.mock_mode:
            return self._generate_mock_bookings(listing_id, start_date, end_date)

        # TODO: Implement real Airbnb API or scraping
        return await self._fetch_via_selenium(listing_id, start_date, end_date)

    async def get_booking(
        self, listing_id: str, booking_id: str
    ) -> AirbnbBookingData | None:
        """
        Get a specific booking by ID.

        Args:
            listing_id: Airbnb listing ID
            booking_id: Airbnb booking ID

        Returns:
            Booking data if found
        """
        bookings = await self.fetch_bookings(listing_id)
        for booking in bookings:
            if booking.external_id == booking_id:
                return booking
        return None

    async def sync_bookings(
        self,
        listing_id: str,
        property_id: UUID,
        existing_booking_ids: set[str],
    ) -> list[AirbnbBookingData]:
        """
        Sync bookings and return only new ones.

        Args:
            listing_id: Airbnb listing ID
            property_id: Internal property UUID
            existing_booking_ids: Set of already-known external IDs

        Returns:
            List of new bookings not in existing_booking_ids
        """
        all_bookings = await self.fetch_bookings(listing_id)
        new_bookings = [
            b for b in all_bookings if b.external_id not in existing_booking_ids
        ]

        if new_bookings:
            logger.info(
                f"Found {len(new_bookings)} new Airbnb bookings for listing {listing_id}"
            )

        return new_bookings

    def _generate_mock_bookings(
        self,
        listing_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AirbnbBookingData]:
        """Generate mock booking data for testing."""
        # Use cached bookings if available (for consistency)
        if listing_id in self._mock_bookings_cache:
            bookings = self._mock_bookings_cache[listing_id]
        else:
            # Generate new mock bookings
            bookings = self._create_mock_bookings(listing_id)
            self._mock_bookings_cache[listing_id] = bookings

        # Filter by date range
        if start_date:
            bookings = [b for b in bookings if b.checkin_date >= start_date]
        if end_date:
            bookings = [b for b in bookings if b.checkout_date <= end_date]

        return bookings

    def _create_mock_bookings(self, listing_id: str) -> list[AirbnbBookingData]:
        """Create a set of realistic mock bookings."""
        today = date.today()
        guest_names = [
            "John Smith",
            "Emily Johnson",
            "Michael Brown",
            "Sarah Davis",
            "David Wilson",
            "Jennifer Martinez",
            "Robert Anderson",
            "Lisa Thomas",
            "William Taylor",
            "Maria Garcia",
        ]

        bookings = []

        # Generate bookings for the next 60 days
        current_date = today + timedelta(days=2)  # Start 2 days from now
        booking_num = 0

        while current_date < today + timedelta(days=60) and booking_num < 10:
            # Random stay length (2-7 nights)
            stay_length = 2 + (hash(f"{listing_id}_{booking_num}") % 6)
            checkout_date = current_date + timedelta(days=stay_length)

            # Random guest count (1-4)
            guest_count = 1 + (hash(f"{listing_id}_{booking_num}_guests") % 4)

            # Price based on stay length
            total_price = stay_length * 150.0 + (guest_count * 25.0)

            booking = AirbnbBookingData(
                external_id=f"airbnb_{listing_id}_{booking_num}_{current_date.isoformat()}",
                guest_name=guest_names[booking_num % len(guest_names)],
                checkin_date=current_date,
                checkout_date=checkout_date,
                guest_count=guest_count,
                total_price=total_price,
                notes=self._generate_mock_notes(booking_num),
            )
            bookings.append(booking)

            # Gap between bookings (1-5 days for turnover + vacancy)
            gap = 1 + (hash(f"{listing_id}_{booking_num}_gap") % 5)
            current_date = checkout_date + timedelta(days=gap)
            booking_num += 1

        logger.info(f"Generated {len(bookings)} mock Airbnb bookings for {listing_id}")
        return bookings

    def _generate_mock_notes(self, booking_num: int) -> str | None:
        """Generate mock booking notes."""
        notes_options = [
            None,
            None,
            None,  # Many bookings have no notes
            "Late arrival after 10pm",
            "Will have 1 small dog",
            "Celebrating anniversary",
            "Need early check-in if possible",
            "Business trip, quiet hours appreciated",
            "Family vacation with 2 children",
        ]
        return notes_options[booking_num % len(notes_options)]

    async def _fetch_via_selenium(
        self,
        listing_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AirbnbBookingData]:
        """
        Fetch bookings via Selenium web scraping.

        TODO: Implement actual Selenium scraping logic.
        This is a placeholder skeleton.
        """
        logger.warning(
            "Selenium scraping not implemented. "
            "Set RENTAHUMAN_MOCK_MODE=true for development."
        )

        # Skeleton for Selenium implementation:
        #
        # from selenium import webdriver
        # from selenium.webdriver.common.by import By
        # from selenium.webdriver.support.ui import WebDriverWait
        # from selenium.webdriver.support import expected_conditions as EC
        #
        # async def _scrape():
        #     options = webdriver.ChromeOptions()
        #     options.add_argument('--headless')
        #     driver = webdriver.Chrome(options=options)
        #
        #     try:
        #         # Login to Airbnb host dashboard
        #         driver.get('https://www.airbnb.com/hosting/reservations')
        #
        #         # Wait for and enter credentials
        #         # ...
        #
        #         # Navigate to reservations
        #         # Parse booking data
        #         # ...
        #
        #     finally:
        #         driver.quit()

        return []


# Default service instance
_default_service: AirbnbService | None = None


def get_airbnb_service() -> AirbnbService:
    """Get or create the default Airbnb service instance."""
    global _default_service
    if _default_service is None:
        from config import settings

        _default_service = AirbnbService(mock_mode=settings.rentahuman_mock_mode)
    return _default_service
