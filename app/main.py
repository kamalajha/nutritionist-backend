from fastapi import FastAPI
from datetime import datetime, timedelta
import logging
import asyncio 
from fastapi.middleware.cors import CORSMiddleware
from app import models
from app.routers import auth, users, nutritionists, appointments, checklists, notifications
# app/main.py
from app.database import engine, Base,init_db, SessionLocal
# Sabse pehle models ko import karein taaki wo register ho jayein
from app.models.user import User
from app.models.nutritionist import Nutritionist
from app.models.appointment import Appointment

from app.models.checklist import PreparationChecklist
from app.utils import send_app_notification
init_db()
logger = logging.getLogger(__name__)
# Phir metadata create karein
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Nutrition Appointment System API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
]
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(nutritionists.router)
app.include_router(appointments.router)
app.include_router(notifications.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Nutrition Appointment System API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
def check_and_send_reminders():
    """Har 1 minute mein chalne wala function"""
    db = SessionLocal()
    try:
        now = datetime.now()
        # Hum 2 minute ka buffer le rahe hain taaki koi miss na ho
        start_range = now + timedelta(minutes=14)
        end_range = now + timedelta(minutes=16)

        upcoming_appointments = db.query(Appointment).filter(
            Appointment.status == "confirmed",
            Appointment.appointment_date == now.date(),
            Appointment.start_time >= start_range.time(),
            Appointment.start_time <= end_range.time()
        ).all()

        for appt in upcoming_appointments:
            # 1. Client ka data fetch karein
            client = db.query(User).filter(User.user_id == appt.user_id).first()
            # 2. Nutritionist ka data fetch karein (Donon ko remind karna hai)
            nutri = db.query(Nutritionist).filter(Nutritionist.nutritionist_id == appt.nutritionist_id).first()

            if client:
                logger.info(f"Triggering 15-min reminder for User: {client.email}")
                # Async function ko sync scheduler mein chalane ka sahi tareeka
                asyncio.run(send_app_notification(
                    db=db,
                    user_id=client.user_id,
                    title="Meeting Starting Soon! ",
                    message=f"Your session with {nutri.full_name if nutri else 'Expert'} starts in 15 minutes. Please be ready.",
                    channel="email", # Ya "in_app" as per your need
                    email_to=client.email,
                    appt_id=appt.appointment_id
                ))

            if nutri:
                 logger.info(f"Triggering 15-min reminder for Doctor: {nutri.email}")
                 asyncio.run(send_app_notification(
                    db=db,
                    user_id=nutri.user_id, # Ensure your nutritionist model has a user_id link
                    title="Upcoming Session Reminder",
                    message=f"You have a session with {client.full_name} in 15 minutes.",
                    channel="email",
                    email_to=nutri.email,
                    appt_id=appt.appointment_id
                ))

    except Exception as e:
        logger.error(f"Scheduler Error: {e}")
    finally:
        db.close()