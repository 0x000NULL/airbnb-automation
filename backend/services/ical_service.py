"""
iCal integration service for importing bookings from Airbnb/VRBO calendar feeds.

Both Airbnb and VRBO export .ics calendar URLs for each listing.
This service parses those feeds and returns booking data compatible
with the existing AirbnbBookingData / VRBOBookingData dataclasses.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx
from icalendar import Calendar

from services.airbnb_service import AirbnbBookingData
from services.vrbo_service import VRBOBookingData

logger = logging.getLogger(__name__)


@dataclass
class ICalBookingData:
    """Parsed booking data from an iCal VEVENT."""

    uid: str
    summary: str
    checkin_date: date
    checkout_date: date
    description: str | None = None


class ICalService:
    """
    Service for fetching and parsing iCal (.ics) calendar feeds.

    Airbnb and VRBO both provide iCal export URLs for each listing.
    This service fetches the feed, parses VEVENT entries, and returns
    booking data compatible with the existing booking dataclasses.
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def fetch_and_parse(self, ical_url: str) -> list[ICalBookingData]:
        """
        Fetch an iCal feed from a URL and parse bookings.

        Args:
            ical_url: URL to the .ics calendar feed

        Returns:
            List of parsed booking data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(ical_url)
                response.raise_for_status()
                return self.parse_ics_content(response.text)
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch iCal feed from {ical_url}: {e}")
            raise ValueError(f"Failed to fetch iCal feed: {e}") from e

    def parse_ics_content(self, ics_content: str) -> list[ICalBookingData]:
        """
        Parse raw .ics content into booking data.

        Args:
            ics_content: Raw iCalendar content string

        Returns:
            List of parsed booking data
        """
        bookings: list[ICalBookingData] = []

        try:
            cal = Calendar.from_ical(ics_content)
        except Exception as e:
            logger.error(f"Failed to parse iCal content: {e}")
            raise ValueError(f"Invalid iCal content: {e}") from e

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            try:
                booking = self._parse_vevent(component)
                if booking:
                    bookings.append(booking)
            except Exception as e:
                summary = str(component.get("SUMMARY", "unknown"))
                logger.warning(f"Skipping malformed VEVENT '{summary}': {e}")
                continue

        logger.info(f"Parsed {len(bookings)} bookings from iCal feed")
        return bookings

    def _parse_vevent(self, component) -> ICalBookingData | None:
        """Parse a single VEVENT component into booking data."""
        # Extract UID
        uid = str(component.get("UID", ""))
        if not uid:
            # Generate a UID from summary + dates as fallback
            summary = str(component.get("SUMMARY", ""))
            dtstart = component.get("DTSTART")
            uid = hashlib.md5(f"{summary}:{dtstart}".encode()).hexdigest()

        # Extract summary (guest name)
        summary = str(component.get("SUMMARY", "Unknown Guest"))

        # Extract dates
        dtstart = component.get("DTSTART")
        dtend = component.get("DTEND")

        if not dtstart:
            logger.warning(f"VEVENT {uid} has no DTSTART, skipping")
            return None

        checkin_date = self._extract_date(dtstart.dt)
        checkout_date = self._extract_date(dtend.dt) if dtend else checkin_date

        # Sanity check
        if checkout_date <= checkin_date:
            logger.warning(
                f"VEVENT {uid} has checkout <= checkin "
                f"({checkout_date} <= {checkin_date}), skipping"
            )
            return None

        # Extract description
        description = None
        desc_raw = component.get("DESCRIPTION")
        if desc_raw:
            description = str(desc_raw).strip() or None

        return ICalBookingData(
            uid=uid,
            summary=summary,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            description=description,
        )

    def _extract_date(self, dt_value) -> date:
        """
        Extract a date from a dtstart/dtend value.

        Handles both date and datetime objects, with timezone conversion.
        """
        if isinstance(dt_value, datetime):
            # Convert to UTC if timezone-aware, then extract date
            if dt_value.tzinfo is not None:
                dt_value = dt_value.astimezone(timezone.utc)
            return dt_value.date()
        elif isinstance(dt_value, date):
            return dt_value
        else:
            raise ValueError(f"Unexpected date type: {type(dt_value)}")

    def to_airbnb_bookings(
        self,
        ical_bookings: list[ICalBookingData],
        listing_id: str,
    ) -> list[AirbnbBookingData]:
        """
        Convert iCal bookings to AirbnbBookingData format.

        Args:
            ical_bookings: Parsed iCal booking data
            listing_id: The Airbnb listing ID (used for external_id prefix)

        Returns:
            List of AirbnbBookingData
        """
        results = []
        for b in ical_bookings:
            results.append(
                AirbnbBookingData(
                    external_id=f"ical_{b.uid}",
                    guest_name=b.summary,
                    checkin_date=b.checkin_date,
                    checkout_date=b.checkout_date,
                    guest_count=1,  # iCal doesn't provide guest count
                    total_price=0.0,  # iCal doesn't provide pricing
                    notes=b.description,
                )
            )
        return results

    def to_vrbo_bookings(
        self,
        ical_bookings: list[ICalBookingData],
        listing_id: str,
    ) -> list[VRBOBookingData]:
        """
        Convert iCal bookings to VRBOBookingData format.

        Args:
            ical_bookings: Parsed iCal booking data
            listing_id: The VRBO listing ID (used for external_id prefix)

        Returns:
            List of VRBOBookingData
        """
        results = []
        for b in ical_bookings:
            results.append(
                VRBOBookingData(
                    external_id=f"ical_{b.uid}",
                    guest_name=b.summary,
                    checkin_date=b.checkin_date,
                    checkout_date=b.checkout_date,
                    guest_count=1,
                    total_price=0.0,
                    notes=b.description,
                )
            )
        return results


# Default service instance
_default_service: ICalService | None = None


def get_ical_service() -> ICalService:
    """Get or create the default iCal service instance."""
    global _default_service
    if _default_service is None:
        _default_service = ICalService()
    return _default_service
