"""
Notifications API endpoints.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, update

from api.deps import CurrentUser, DbSession
from models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationResponse(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    message: str
    link: str | None = None
    read: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class NotificationList(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int


@router.get("/", response_model=NotificationList)
async def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> NotificationList:
    """List notifications for the current user."""
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.read == False)
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    # Total count
    count_q = select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
    total = (await db.execute(count_q)).scalar() or 0

    # Unread count
    unread_q = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id, Notification.read == False
    )
    unread_count = (await db.execute(unread_q)).scalar() or 0

    return NotificationList(
        notifications=[
            NotificationResponse(
                id=n.id,
                type=n.type,
                title=n.title,
                message=n.message,
                link=n.link,
                read=n.read,
                created_at=n.created_at.isoformat(),
            )
            for n in notifications
        ],
        total=total,
        unread_count=unread_count,
    )


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Mark a notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    await db.flush()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(current_user: CurrentUser, db: DbSession) -> dict:
    """Mark all notifications as read."""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read == False)
        .values(read=True)
    )
    return {"ok": True}
