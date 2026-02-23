"""
Polling tasks for syncing bookings from Airbnb and VRBO.

Runs every 15 minutes to detect new bookings and trigger task generation.
"""

import logging
from uuid import UUID

from celery_config import celery_app
from database import async_session_maker
from models.booking import AirbnbBooking, BookingSource
from models.property import Property
from services.airbnb_service import AirbnbService, get_airbnb_service
from services.vrbo_service import VRBOService, get_vrbo_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _get_all_properties(session: AsyncSession) -> list[Property]:
    """Get all properties with connected listings."""
    result = await session.execute(select(Property))
    return list(result.scalars().all())


async def _get_existing_booking_ids(
    session: AsyncSession,
    property_id: UUID,
    source: BookingSource,
) -> set[str]:
    """Get set of existing external booking IDs for a property."""
    result = await session.execute(
        select(AirbnbBooking.external_id).where(
            AirbnbBooking.property_id == property_id,
            AirbnbBooking.source == source,
        )
    )
    return {row[0] for row in result.fetchall() if row[0]}


async def _save_new_booking(
    session: AsyncSession,
    property_id: UUID,
    booking_data: dict,
    source: BookingSource,
) -> AirbnbBooking:
    """Save a new booking to the database."""
    booking = AirbnbBooking(
        property_id=property_id,
        external_id=booking_data.get("external_id"),
        guest_name=booking_data["guest_name"],
        checkin_date=booking_data["checkin_date"],
        checkout_date=booking_data["checkout_date"],
        guest_count=booking_data["guest_count"],
        total_price=booking_data.get("total_price", 0.0),
        notes=booking_data.get("notes"),
        source=source,
    )
    session.add(booking)
    await session.flush()
    return booking


@celery_app.task(
    name="tasks.polling.poll_airbnb_bookings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def poll_airbnb_bookings(self) -> dict:
    """
    Poll Airbnb for new bookings across all properties.

    Returns:
        Summary of sync results
    """
    import asyncio

    async def _poll():
        service = get_airbnb_service()
        results = {
            "properties_checked": 0,
            "new_bookings": 0,
            "errors": [],
        }

        async with async_session_maker() as session:
            properties = await _get_all_properties(session)

            for prop in properties:
                if not prop.airbnb_listing_id:
                    continue

                results["properties_checked"] += 1

                try:
                    # Get existing booking IDs
                    existing_ids = await _get_existing_booking_ids(
                        session, prop.id, BookingSource.AIRBNB
                    )

                    # Fetch new bookings
                    new_bookings = await service.sync_bookings(
                        listing_id=prop.airbnb_listing_id,
                        property_id=prop.id,
                        existing_booking_ids=existing_ids,
                    )

                    # Save new bookings
                    for booking_data in new_bookings:
                        booking = await _save_new_booking(
                            session=session,
                            property_id=prop.id,
                            booking_data={
                                "external_id": booking_data.external_id,
                                "guest_name": booking_data.guest_name,
                                "checkin_date": booking_data.checkin_date,
                                "checkout_date": booking_data.checkout_date,
                                "guest_count": booking_data.guest_count,
                                "total_price": booking_data.total_price,
                                "notes": booking_data.notes,
                            },
                            source=BookingSource.AIRBNB,
                        )
                        results["new_bookings"] += 1

                        # Trigger task generation
                        from tasks.task_generation import generate_tasks_for_booking

                        generate_tasks_for_booking.delay(str(booking.id))

                        logger.info(
                            f"New Airbnb booking detected: {booking.guest_name} "
                            f"at {prop.name}"
                        )

                    await session.commit()

                except Exception as e:
                    logger.error(f"Error polling Airbnb for {prop.name}: {e}")
                    results["errors"].append(
                        {"property": prop.name, "error": str(e)}
                    )
                    await session.rollback()

        return results

    return asyncio.get_event_loop().run_until_complete(_poll())


@celery_app.task(
    name="tasks.polling.poll_vrbo_bookings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def poll_vrbo_bookings(self) -> dict:
    """
    Poll VRBO for new bookings across all properties.

    Returns:
        Summary of sync results
    """
    import asyncio

    async def _poll():
        service = get_vrbo_service()
        results = {
            "properties_checked": 0,
            "new_bookings": 0,
            "errors": [],
        }

        async with async_session_maker() as session:
            properties = await _get_all_properties(session)

            for prop in properties:
                if not prop.vrbo_listing_id:
                    continue

                results["properties_checked"] += 1

                try:
                    # Get existing booking IDs
                    existing_ids = await _get_existing_booking_ids(
                        session, prop.id, BookingSource.VRBO
                    )

                    # Fetch new bookings
                    new_bookings = await service.sync_bookings(
                        listing_id=prop.vrbo_listing_id,
                        property_id=prop.id,
                        existing_booking_ids=existing_ids,
                    )

                    # Save new bookings
                    for booking_data in new_bookings:
                        booking = await _save_new_booking(
                            session=session,
                            property_id=prop.id,
                            booking_data={
                                "external_id": booking_data.external_id,
                                "guest_name": booking_data.guest_name,
                                "checkin_date": booking_data.checkin_date,
                                "checkout_date": booking_data.checkout_date,
                                "guest_count": booking_data.guest_count,
                                "total_price": booking_data.total_price,
                                "notes": booking_data.notes,
                            },
                            source=BookingSource.VRBO,
                        )
                        results["new_bookings"] += 1

                        # Trigger task generation
                        from tasks.task_generation import generate_tasks_for_booking

                        generate_tasks_for_booking.delay(str(booking.id))

                        logger.info(
                            f"New VRBO booking detected: {booking.guest_name} "
                            f"at {prop.name}"
                        )

                    await session.commit()

                except Exception as e:
                    logger.error(f"Error polling VRBO for {prop.name}: {e}")
                    results["errors"].append(
                        {"property": prop.name, "error": str(e)}
                    )
                    await session.rollback()

        return results

    return asyncio.get_event_loop().run_until_complete(_poll())


@celery_app.task(name="tasks.polling.sync_property_bookings")
def sync_property_bookings(property_id: str, source: str = "airbnb") -> dict:
    """
    Manually trigger booking sync for a specific property.

    Args:
        property_id: UUID of the property
        source: "airbnb" or "vrbo"

    Returns:
        Sync results
    """
    import asyncio

    async def _sync():
        async with async_session_maker() as session:
            result = await session.execute(
                select(Property).where(Property.id == UUID(property_id))
            )
            prop = result.scalar_one_or_none()

            if not prop:
                return {"error": "Property not found"}

            if source == "airbnb":
                if not prop.airbnb_listing_id:
                    return {"error": "No Airbnb listing connected"}
                service = get_airbnb_service()
                listing_id = prop.airbnb_listing_id
                booking_source = BookingSource.AIRBNB
            else:
                if not prop.vrbo_listing_id:
                    return {"error": "No VRBO listing connected"}
                service = get_vrbo_service()
                listing_id = prop.vrbo_listing_id
                booking_source = BookingSource.VRBO

            existing_ids = await _get_existing_booking_ids(
                session, prop.id, booking_source
            )

            new_bookings = await service.sync_bookings(
                listing_id=listing_id,
                property_id=prop.id,
                existing_booking_ids=existing_ids,
            )

            saved_count = 0
            for booking_data in new_bookings:
                booking = await _save_new_booking(
                    session=session,
                    property_id=prop.id,
                    booking_data={
                        "external_id": booking_data.external_id,
                        "guest_name": booking_data.guest_name,
                        "checkin_date": booking_data.checkin_date,
                        "checkout_date": booking_data.checkout_date,
                        "guest_count": booking_data.guest_count,
                        "total_price": booking_data.total_price,
                        "notes": booking_data.notes,
                    },
                    source=booking_source,
                )
                saved_count += 1

                from tasks.task_generation import generate_tasks_for_booking

                generate_tasks_for_booking.delay(str(booking.id))

            await session.commit()

            return {
                "property": prop.name,
                "source": source,
                "new_bookings": saved_count,
            }

    return asyncio.get_event_loop().run_until_complete(_sync())
