from sqlalchemy import Column, Integer, String, Boolean, Text, DECIMAL, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Nutritionist(Base):  # <--- Check karein 'N' capital hai ya nahi
    __tablename__ = "nutritionists"
    
    nutritionist_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    specialization = Column(String(100))
    license_number = Column(String(50))
    bio = Column(Text)
    hourly_rate = Column(DECIMAL(10, 2))
    available_days = Column(String(100))
    working_hours = Column(String(100))
    accepting_patients = Column(Boolean, default=True)
    rating = Column(DECIMAL(3, 2), default=0.00)
    total_sessions = Column(Integer, default=0)
    experience = Column(String(100), nullable=True) # New column for experience
    # Naye columns jo aapne add kiye hain
    profile_image = Column(Text) # SQL mein rename kiya hua column
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    type = Column(String, default="expert")
    # Relationships
    # String use karein taaki registry error na aaye
    user = relationship("User", foreign_keys=[user_id])
    nutritionist_appointments = relationship("Appointment",foreign_keys="[Appointment.nutritionist_id]", back_populates="nutritionist")