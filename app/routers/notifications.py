from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.notification import Notification
from app.routers.auth import get_current_user  # Auth logic for security

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

# 1. User ki saari notifications fetch karna
@router.get("/", response_model=List[dict])
def get_my_notifications(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Authenticated user ke liye latest 20 notifications fetch karta hai"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.user_id
    ).order_by(Notification.created_at.desc()).limit(20).all()
    
    return notifications

# 2. Notification ko "Read" mark karna
@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kisi specific notification ko read mark karne ke liye"""
    notif = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.read_at = datetime.utcnow()
    notif.status = "delivered"  # Status update
    db.commit()
    
    return {"status": "success", "message": "Marked as read"}

# 3. Unread count (React Bell badge ke liye)
@router.get("/unread-count")
def get_unread_count(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.read_at == None
    ).count()
    
    return {"unread_count": count}
# app/routers/notifications.py mein ye niche add karein

@router.get("/latest-meeting")
def get_latest_meeting(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sirf virtual meeting wali latest unread notification dhoondta hai"""
    notif = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.read_at == None,
        Notification.message.contains("meet.google.com") # Ya jo bhi video link pattern ho
    ).order_by(Notification.created_at.desc()).first()
    
    return notif