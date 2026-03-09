from sqlalchemy import cast, String
import os
from dotenv import load_dotenv
import traceback
import requests # For making HTTP requests to cashfree API
from app.models.nutritionist import Nutritionist as NutritionistModel
from app.models.appointment import Appointment as AppointmentModel
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime,timedelta
import uuid
from app.models.notification import Notification
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.dependencies import get_current_active_user
from app.services.zoom_service import create_zoom_meeting
from app.crud.appointment import (
    get_appointments, get_appointment, create_appointment, update_appointment,
    cancel_appointment
)
from app.schemas.appointment import Appointment, AppointmentCreate, AppointmentUpdate, AppointmentWithDetails, PaymentOrderCreate
from app.schemas import appointment
load_dotenv()
router = APIRouter(prefix="/appointments", tags=["appointments"])
CASHFREE_APP_ID = os.getenv("CASHFREE_APP_ID")

CASHFREE_SECRET_KEY = os.getenv("CASHFREE_SECRET_KEY")
CASHFREE_URL = os.getenv("CASHFREE_URL")

@router.post("/", response_model=Appointment)
def create_new_appointment(
    appointment: AppointmentCreate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    appointment.user_id = current_user.user_id
    if current_user.role == "client" and current_user.user_id != appointment.user_id:
        raise HTTPException(status_code=403, detail="Can only book appointments for yourself")

   
    return create_appointment(db, appointment)

@router.get("/", response_model=List[AppointmentWithDetails])
def read_appointments(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    nutritionist_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "client":
        user_id = current_user.user_id
    elif current_user.role == "nutritionist":
        from app.crud.nutritionist import get_nutritionist_by_user_id
        nutritionist = get_nutritionist_by_user_id(db, current_user.user_id)
        if nutritionist:
            nutritionist_id = nutritionist.nutritionist_id
    
    return get_appointments(
        db, skip=skip, limit=limit, user_id=user_id,
        nutritionist_id=nutritionist_id, status=status,
        start_date=start_date, end_date=end_date
    )

@router.get("/{appointment_id}", response_model=AppointmentWithDetails)
def read_appointment(
    appointment_id: uuid.UUID,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_appointment = get_appointment(db, appointment_id)
    if db_appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if current_user.role == "client" and db_appointment.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    elif current_user.role == "nutritionist":
        from app.crud.nutritionist import get_nutritionist_by_user_id
        nutritionist = get_nutritionist_by_user_id(db, current_user.user_id)
        if nutritionist and db_appointment.nutritionist_id != nutritionist.nutritionist_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return db_appointment

# FIXED: Allow clients to reschedule their own appointments
@router.put("/{appointment_id}", response_model=Appointment)
def update_existing_appointment(
    appointment_id: uuid.UUID,
    appointment_update: AppointmentUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_appointment = get_appointment(db, appointment_id)
    if db_appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check permissions
    can_update = False
    
    if current_user.role == "admin":
        can_update = True
    elif current_user.role == "client" and db_appointment.user_id == current_user.user_id:
        # FIXED: Clients can now reschedule their own appointments
        can_update = True
        # Only allow clients to update date/time, not status or other fields
        if appointment_update.status and appointment_update.status != db_appointment.status:
            raise HTTPException(status_code=403, detail="Clients cannot change appointment status")
    elif current_user.role == "nutritionist":
        from app.crud.nutritionist import get_nutritionist_by_user_id
        nutritionist = get_nutritionist_by_user_id(db, current_user.user_id)
        if nutritionist and db_appointment.nutritionist_id == nutritionist.nutritionist_id:
            can_update = True
    
    if not can_update:
        raise HTTPException(status_code=403, detail="Not enough permissions to update this appointment")
    
    return update_appointment(db, appointment_id, appointment_update)

@router.post("/{appointment_id}/cancel")
def cancel_existing_appointment(
    appointment_id: uuid.UUID,
    reason: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return cancel_appointment(db, appointment_id, current_user.user_id, reason)


class PaymentRequest(BaseModel):
    appointment_id: Optional[uuid.UUID] = None
    nutritionist_id: Optional[int] = None
    appointment_date: str # Frontend se aayegi "2026-02-11"
    appointment_time: str # Frontend se aayegi "10:30"
    appointment_type: Optional[str] = "virtual"
    notes: Optional[str] = None

@router.post("/create-payment-order")
async def create_payment_order(
    req: PaymentRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    try:
        generated_order_id = f"order_{uuid.uuid4().hex[:12]}"
        
        # 1. Nutritionist ki fee fetch karo
        nutritionist = db.query(NutritionistModel).filter(
            NutritionistModel.nutritionist_id == req.nutritionist_id
        ).first()
        
        if not nutritionist:
            raise HTTPException(status_code=404, detail="Nutritionist not found")
        
        fee = nutritionist.hourly_rate

        # 2. Parse date and time (Simple parsing)
        appt_date = datetime.strptime(req.appointment_date, "%Y-%m-%d").date()
        
        # Backend safety check for HH:MM:SS format
        time_val = req.appointment_time
        if len(time_val.split(':')) == 2:
            time_val += ":00"
        appt_time = datetime.strptime(time_val, "%H:%M:%S").time()

        # 3. New appointment create karo (Pending status)
        new_appt = AppointmentModel(
            appointment_id=uuid.uuid4(),
            user_id=current_user.user_id,
            nutritionist_id=req.nutritionist_id,
            appointment_date=appt_date,
            start_time=appt_time,
            appointment_type=req.appointment_type or "virtual",
            end_time=None,
            notes=req.notes,
            status="scheduled",
            payment_status="PENDING",
            cashfree_order_id=generated_order_id,
            amount=int(fee) # Payment gateway ke liye amount
        )
        db.add(new_appt)
        db.commit()
        db.refresh(new_appt)

        # 4. Cashfree payload (Simplified)
        order_payload = {
            "order_id": generated_order_id,
            "order_amount": float(fee),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": f"CUST_{current_user.user_id}",
                "customer_email": current_user.email,
                "customer_phone": getattr(current_user, "contact_number", "9999999999")[-10:]
            }
        }

        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }

        # 5. Cashfree API call
        response = requests.post(CASHFREE_URL, json=order_payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            return {
                "payment_session_id": response_data.get("payment_session_id"),
                "order_id": generated_order_id,
                "appointment_id": str(new_appt.appointment_id)
            }
        else:
            db.delete(new_appt)
            db.commit()
            raise HTTPException(status_code=400, detail=response_data.get("message"))

    except Exception as e:
        db.rollback()
        print(f"Payment Order Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


from sqlalchemy import cast, String
import requests

# app/routers/appointments.py

@router.get("/verify-payment/{order_id}")
async def verify_payment(order_id: str, db: Session = Depends(get_db)):
    try:
        # 1. Cashfree se status check karo
        url = f"{CASHFREE_URL}/{order_id}"
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01"
        }

        response = requests.get(url, headers=headers)
        data = response.json()
        order_status = data.get("order_status")

        # 2. Database mein appointment aur user details find karo
        appointment = db.query(AppointmentModel).filter(
            AppointmentModel.cashfree_order_id == order_id
        ).first()

        if not appointment:
            return {"status": "failed", "details": "Appointment not found in database"}

        # 3. Status ke according update karo
       # ... (Aapka pichle code ka logic yahan tak sahi hai) ...
        if order_status == "PAID":
            if appointment.status == "confirmed":
                return {"status": "success", "appointment_id": str(appointment.appointment_id)}

            zoom_time = f"{appointment.appointment_date}T{appointment.start_time.strftime('%H:%M:%S')}"
            
            try:
                from app.models.user import User as UserModel
                patient = db.query(UserModel).filter(UserModel.user_id == appointment.user_id).first()
                patient_name = patient.full_name if patient else "Patient"

                print(f"DEBUG: Processing order {order_id}")
                zoom_meeting = create_zoom_meeting(
                    topic=f"Nutrition Session with {patient_name}",
                    start_time_str=zoom_time
                )
                print(f"DEBUG: Zoom Response -> {zoom_meeting}")
                
                # Check karein ki Zoom ne link diya ya nahi
                meeting_url = zoom_meeting.get("join_url") if zoom_meeting else None
                
            except Exception as e:
                print(f"Zoom Logic Crash: {e}")
                meeting_url = None

            #  IMPORTANT: Agar Zoom fail hua toh backup link do
            if not meeting_url:
                meeting_url = f"https://meet.jit.si/nutrition-backup-{uuid.uuid4().hex[:8]}"
            
            #  DATABASE UPDATE (Ye part aapka missing tha)
            appointment.status = "confirmed"
            appointment.payment_status = "SUCCESS"
            appointment.meeting_url = meeting_url
            appointment.transaction_id = data.get("cf_order_id")
            
            db.commit() # Database mein save karo!
            db.refresh(appointment)
            
            print(f"DEBUG: Appointment {appointment.appointment_id} confirmed with link: {meeting_url}")
            return {"status": "success", "appointment_id": str(appointment.appointment_id), "meeting_url": meeting_url}
    except Exception as e:
        db.rollback()
        print(f"Verification Error: {str(e)}")
        return {"status": "error", "details": str(e)}
@router.delete("/{appointment_id}")
def delete_appointment(
    
    appointment_id: uuid.UUID,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_appointment = get_appointment(db, appointment_id)
    if db_appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check permissions
    can_delete = False
    if current_user.role == "admin":
        can_delete = True
    elif current_user.role == "client" and db_appointment.user_id == current_user.user_id:
        can_delete = True
    elif current_user.role == "nutritionist":
        from app.crud.nutritionist import get_nutritionist_by_user_id
        nutritionist = get_nutritionist_by_user_id(db, current_user.user_id)
        if nutritionist and db_appointment.nutritionist_id == nutritionist.nutritionist_id:
            can_delete = True
    
    if not can_delete:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Mark as cancelled instead of deleting

    db_appointment.status = "cancelled"
    db_appointment.cancelled_by = current_user.user_id
    db_appointment.cancellation_reason = "Cancelled by user"
    db_appointment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_appointment)
    
    return {"message": "Appointment cancelled successfully"}
    
    # app/routers/appointments.py

# 1. Jab koi meeting join kare (Start)
@router.post("/{appointment_id}/start-session")
async def start_session(appointment_id: uuid.UUID, db: Session = Depends(get_db)):

    appointment = db.query(AppointmentModel).filter(
        AppointmentModel.appointment_id == appointment_id
    ).first()

    appointment.actual_start_time = datetime.utcnow()
    appointment.status = "confirmed"

    db.commit()

    return {
        "message": "Session started",
        "meeting_url": appointment.meeting_url  # database se meeting URL bhejo
    }

@router.post("/{appointment_id}/end-session")
async def end_session(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    appointment = db.query(AppointmentModel).filter(
        AppointmentModel.appointment_id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.actual_end_time = datetime.utcnow()   # 👈 YAHAN SE AATA HAI
    appointment.status = "completed"

    db.commit()
    db.refresh(appointment)
    return {
        "message": "Session ended successfully",
        "actual_end_time": appointment.actual_end_time
    }


@router.get("/nutritionists/{id}/slots")
def get_auto_slots(id: int, date: str, db: Session = Depends(get_db)):
    # 1. Fixed timing setup
    start_working = datetime.strptime("10:00", "%H:%M")
    end_working = datetime.strptime("17:00", "%H:%M")
    slot_duration = 30 # minutes
    
    # 2. DB se booked appointments nikalo
    booked_appointments = db.query(AppointmentModel).filter(
        AppointmentModel.nutritionist_id == id, 
        AppointmentModel.appointment_date == date,
        AppointmentModel.status != "cancelled"
    ).all()
    
    # 3. Booked slots ki range nikalo
    # Hum sirf start_time nahi, end_time tak block karenge
    blocked_ranges = []
    for a in booked_appointments:
        if a.start_time and a.end_time:
            blocked_ranges.append((a.start_time, a.end_time))
    
    available_slots = []
    current = start_working
    
    while current < end_working:
        current_time = current.time()
        is_booked = False
        
        # Check karo ki current slot kisi blocked range ke andar toh nahi hai
        for b_start, b_end in blocked_ranges:
            if current_time >= b_start and current_time < b_end:
                is_booked = True
                break
        
        available_slots.append({
            "time": current_time.strftime("%H:%M"),
            "is_available": not is_booked
        })
        current += timedelta(minutes=slot_duration)
        
    return available_slots