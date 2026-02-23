from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, JSON
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship,foreign
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    profile_image = Column(Text) #
    
    # ERROR FIX: Ye column missing hone se app crash ho rahi thi
    contact_number = Column(String(20), nullable=True) #
    
    timezone = Column(String(50), default='UTC')
    role = Column(String(50), nullable=False)  # client, nutritionist, admin
    notification_preferences = Column(JSON, default={"email": True, "push": True})
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    appointments = relationship("Appointment", foreign_keys="[Appointment.user_id]", back_populates="user")
   # nutritionist_appointments = relationship("Appointment", back_populates="nutritionist", foreign_keys="[Appointment.nutritionist_id]")