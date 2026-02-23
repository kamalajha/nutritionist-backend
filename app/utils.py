from datetime import datetime, timedelta
import uuid
from jose import jwt
from app.config import settings
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
mail_conf= ConnectionConfig(
MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True
)
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

from datetime import datetime, timedelta
from jose import jwt
from app.config import settings

from app.models.notification import Notification # Jo table aapne banayi hai
from sqlalchemy.orm import Session
import uuid

# 1. Email Configuration (FastAPI-Mail)
# Isse .env se connect karna best hai
mail_conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True
)

# --- Existing JWT Logic ---
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# --- New Notification Logic ---

async def send_app_notification(
    db: Session, 
    user_id: int, 
    title: str, 
    message: str, 
    channel: str = "in_app", 
    email: str = None,
    appointment_id: uuid.UUID = None
):
    """
    Ek sath In-App entry aur Email bhejta hai.
    """
    try:
        # 1. DB entry (Hamesha save hogi taaki history rahe)
        new_notif = Notification(
            user_id=user_id,
            appointment_id=appointment_id,
            title=title,
            message=message,
            channel=channel,
            status="pending"
        )
        db.add(new_notif)
        db.commit()

        # 2. Email sending (Sirf agar channel email hai)
        if channel == "email" and email:
            message_schema = MessageSchema(
                subject=title,
                recipients=[email],
                body=f"<html><body><h2>{title}</h2><p>{message}</p></body></html>",
                subtype="html"
            )
            fm = FastMail(mail_conf)
            await fm.send_message(message_schema)
            
            # Status update as sent
            new_notif.status = "sent"
            new_notif.sent_at = datetime.utcnow()
            db.commit()

        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        db.rollback()
        return False