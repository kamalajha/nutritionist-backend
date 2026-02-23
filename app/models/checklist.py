from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class PreparationChecklist(Base):
    __tablename__ = "preparation_checklists"
    
    checklist_id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.appointment_id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(50))
    item_text = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationship
    appointment = relationship("Appointment", back_populates="checklist_items")