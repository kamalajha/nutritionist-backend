from sqlalchemy.orm import Session,joinedload
from typing import Optional, List
from datetime import datetime,timedelta
import uuid

from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate

def get_appointment(db: Session, appointment_id: uuid.UUID):
    return db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()

def get_appointments(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    user_id: Optional[int] = None,
    nutritionist_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    query = db.query(Appointment).options( joinedload(Appointment.user), joinedload(Appointment.nutritionist) )
    
    if user_id:
        query = query.filter(Appointment.user_id == user_id)
    if nutritionist_id:
        query = query.filter(Appointment.nutritionist_id == nutritionist_id)
    if status:
        query = query.filter(Appointment.status == status)
    if start_date:
        query = query.filter(Appointment.appointment_date >= start_date)
    if end_date:
        query = query.filter(Appointment.appointment_date <= end_date)
    
    return query.offset(skip).limit(limit).all()

from datetime import datetime, timedelta

def create_appointment(db: Session, appointment: AppointmentCreate):
    # 1. Schema data ko dictionary mein convert karein
    appointment_data = appointment.model_dump()
    
    # 2. Agar end_time None hai, toh default 1 hour set karein
    if appointment_data.get("end_time") is None:
        # start_time ko temporary datetime mein convert karein calculation ke liye
        temp_dt = datetime.combine(datetime.today(), appointment_data["start_time"])
        
        # 60 minutes add karein ➕
        new_end_dt = temp_dt + timedelta(hours=1)
        
        # Wapas 'time' object nikal kar set karein
        appointment_data["end_time"] = new_end_dt.time()
    if appointment_data.get("appointment_type") == "virtual":
    # Ek unique room name banate hain uuid se 🆔
           unique_room = str(uuid.uuid4())[:8]
    
    # Jitsi ka standard format use karke URL set karte hain 
           appointment_data["meeting_url"] = f"https://meet.jit.si/TrackIntake-{unique_room}"
    else:
    # Agar in_person hai toh link ki zaroorat nahi 
           appointment_data["meeting_url"] = None
    # 3. Database object banayein aur save karein
    db_appointment = Appointment(**appointment_data)
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

def update_appointment(db: Session, appointment_id: uuid.UUID, appointment_update: AppointmentUpdate):
    db_appointment = get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    
    update_data = appointment_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_appointment, key, value)
    
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

def cancel_appointment(db: Session, appointment_id: uuid.UUID, cancelled_by: int, reason: str):
    db_appointment = get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    
    db_appointment.status = "cancelled"
    db_appointment.cancelled_by = cancelled_by
    db_appointment.cancellation_reason = reason
    
    db.commit()
    db.refresh(db_appointment)
    return db_appointment