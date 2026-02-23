"""
Booking management API endpoints.
"""

import logging
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, DbSession
from models.booking import AirbnbBooking
from models.property import Property
from models.task import Task, TaskStatus
from schemas.booking import BookingList, BookingResponse, UpcomingBooking

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=BookingList)
async def list_bookings(
    current_user: CurrentUser,
    db: DbSession,
    property_id: UUID | None = Query(None, description="Filter by property"),
    start_date: date | None = Query(None, description="Filter by start date"),
    end_date: date | None = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> BookingList:
    """
    List all bookings for the current user's properties.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    if not property_ids:
        return BookingList(bookings=[], total=0)

    # Build query
    query = select(AirbnbBooking).where(AirbnbBooking.property_id.in_(property_ids))

    if property_id:
        query = query.where(AirbnbBooking.property_id == property_id)
    if start_date:
        query = query.where(AirbnbBooking.checkin_date >= start_date)
    if end_date:
        query = query.where(AirbnbBooking.checkout_date <= end_date)

    query = query.order_by(AirbnbBooking.checkin_date.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    bookings = result.scalars().all()

    # Get total count
    count_query = select(AirbnbBooking.id).where(
        AirbnbBooking.property_id.in_(property_ids)
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return BookingList(
        bookings=[BookingResponse.model_validate(b) for b in bookings],
        total=total,
    )


@router.get("/upcoming", response_model=list[UpcomingBooking])
async def list_upcoming_bookings(
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(30, ge=1, le=90, description="Days to look ahead"),
) -> list[UpcomingBooking]:
    """
    Get upcoming bookings for the next N days.
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    # Get user's properties
    property_result = await db.execute(
        select(Property).where(Property.host_id == current_user.id)
    )
    properties = {p.id: p for p in property_result.scalars().all()}

    if not properties:
        return []

    # Get upcoming bookings
    result = await db.execute(
        select(AirbnbBooking)
        .options(selectinload(AirbnbBooking.tasks))
        .where(
            and_(
                AirbnbBooking.property_id.in_(properties.keys()),
                AirbnbBooking.checkin_date >= today,
                AirbnbBooking.checkin_date <= end_date,
            )
        )
        .order_by(AirbnbBooking.checkin_date.asc())
    )
    bookings = result.scalars().all()

    upcoming = []
    for booking in bookings:
        property_obj = properties.get(booking.property_id)
        pending_tasks = sum(
            1 for t in booking.tasks if t.status == TaskStatus.PENDING
        )

        upcoming.append(
            UpcomingBooking(
                id=booking.id,
                property_id=booking.property_id,
                property_name=property_obj.name if property_obj else "Unknown",
                guest_name=booking.guest_name,
                checkin_date=booking.checkin_date,
                checkout_date=booking.checkout_date,
                guest_count=booking.guest_count,
                days_until_checkin=(booking.checkin_date - today).days,
                tasks_pending=pending_tasks,
            )
        )

    return upcoming


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> BookingResponse:
    """
    Get a specific booking by ID.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    result = await db.execute(
        select(AirbnbBooking).where(
            and_(
                AirbnbBooking.id == booking_id,
                AirbnbBooking.property_id.in_(property_ids),
            )
        )
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    return BookingResponse.model_validate(booking)


@router.post("/{booking_id}/sync", response_model=BookingResponse)
async def sync_booking(
    booking_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> BookingResponse:
    """
    Force sync a booking from Airbnb/VRBO.

    This triggers a refresh of the booking data from the source platform.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    result = await db.execute(
        select(AirbnbBooking).where(
            and_(
                AirbnbBooking.id == booking_id,
                AirbnbBooking.property_id.in_(property_ids),
            )
        )
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # TODO: Implement actual sync from Airbnb/VRBO
    # For now, just update the synced_at timestamp
    from datetime import datetime, timezone

    booking.synced_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(booking)

    logger.info(f"Booking synced: {booking.id}")

    return BookingResponse.model_validate(booking)
