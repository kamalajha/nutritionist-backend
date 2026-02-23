from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# 1. Base Schema
class NutritionistBase(BaseModel):
    # 'full_name' ko Base se hata kar 'Out' mein rakha hai kyunki ye JOIN se aata hai
    type:Optional[str] = "expert"  # Default value set kiya
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[Decimal] = None
    available_days: List[str] = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    working_hours: Optional[Dict[str, Any]] = None # Optional kiya taaki null pe crash na ho
    accepting_patients: bool = True

# 2. Create Schema
class NutritionistCreate(NutritionistBase):
    user_id: int

# 3. Update Schema
class NutritionistUpdate(BaseModel):
    type: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[Decimal] = None
    available_days: Optional[List[str]] = None
    working_hours: Optional[Dict[str, Any]] = None
    accepting_patients: Optional[bool] = None

# 4. InDB Schema (Database table ke columns)
class NutritionistInDB(NutritionistBase):
    nutritionist_id: int
    user_id: int
    rating: Decimal = Decimal("0.00")
    total_sessions: int = 0
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# 5. Final Schema for Frontend (Join data ke saath)
class NutritionistOut(NutritionistInDB):
    full_name: Optional[str] = None
    profile_image: Optional[str] = None # DB renamed column sync
    contact: Optional[str] = None       # Map to contact_number
    location: Optional[str] = "Indore, India"
    experience:Optional[str] = None
    hourly_rate:Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)

# Compatibility alias
class Nutritionist(NutritionistOut):
    pass