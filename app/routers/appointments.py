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
# app/routers/appointments.py

class PaymentRequest(BaseModel):
    appointment_id: Optional[uuid.UUID] = None
    nutritionist_id: Optional[int] = None
    appointment_date: str # Frontend se aayegi "2026-02-11"
    appointment_time: str # Frontend se aayegi "10:30"
    appointment_type: Optional[str] = "virtual"
    notes: Optional[str] = None

# app/routers/appointments.py

@router.post("/create-payment-order")
async def create_payment_order(
    req: PaymentRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    try:
        generated_order_id = f"order_{uuid.uuid4().hex[:12]}"
        fee = 0
        
        # Nutritionist ki fee fetch karo
        if req.nutritionist_id:
            n = db.query(NutritionistModel).filter(
                NutritionistModel.nutritionist_id == req.nutritionist_id
            ).first()
            if not n:
                raise HTTPException(status_code=404, detail="Nutritionist not found")
            fee = n.hourly_rate
        else:
            raise HTTPException(status_code=400, detail="Nutritionist ID required")

        # Parse date and time properly
        from datetime import datetime, time as dt_time
        
        appt_date = datetime.strptime(req.appointment_date, "%Y-%m-%d").date()
        appt_time = datetime.strptime(req.appointment_time, "%H:%M").time()
        
        # End time calculate karo (1 hour later)
        from datetime import timedelta
        start_datetime = datetime.combine(appt_date, appt_time)
        end_datetime = start_datetime + timedelta(hours=1)
        end_time = end_datetime.time()

        # New appointment create karo with pending status
        new_appt = AppointmentModel(
            appointment_id=uuid.uuid4(),
            user_id=current_user.user_id,
            nutritionist_id=req.nutritionist_id,
            appointment_date=appt_date,
            start_time=appt_time,      # Booking start time
            end_time=end_time,          # Booking end time (1hr later)
            appointment_type=req.appointment_type or "virtual",
            notes=req.notes,
            status="scheduled",
            payment_status="PENDING",
            cashfree_order_id=generated_order_id,
            amount=int(fee * 100),
            
            actual_start_time=None, 
            actual_end_time=None
        )
        db.add(new_appt)
        db.commit()
        db.refresh(new_appt)

        # Phone formatting
        phone = getattr(current_user, "contact_number", "9123456789")
        clean_phone = "".join(filter(str.isdigit, str(phone)))
        final_phone = clean_phone[2:] if len(clean_phone) == 12 and clean_phone.startswith("91") else clean_phone[-10:]

        # Cashfree payload
        order_payload = {
            "order_id": generated_order_id,
            "order_amount": float(fee),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": f"CUST_{current_user.user_id}",
                "customer_email": current_user.email,
                "customer_phone": final_phone
            }
        }

        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }

        # Cashfree API call
        response = requests.post(CASHFREE_URL, json=order_payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            return {
                "payment_session_id": response_data.get("payment_session_id"),
                "order_id": generated_order_id,
                "appointment_id": str(new_appt.appointment_id)  # Frontend ko appointment ID bhi bhejo
            }
        else:
            # Agar Cashfree fail ho gaya, appointment delete karo
            db.delete(new_appt)
            db.commit()
            raise HTTPException(status_code=400, detail=response_data.get("message"))

    except Exception as e:
        db.rollback()
     
        error_details = traceback.format_exc() 
        print("---------- CRASH LOG START ----------")
        print(error_details)
        print("---------- CRASH LOG END ------------")
        
        # Frontend ko bhi detail bhej dein (Sirf debugging ke liye)
        raise HTTPException(
            status_code=500, 
            detail=f"Backend Error: {str(e)} | Details: {error_details[:100]}..."
        )

from sqlalchemy import cast, String
import requests

# app/routers/appointments.py

@router.get("/verify-payment/{order_id}")
async def verify_payment(order_id: str, db: Session = Depends(get_db)):
    try:
        # Cashfree se status check karo
        url = f"{CASHFREE_URL}/{order_id}"
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01"
        }

        response = requests.get(url, headers=headers)
        data = response.json()
        order_status = data.get("order_status")

        # Database mein appointment find karo
        appointment = db.query(AppointmentModel).filter(
            AppointmentModel.cashfree_order_id == order_id
        ).first()

        if not appointment:
            return {"status": "failed", "details": "Appointment not found in database"}

        # Status ke according update karo
        if order_status == "PAID":
            #  Meeting URL generation
            import uuid
            meeting_id = str(uuid.uuid4())[:8]
            meeting_url = f"https://meet.jit.si/nutrition-{meeting_id}"
            
            appointment.status = "confirmed"
            appointment.payment_status = "SUCCESS"
            appointment.transaction_id = data.get("cf_order_id")
            appointment.meeting_url = meeting_url  #Meeting URL add karo
            db.commit()
            print(f"Success: Order {order_id} verified and confirmed")
            return {"status": "success", "appointment_id": str(appointment.appointment_id)}
        
        elif order_status in ["ACTIVE", "PENDING"]:
            return {"status": "pending", "details": "Payment is still in progress"}
        
        else:  # FAILED, EXPIRED, etc
            appointment.status = "cancelled"
            appointment.payment_status = "FAILED"
            db.commit()
            return {"status": "failed", "details": order_status}

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

    return {
        "message": "Session ended successfully",
        "actual_end_time": appointment.actual_end_time
    }

@router.get("/nutritionists/{id}/slots")
def get_auto_slots(id: int, date: str, db: Session = Depends(get_db)):
    # 1. Fixed timing (10 AM to 5 PM)
    start_time = datetime.strptime("10:00", "%H:%M")
    end_time = datetime.strptime("17:00", "%H:%M")
    slot_duration = 30 # minutes
    
    # 2. DB se check karein kaunse slots booked hain
    # Maan lijiye aapki appointments table mein 'appointment_date' aur 'appointment_time' hai
    booked_appointments = db.query(AppointmentModel).filter(
        AppointmentModel.nutritionist_id == id, 
        AppointmentModel.appointment_date == date,
        AppointmentModel.status != "cancelled" # Sirf wahi jo cancel nahi hue
    ).all()
    
#   booked_times = [a.appointment_time.strftime("%H:%M") for a in booked_appointments]
    booked_times = []
    for a in booked_appointments:
        t = a.start_time # Aapne model mein start_time use kiya hai
        if t:
            booked_times.append(t.strftime("%H:%M") if hasattr(t, 'strftime') else str(t)[:5])
   
    available_slots = []
    current = start_time
    while current < end_time:
        time_str = current.strftime("%H:%M")
        available_slots.append({
            "time": time_str,
            "is_available": time_str not in booked_times
        })
        current += timedelta(minutes=slot_duration)
        
    return available_slots