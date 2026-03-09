
from app.models.checklist import PreparationChecklist
from sqlalchemy import Column, DateTime, Integer, String, Boolean, Text, TIMESTAMP, ForeignKey, Date, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Appointment(Base):
    __tablename__ = "appointments"
    
    appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    nutritionist_id = Column(Integer, ForeignKey("nutritionists.nutritionist_id", ondelete="CASCADE"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)
    appointment_type = Column(String(20))  # virtual, in_person, phone_call
    status = Column(String(20), default="scheduled")  # scheduled, confirmed, in_progress, completed, cancelled, no_show
    meeting_url = Column(Text)
    cancelled_by = Column(Integer, ForeignKey("users.user_id"))
    cancellation_reason = Column(Text)
    provider_joined_at = Column(TIMESTAMP(timezone=True))
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    notes = Column(Text, nullable=True)
    transaction_id = Column(String(100), nullable=True)  # Payment gateway transaction ID
    payment_status = Column(String(20), default="pending")  # pending, paid, failed, refunded
    amount = Column(Integer, nullable=True)  # Amount in cents for easier calculations
    cashfree_order_id = Column(String(255), nullable=True)  # Cashfree ka order ID
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="appointments")
    nutritionist = relationship(
        "Nutritionist", 
       
        back_populates="nutritionist_appointments"
    )
    # nutritionist = relationship("Nutritionist", back_populates="appointments")
    # cancelled_by_user = relationship("User", foreign_keys=[cancelled_by])
    checklist_items = relationship("PreparationChecklist", back_populates="appointment")
from sqlalchemy import Column, Integer, String, Boolean, Date, Time, ForeignKey
from app.database import Base

class Slot(Base):
    __tablename__ = "nutritionist_slots"

    slot_id = Column(Integer, primary_key=True, index=True)
    nutritionist_id = Column(Integer, ForeignKey("nutritionists.nutritionist_id"))
    slot_date = Column(Date)
    start_time = Column(String)  # Ya Time use karein
    end_time = Column(String)
    is_available = Column(Boolean, default=True)
    is_booked = Column(Boolean, default=False)