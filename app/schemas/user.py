from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    timezone: str = "UTC"
    role: str  # client, nutritionist, admin
    notification_preferences: Dict[str, bool] = {"email": True, "push": True}

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = None
    timezone: Optional[str] = None
    notification_preferences: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    user_id: int
    profile_image: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class User(UserInDB):
    pass

# Authentication
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
class UserOut(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    
    # Yeh config zaroori hai taaki SQLAlchemy models 
    # automatically Pydantic objects mein badal sakein
    model_config = {
        "from_attributes": True
    }