"""
Task management API endpoints.
"""

import logging
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, DbSession
from models.automation_config import AutomationConfig
from models.property import Property
from models.task import Task, TaskStatus, TaskType
from schemas.task import (
    TaskBookRequest,
    TaskCreate,
    TaskList,
    TaskResponse,
    TaskStatusResponse,
    TaskUpdate,
)
from services.booking_engine import get_booking_engine
from services.rentahuman_client import get_rentahuman_client
from services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=TaskList)
async def list_tasks(
    current_user: CurrentUser,
    db: DbSession,
    property_id: UUID | None = Query(None, description="Filter by property"),
    task_type: TaskType | None = Query(None, description="Filter by task type"),
    task_status: TaskStatus | None = Query(None, description="Filter by status"),
    start_date: date | None = Query(None, description="Filter by start date"),
    end_date: date | None = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> TaskList:
    """
    List all tasks for the current user's properties.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    if not property_ids:
        return TaskList(tasks=[], total=0)

    # Build query
    query = select(Task).where(Task.property_id.in_(property_ids))

    if property_id:
        query = query.where(Task.property_id == property_id)
    if task_type:
        query = query.where(Task.type == task_type)
    if task_status:
        query = query.where(Task.status == task_status)
    if start_date:
        query = query.where(Task.scheduled_date >= start_date)
    if end_date:
        query = query.where(Task.scheduled_date <= end_date)

    query = query.order_by(Task.scheduled_date.asc(), Task.scheduled_time.asc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Get total count
    count_query = select(Task.id).where(Task.property_id.in_(property_ids))
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return TaskList(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
    )


@router.get("/upcoming", response_model=TaskList)
async def list_upcoming_tasks(
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(7, ge=1, le=30, description="Days to look ahead"),
) -> TaskList:
    """
    Get upcoming tasks that need booking (PENDING status).
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    if not property_ids:
        return TaskList(tasks=[], total=0)

    result = await db.execute(
        select(Task)
        .where(
            and_(
                Task.property_id.in_(property_ids),
                Task.status == TaskStatus.PENDING,
                Task.scheduled_date >= today,
                Task.scheduled_date <= end_date,
            )
        )
        .order_by(Task.scheduled_date.asc(), Task.scheduled_time.asc())
    )
    tasks = result.scalars().all()

    return TaskList(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> TaskResponse:
    """
    Create a new task manually.
    """
    # Verify property belongs to user
    result = await db.execute(
        select(Property).where(
            and_(
                Property.id == task_data.property_id,
                Property.host_id == current_user.id,
            )
        )
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    task = Task(
        type=task_data.type,
        property_id=task_data.property_id,
        airbnb_booking_id=task_data.airbnb_booking_id,
        description=task_data.description,
        required_skills=task_data.required_skills,
        budget=task_data.budget,
        scheduled_date=task_data.scheduled_date,
        scheduled_time=task_data.scheduled_time,
        duration_hours=task_data.duration_hours,
        checklist=task_data.checklist,
        host_notes=task_data.host_notes,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"Task created: {task.type.value} for property {property_obj.name}")

    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> TaskResponse:
    """
    Get a specific task by ID.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.property_id.in_(property_ids),
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return TaskResponse.model_validate(task)


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> TaskStatusResponse:
    """
    Get task status with human assignment details.

    If task has a RentAHuman booking, fetches current status from RentAHuman API.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.property_id.in_(property_ids),
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Fetch completion photos from storage
    storage = get_storage_service()
    completion_photos = await storage.list_task_photos(str(task_id))

    # Fetch status from RentAHuman if we have a booking
    human_feedback = None
    if task.rentahuman_booking_id:
        client = get_rentahuman_client()
        booking_status = await client.get_booking_status(task.rentahuman_booking_id)
        if booking_status:
            human_feedback = booking_status.get("human_feedback")
            # Update task status if it changed
            new_status = booking_status.get("status")
            if new_status == "completed" and task.status != TaskStatus.COMPLETED:
                task.status = TaskStatus.COMPLETED
                await db.commit()
            elif new_status == "in_progress" and task.status != TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.IN_PROGRESS
                await db.commit()

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        rentahuman_booking_id=task.rentahuman_booking_id,
        assigned_human=task.assigned_human,
        completion_photos=completion_photos,
        human_feedback=human_feedback,
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> TaskResponse:
    """
    Update a task.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.property_id.in_(property_ids),
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Update fields
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    logger.info(f"Task updated: {task.id}")

    return TaskResponse.model_validate(task)


@router.post("/{task_id}/book", response_model=TaskResponse)
async def book_task(
    task_id: UUID,
    request: TaskBookRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TaskResponse:
    """
    Manually trigger booking for a task.
    """
    # Get user's properties and task
    property_result = await db.execute(
        select(Property).where(Property.host_id == current_user.id)
    )
    properties = {p.id: p for p in property_result.scalars().all()}

    if not properties:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No properties found",
        )

    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.property_id.in_(properties.keys()),
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not in PENDING status (current: {task.status.value})",
        )

    # Get property and automation config
    prop = properties[task.property_id]

    config_result = await db.execute(
        select(AutomationConfig).where(AutomationConfig.host_id == current_user.id)
    )
    config = config_result.scalar_one_or_none()

    if not config:
        # Create default config if not exists
        config = AutomationConfig(host_id=current_user.id)
        db.add(config)
        await db.flush()

    # Use BookingEngine to find and book a human
    booking_engine = get_booking_engine()
    booking_result = await booking_engine.book_task(task, prop, config)

    if booking_result.success:
        task.status = TaskStatus.HUMAN_BOOKED
        task.rentahuman_booking_id = booking_result.booking_id
        if booking_result.human:
            task.assigned_human = {
                "id": booking_result.human.id,
                "name": booking_result.human.name,
                "photo": booking_result.human.photo_url,
                "rating": booking_result.human.rating,
                "reviews": booking_result.human.reviews,
            }
        logger.info(f"Task booked successfully: {task.id} -> {booking_result.booking_id}")
    else:
        # Booking failed but we don't fail the request - return current state
        logger.warning(f"Task booking failed: {task.id} - {booking_result.error}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Booking failed: {booking_result.error}",
        )

    await db.commit()
    await db.refresh(task)

    return TaskResponse.model_validate(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> TaskResponse:
    """
    Mark a task as complete.
    """
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.property_id.in_(property_ids),
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task.status = TaskStatus.COMPLETED
    await db.commit()
    await db.refresh(task)

    logger.info(f"Task completed: {task.id}")

    return TaskResponse.model_validate(task)


@router.post("/{task_id}/photo", response_model=TaskResponse)
async def upload_task_photo(
    task_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(..., description="Photo file"),
) -> TaskResponse:
    """
    Upload a completion photo for a task.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/heic"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}",
        )

    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB",
        )

    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.property_id.in_(property_ids),
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Upload to DigitalOcean Spaces
    storage = get_storage_service()
    photo_url = await storage.upload_photo(
        file_data=content,
        task_id=str(task_id),
        filename=file.filename or "photo.jpg",
        content_type=file.content_type or "image/jpeg",
    )

    if not photo_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload photo",
        )

    task.photo_upload_url = photo_url

    await db.commit()
    await db.refresh(task)

    logger.info(f"Photo uploaded for task: {task.id} -> {photo_url}")

    return TaskResponse.model_validate(task)
