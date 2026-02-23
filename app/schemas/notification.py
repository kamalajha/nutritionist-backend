from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

class NotificationBase(BaseModel):
    title: Optional[str] = None
    message: str
    channel: str  # email, push, in_app

class NotificationCreate(NotificationBase):
    user_id: int
    appointment_id: Optional[uuid.UUID] = None

class NotificationUpdate(BaseModel):
    status: Optional[str] = None
    read_at: Optional[datetime] = None

class NotificationInDB(NotificationBase):
    notification_id: uuid.UUID
    user_id: int
    appointment_id: Optional[uuid.UUID] = None
    status: str = "pending"
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Notification(NotificationInDB):
    pass