"""
Automation configuration API endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from models.automation_config import AutomationConfig
from schemas.config import (
    AutomationConfigResponse,
    AutomationConfigUpdate,
    MaintenanceTemplateResponse,
    TurnoverTemplateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=AutomationConfigResponse)
async def get_config(
    current_user: CurrentUser,
    db: DbSession,
) -> AutomationConfigResponse:
    """
    Get current user's automation configuration.
    """
    result = await db.execute(
        select(AutomationConfig).where(AutomationConfig.host_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    if not config:
        # Create default config if it doesn't exist
        config = AutomationConfig(host_id=current_user.id)
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return AutomationConfigResponse.model_validate(config)


@router.put("/", response_model=AutomationConfigResponse)
async def update_config(
    config_data: AutomationConfigUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AutomationConfigResponse:
    """
    Update automation configuration.
    """
    result = await db.execute(
        select(AutomationConfig).where(AutomationConfig.host_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    if not config:
        # Create config if it doesn't exist
        config = AutomationConfig(host_id=current_user.id)
        db.add(config)
        await db.flush()

    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    logger.info(f"Config updated for user: {current_user.email}")

    return AutomationConfigResponse.model_validate(config)


@router.post("/template/turnover", response_model=TurnoverTemplateResponse)
async def get_turnover_template(
    current_user: CurrentUser,
) -> TurnoverTemplateResponse:
    """
    Get default turnover cleaning task template.
    """
    return TurnoverTemplateResponse(
        task_type="cleaning",
        description_template=(
            "Turnover cleaning for {property_name}: "
            "checkout at {checkout_time}, checkin at {checkin_time}. "
            "{bedrooms}BR, {bathrooms}BA property."
        ),
        default_duration_hours=3.0,
        default_checklist=[
            "Vacuum all carpets and rugs",
            "Mop hard floors",
            "Clean and sanitize all bathrooms",
            "Change all bed linens",
            "Make beds with fresh linens",
            "Empty all trash cans",
            "Clean kitchen appliances (stove, microwave, refrigerator)",
            "Wipe down all countertops and surfaces",
            "Clean mirrors and glass surfaces",
            "Restock toiletries (soap, shampoo, toilet paper)",
            "Check for and report any damage",
            "Ensure all lights work",
            "Set thermostat to welcome temperature",
            "Leave welcome materials visible",
        ],
        required_skills=["cleaning"],
    )


@router.post("/template/maintenance", response_model=MaintenanceTemplateResponse)
async def get_maintenance_template(
    current_user: CurrentUser,
) -> MaintenanceTemplateResponse:
    """
    Get default maintenance task template.
    """
    return MaintenanceTemplateResponse(
        task_type="maintenance",
        description_template=(
            "Maintenance request for {property_name}: {issue_description}"
        ),
        default_duration_hours=2.0,
        default_checklist=[
            "Assess the issue",
            "Gather necessary tools and materials",
            "Complete the repair",
            "Test the repair",
            "Clean up work area",
            "Take before/after photos",
            "Report completion to host",
        ],
        required_skills=["handyman", "maintenance"],
    )
