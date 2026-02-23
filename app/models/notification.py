from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base
from datetime import datetime

class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.appointment_id", ondelete="CASCADE"))
    
    title = Column(String(200))
    message = Column(Text, nullable=False)
    channel = Column(String(20)) # 'email', 'in_app'
    status = Column(String(20), default="pending") # 'pending', 'sent'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(channel.in_(['email', 'push', 'in_app'])),
        CheckConstraint(status.in_(['pending', 'sent', 'delivered', 'failed'])),
    )