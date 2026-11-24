from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationOut, NotificationPreference
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationOut])
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notes = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(desc(Notification.created_at)).limit(50).all()

    return [
        NotificationOut(
            id=n.id,
            user_id=n.user_id,
            booking_id=n.booking_id,
            channel=n.channel,
            type=n.type,
            title=n.title,
            payload=n.payload,
            status=n.status,
            sent_at=n.sent_at,
            created_at=n.created_at
        )
        for n in notes
    ]

@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.status.in_(["sent", "queued"])
    ).count()
    return {"unread_count": count}

@router.post("/mark-read")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.status.in_(["sent", "queued"])
    ).update({"status": "read"})
    db.commit()
    return {"message": "All notifications marked as read."}

@router.get("/preferences")
def get_preferences(current_user: User = Depends(get_current_user)):
    return {
        "email": True,
        "sms": True,
        "whatsapp": True
    }

@router.put("/preferences")
def update_preferences(prefs: NotificationPreference, current_user: User = Depends(get_current_user)):
    return {"message": "Notification preferences updated.", "preferences": prefs.model_dump()}
