"""
Property management API endpoints.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, DbSession
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
) -> PropertyList:
    """
    List all properties for the current user.
    """
    result = await db.execute(
        select(Property)
        .where(Property.host_id == current_user.id)
        .order_by(Property.created_at.desc())
    )
    properties = result.scalars().all()

    return PropertyList(
        properties=[PropertyResponse.model_validate(p) for p in properties],
        total=len(properties),
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
