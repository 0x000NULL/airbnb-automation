"""
Human search and management API endpoints (RentAHuman integration).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import CurrentUser
from schemas.human import (
    HumanAvailability,
    HumanList,
    HumanResponse,
    HumanReviewList,
    HumanSearchParams,
    SkillList,
)
from services.rentahuman_client import get_rentahuman_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=HumanList)
async def search_humans(
    current_user: CurrentUser,
    location: str = Query(..., min_length=1, description="City, state or ZIP"),
    skill: str | None = Query(None, description="Skill filter"),
    availability: str | None = Query(None, description="Availability filter"),
    budget_max: float | None = Query(None, ge=0, description="Max hourly rate"),
    rating_min: float | None = Query(None, ge=3.0, le=5.0, description="Min rating"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
) -> HumanList:
    """
    Search for available humans by location and criteria.

    Uses RentAHuman API.
    """
    client = get_rentahuman_client()

    humans = await client.search_humans(
        location=location,
        skill=skill,
        availability=availability,
        budget_max=budget_max,
        rating_min=rating_min,
        limit=limit,
    )

    logger.info(f"Human search: location={location}, skill={skill}, found={len(humans)}")

    return HumanList(
        humans=[
            HumanResponse(
                id=h.id,
                name=h.name,
                skills=h.skills,
                location=h.location,
                rate=h.rate,
                currency=h.currency,
                rating=h.rating,
                reviews=h.reviews,
                availability=h.availability,
                bio=h.bio,
                photo_url=h.photo_url,
            )
            for h in humans
        ],
        total=len(humans),
    )


@router.get("/skills", response_model=SkillList)
async def list_skills(
    current_user: CurrentUser,
) -> SkillList:
    """
    Get list of all available skills on RentAHuman.
    """
    client = get_rentahuman_client()
    skills = await client.list_skills()

    return SkillList(
        skills=skills,
        total=len(skills),
    )


@router.get("/{human_id}", response_model=HumanResponse)
async def get_human(
    human_id: str,
    current_user: CurrentUser,
) -> HumanResponse:
    """
    Get a specific human's profile.
    """
    client = get_rentahuman_client()
    human = await client.get_human(human_id)

    if not human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Human {human_id} not found",
        )

    return HumanResponse(
        id=human.id,
        name=human.name,
        skills=human.skills,
        location=human.location,
        rate=human.rate,
        currency=human.currency,
        rating=human.rating,
        reviews=human.reviews,
        availability=human.availability,
        bio=human.bio,
        photo_url=human.photo_url,
    )


@router.get("/{human_id}/reviews", response_model=HumanReviewList)
async def get_human_reviews(
    human_id: str,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50, description="Max reviews"),
) -> HumanReviewList:
    """
    Get reviews for a specific human.

    Note: RentAHuman API reviews endpoint not yet available.
    Returns mock data for now.
    """
    # TODO: Implement actual reviews fetch when RentAHuman API supports it
    # Returning empty data — no fake reviews. Pending RentAHuman API review support.
    return HumanReviewList(
        reviews=[],
        total=0,
        average_rating=0.0,
        note="Reviews will be available when RentAHuman API adds review support",
    )


@router.get("/{human_id}/availability", response_model=HumanAvailability)
async def get_human_availability(
    human_id: str,
    current_user: CurrentUser,
) -> HumanAvailability:
    """
    Get availability for a specific human.

    Note: RentAHuman API availability endpoint not yet available.
    Returns mock data for now.
    """
    # TODO: Implement actual availability check when RentAHuman API supports it
    # Returning empty/unknown data — no fake availability. Pending RentAHuman API support.
    return HumanAvailability(
        human_id=human_id,
        available=False,
        next_available=None,
        booked_slots=[],
        note="Availability data will be available when RentAHuman API adds support",
    )
