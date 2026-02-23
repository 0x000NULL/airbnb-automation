"""
Property management API endpoints.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, DbSession
from models.booking import AirbnbBooking, BookingSource
from models.property import Property
from schemas.property import (
    ConnectPlatformRequest,
    PropertyCreate,
    PropertyList,
    PropertyResponse,
    PropertyUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PropertyResponse:
    """
    Create a new property.
    """
    property_obj = Property(
        host_id=current_user.id,
        name=property_data.name,
        location=property_data.location.model_dump(),
        property_type=property_data.property_type,
        bedrooms=property_data.bedrooms,
        bathrooms=property_data.bathrooms,
        max_guests=property_data.max_guests,
        airbnb_listing_id=property_data.airbnb_listing_id,
        vrbo_listing_id=property_data.vrbo_listing_id,
        ical_url=property_data.ical_url,
        default_checkin_time=property_data.default_checkin_time,
        default_checkout_time=property_data.default_checkout_time,
        cleaning_budget=property_data.cleaning_budget,
        maintenance_budget=property_data.maintenance_budget,
        preferred_skills=property_data.preferred_skills,
    )

    db.add(property_obj)
    await db.commit()
    await db.refresh(property_obj)

    logger.info(f"Property created: {property_obj.name} for user {current_user.email}")

    return PropertyResponse.model_validate(property_obj)


@router.get("/", response_model=PropertyList)
async def list_properties(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> PropertyList:
    """
    List all properties for the current user.
    """
    # Total count
    count_result = await db.execute(
        select(func.count(Property.id)).where(Property.host_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Property)
        .where(Property.host_id == current_user.id)
        .order_by(Property.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    properties = result.scalars().all()

    return PropertyList(
        properties=[PropertyResponse.model_validate(p) for p in properties],
        total=total,
    )


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> PropertyResponse:
    """
    Get a specific property by ID.
    """
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id, Property.host_id == current_user.id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    return PropertyResponse.model_validate(property_obj)


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_data: PropertyUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> PropertyResponse:
    """
    Update a property.
    """
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id, Property.host_id == current_user.id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Update fields that are provided
    update_data = property_data.model_dump(exclude_unset=True)
    if "location" in update_data and update_data["location"]:
        update_data["location"] = update_data["location"].model_dump() if hasattr(update_data["location"], "model_dump") else update_data["location"]

    for field, value in update_data.items():
        setattr(property_obj, field, value)

    await db.commit()
    await db.refresh(property_obj)

    logger.info(f"Property updated: {property_obj.name}")

    return PropertyResponse.model_validate(property_obj)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """
    Delete a property.
    """
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id, Property.host_id == current_user.id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    await db.delete(property_obj)
    await db.commit()

    logger.info(f"Property deleted: {property_obj.name}")


@router.post("/{property_id}/connect-airbnb", response_model=PropertyResponse)
async def connect_airbnb(
    property_id: UUID,
    request: ConnectPlatformRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> PropertyResponse:
    """
    Connect an Airbnb listing to a property.
    """
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id, Property.host_id == current_user.id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    property_obj.airbnb_listing_id = request.listing_id
    await db.commit()
    await db.refresh(property_obj)

    logger.info(f"Airbnb connected to property: {property_obj.name}")

    return PropertyResponse.model_validate(property_obj)


@router.post("/{property_id}/connect-vrbo", response_model=PropertyResponse)
async def connect_vrbo(
    property_id: UUID,
    request: ConnectPlatformRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> PropertyResponse:
    """
    Connect a VRBO listing to a property.
    """
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id, Property.host_id == current_user.id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    property_obj.vrbo_listing_id = request.listing_id
    await db.commit()
    await db.refresh(property_obj)

    logger.info(f"VRBO connected to property: {property_obj.name}")

    return PropertyResponse.model_validate(property_obj)


class ICalSyncResponse(BaseModel):
    """Response for iCal sync endpoint."""

    new_bookings: int = Field(..., description="Number of new bookings imported")
    updated_bookings: int = Field(..., description="Number of existing bookings updated")
    total_in_feed: int = Field(..., description="Total bookings found in iCal feed")


@router.post("/{property_id}/sync-ical", response_model=ICalSyncResponse)
async def sync_ical(
    property_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ICalSyncResponse:
    """
    Manually trigger an iCal sync for a specific property.

    Fetches the iCal feed, parses bookings, and upserts them into the database.
    Returns the count of new and updated bookings.
    """
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id, Property.host_id == current_user.id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    if not property_obj.ical_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property does not have an iCal URL configured",
        )

    from services.ical_service import get_ical_service

    ical_service = get_ical_service()

    try:
        ical_bookings = await ical_service.fetch_and_parse(property_obj.ical_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    # Determine source based on which listing ID is set
    source = BookingSource.AIRBNB
    if property_obj.vrbo_listing_id and not property_obj.airbnb_listing_id:
        source = BookingSource.VRBO

    # Get existing bookings for this property by external_id
    existing_result = await db.execute(
        select(AirbnbBooking).where(AirbnbBooking.property_id == property_id)
    )
    existing_bookings = {
        b.external_id: b for b in existing_result.scalars().all() if b.external_id
    }

    new_count = 0
    updated_count = 0

    for ical_booking in ical_bookings:
        external_id = f"ical_{ical_booking.uid}"

        if external_id in existing_bookings:
            # Update existing booking
            existing = existing_bookings[external_id]
            changed = False
            if existing.guest_name != ical_booking.summary:
                existing.guest_name = ical_booking.summary
                changed = True
            if existing.checkin_date != ical_booking.checkin_date:
                existing.checkin_date = ical_booking.checkin_date
                changed = True
            if existing.checkout_date != ical_booking.checkout_date:
                existing.checkout_date = ical_booking.checkout_date
                changed = True
            if existing.notes != ical_booking.description:
                existing.notes = ical_booking.description
                changed = True
            if changed:
                existing.synced_at = datetime.now(timezone.utc)
                updated_count += 1
        else:
            # Create new booking
            new_booking = AirbnbBooking(
                property_id=property_id,
                external_id=external_id,
                guest_name=ical_booking.summary,
                checkin_date=ical_booking.checkin_date,
                checkout_date=ical_booking.checkout_date,
                guest_count=1,
                total_price=0.0,
                notes=ical_booking.description,
                source=source,
                synced_at=datetime.now(timezone.utc),
            )
            db.add(new_booking)
            new_count += 1

    await db.commit()

    logger.info(
        f"iCal sync for property {property_obj.name}: "
        f"{new_count} new, {updated_count} updated, "
        f"{len(ical_bookings)} total in feed"
    )

    return ICalSyncResponse(
        new_bookings=new_count,
        updated_bookings=updated_count,
        total_in_feed=len(ical_bookings),
    )
