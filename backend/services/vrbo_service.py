"""
VRBO API integration service.

Similar to Airbnb service, provides mock data for development
and skeleton for potential real implementation.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class VRBOBookingData:
    """Raw booking data from VRBO."""

    external_id: str  # VRBO's booking ID
    guest_name: str
    checkin_date: date
    checkout_date: date
    guest_count: int
    total_price: float
    notes: str | None = None


class VRBOService:
    """
    Service for fetching booking data from VRBO.

    Provides mock data by default. Real implementation would use
    official API or web scraping as fallback.
    """

    def __init__(self, mock_mode: bool = True):
        """
        Initialize the VRBO service.

        Args:
            mock_mode: Use mock data instead of real API calls
        """
        self.mock_mode = mock_mode
        self._mock_bookings_cache: dict[str, list[VRBOBookingData]] = {}
        if self.mock_mode:
            logger.warning(
                "⚠️  VRBOService running in MOCK MODE — returning synthetic data. "
                "Set RENTAHUMAN_MOCK_MODE=false for real VRBO integration."
            )

    async def fetch_bookings(
        self,
        listing_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[VRBOBookingData]:
        """
        Fetch bookings for a listing.

        Args:
            listing_id: VRBO listing ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of booking data
        """
        if self.mock_mode:
            return self._generate_mock_bookings(listing_id, start_date, end_date)

        # Try iCal integration if an ical_url is provided
        if ical_url := getattr(self, '_current_ical_url', None):
            return await self._fetch_via_ical(ical_url, listing_id, start_date, end_date)

        raise NotImplementedError(
            "Real VRBO API integration is not yet implemented. "
            "Set RENTAHUMAN_MOCK_MODE=true for development, or implement "
            "_fetch_via_api() with proper VRBO API credentials."
        )

    async def get_booking(
        self, listing_id: str, booking_id: str
    ) -> VRBOBookingData | None:
        """
        Get a specific booking by ID.

        Args:
            listing_id: VRBO listing ID
            booking_id: VRBO booking ID

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
    ) -> list[VRBOBookingData]:
        """
        Sync bookings and return only new ones.

        Args:
            listing_id: VRBO listing ID
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
                f"Found {len(new_bookings)} new VRBO bookings for listing {listing_id}"
            )

        return new_bookings

    def _generate_mock_bookings(
        self,
        listing_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[VRBOBookingData]:
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

    def _create_mock_bookings(self, listing_id: str) -> list[VRBOBookingData]:
        """Create a set of realistic mock bookings."""
        today = date.today()
        guest_names = [
            "James Wilson",
            "Patricia Moore",
            "Christopher Lee",
            "Barbara Taylor",
            "Daniel Harris",
            "Susan Clark",
            "Matthew Lewis",
            "Nancy Walker",
            "Anthony Hall",
            "Karen Young",
        ]

        bookings = []

        # VRBO typically has fewer but longer bookings
        current_date = today + timedelta(days=5)  # Start 5 days from now
        booking_num = 0

        while current_date < today + timedelta(days=90) and booking_num < 6:
            # VRBO tends to have longer stays (3-10 nights)
            stay_length = 3 + (hash(f"vrbo_{listing_id}_{booking_num}") % 8)
            checkout_date = current_date + timedelta(days=stay_length)

            # Random guest count (2-6 for VRBO which tends toward families)
            guest_count = 2 + (hash(f"vrbo_{listing_id}_{booking_num}_guests") % 5)

            # Price typically higher for VRBO
            total_price = stay_length * 200.0 + (guest_count * 30.0)

            booking = VRBOBookingData(
                external_id=f"vrbo_{listing_id}_{booking_num}_{current_date.isoformat()}",
                guest_name=guest_names[booking_num % len(guest_names)],
                checkin_date=current_date,
                checkout_date=checkout_date,
                guest_count=guest_count,
                total_price=total_price,
                notes=self._generate_mock_notes(booking_num),
            )
            bookings.append(booking)

            # Larger gaps for VRBO (3-10 days)
            gap = 3 + (hash(f"vrbo_{listing_id}_{booking_num}_gap") % 8)
            current_date = checkout_date + timedelta(days=gap)
            booking_num += 1

        logger.info(f"Generated {len(bookings)} mock VRBO bookings for {listing_id}")
        return bookings

    def _generate_mock_notes(self, booking_num: int) -> str | None:
        """Generate mock booking notes."""
        notes_options = [
            None,
            None,
            "Family reunion",
            "Anniversary trip",
            "Need 2 high chairs",
            "Will have pet dog",
        ]
        return notes_options[booking_num % len(notes_options)]

    async def fetch_bookings_with_ical(
        self,
        listing_id: str,
        ical_url: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[VRBOBookingData]:
        """
        Fetch bookings using an iCal feed URL.

        Args:
            listing_id: VRBO listing ID
            ical_url: iCal feed URL
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of booking data
        """
        return await self._fetch_via_ical(ical_url, listing_id, start_date, end_date)

    async def _fetch_via_ical(
        self,
        ical_url: str,
        listing_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[VRBOBookingData]:
        """
        Fetch bookings via iCal feed.

        Args:
            ical_url: iCal feed URL
            listing_id: VRBO listing ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of VRBOBookingData
        """
        from services.ical_service import get_ical_service

        ical_service = get_ical_service()
        ical_bookings = await ical_service.fetch_and_parse(ical_url)
        bookings = ical_service.to_vrbo_bookings(ical_bookings, listing_id)

        # Apply date filters
        if start_date:
            bookings = [b for b in bookings if b.checkin_date >= start_date]
        if end_date:
            bookings = [b for b in bookings if b.checkout_date <= end_date]

        logger.info(
            f"Fetched {len(bookings)} VRBO bookings via iCal for listing {listing_id}"
        )
        return bookings

    async def _fetch_via_api(
        self,
        listing_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[VRBOBookingData]:
        """
        Fetch bookings via VRBO API.

        TODO: Implement actual VRBO API integration.
        This is a placeholder skeleton.
        """
        logger.warning(
            "VRBO API not implemented. "
            "Set RENTAHUMAN_MOCK_MODE=true for development."
        )

        # Skeleton for VRBO API implementation:
        #
        # import httpx
        #
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"https://api.vrbo.com/v1/listings/{listing_id}/reservations",
        #         headers={"Authorization": f"Bearer {api_key}"},
        #     )
        #     data = response.json()
        #     return [VRBOBookingData(**b) for b in data["reservations"]]

        return []


# Default service instance
_default_service: VRBOService | None = None


def get_vrbo_service() -> VRBOService:
    """Get or create the default VRBO service instance."""
    global _default_service
    if _default_service is None:
        from config import settings

        _default_service = VRBOService(mock_mode=settings.rentahuman_mock_mode)
    return _default_service
