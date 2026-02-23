from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Any, Optional, List
from datetime import date, time, datetime
import uuid
from decimal import Decimal
from app.schemas.nutritionist import NutritionistOut
from app.schemas.user import UserOut

class AppointmentBase(BaseModel):
    appointment_date: date
    # Alias use kiya hai taaki frontend 'appointment_time' bheje aur DB 'start_time' use kare
    start_time: time = Field(..., alias="appointment_time") 
    end_time: Optional[time] = None
    appointment_type: str  # virtual, in_person
    meeting_url: Optional[str] = None
    notes: Optional[str] = Field(None, alias="health_concerns")
    status: Optional[str] = "scheduled"
    transaction_id: Optional[str] = None
    payment_status: Optional[str] = "pending"
    amount: Optional[int] = None
    
    # ⚡ Session Tracking Fields
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None # 👈 Ye session details ke liye zaroori hai

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator('appointment_date', mode='before')
    @classmethod
    def parse_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(value, '%d-%m-%Y').date()
                except ValueError:
                    return value
        return value

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def parse_time(cls, value):
        if isinstance(value, str):
            if not value: return None
            try:
                return datetime.strptime(value, '%H:%M').time()
            except ValueError:
                try:
                    return datetime.strptime(value, '%H:%M:%S').time()
                except ValueError:
                    return value
        return value

class AppointmentCreate(AppointmentBase):
    user_id: Optional[int] = None
    nutritionist_id: int

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    meeting_url: Optional[str] = None
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None 

class AppointmentInDB(AppointmentBase):
    appointment_id: uuid.UUID
    user_id: int
    nutritionist_id: int
    created_at: datetime
    updated_at: datetime
    
    # Fields missing in base but present in DB
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    provider_joined_at: Optional[datetime] = None

class Appointment(AppointmentInDB):
    pass

class AppointmentWithDetails(Appointment):
    user: Optional[UserOut] = None
    nutritionist: Optional[NutritionistOut] = None
    checklist_items: Optional[List[Any]] = None

class PaymentOrderCreate(BaseModel):
    amount: int