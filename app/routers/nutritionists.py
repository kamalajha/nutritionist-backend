from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_active_user, require_role

# Naming collision bachane ke liye aliasing
from app.schemas.nutritionist import (
    Nutritionist as NutritionistSchema, 
    NutritionistCreate, 
    NutritionistUpdate
)
from app.models.nutritionist import Nutritionist as NutritionistModel
from app.models.appointment import Slot
from app.routers.auth import get_current_user

router = APIRouter(prefix="/nutritionists", tags=["nutritionists"])

# --- NUTRITIONIST PROFILE ROUTES ---

@router.post("/", response_model=NutritionistSchema)
def create_new_nutritionist(
    nutritionist: NutritionistCreate,
    current_user = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    from app.crud.nutritionist import create_nutritionist
    return create_nutritionist(db, nutritionist)

@router.get("/", response_model=List[NutritionistSchema])
def read_nutritionists(
    skip: int = 0,
    limit: int = 100,
    accepting_patients: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    from app.crud.nutritionist import get_nutritionists
    return get_nutritionists(db, skip=skip, limit=limit, accepting_patients=accepting_patients)

@router.get("/{nutritionist_id}", response_model=NutritionistSchema)
def read_nutritionist(nutritionist_id: int, db: Session = Depends(get_db)):
    db_nutritionist = db.query(NutritionistModel).filter(NutritionistModel.nutritionist_id == nutritionist_id).first()
    if db_nutritionist is None:
        raise HTTPException(status_code=404, detail="Nutritionist not found")
    return db_nutritionist

# --- SLOTS LOGIC (FIXED & FULL) ---

@router.get("/slots/available/{nutritionist_id}")
def get_available_slots(nutritionist_id: int, date: str, db: Session = Depends(get_db)):
    # Patient side logic: Filter by nutritionist_id
    slots = db.query(Slot).filter(
        Slot.nutritionist_id == nutritionist_id,
        Slot.slot_date == date,
        Slot.is_available == True
    ).all()
    print(f"DEBUG: Found {len(slots)} slots for nutri_{nutritionist_id} on {date}")
    return slots

@router.post("/add-manual-slot")
def add_manual_slot(
    date: str, 
    start: str, 
    end: str, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. User ID (auth) se Nutritionist Table ki ID nikalna
    nutritionist = db.query(NutritionistModel).filter(NutritionistModel.user_id == current_user.user_id).first()
    
    if not nutritionist:
        raise HTTPException(status_code=404, detail="Nutritionist profile not found for this user.")

    # 2. Overlap Check
    existing = db.query(Slot).filter(
        Slot.slot_date == date,
        Slot.start_time == start,
        Slot.nutritionist_id == nutritionist.nutritionist_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Bhai, ye slot pehle se bana hua hai!")

    # 3. Create Slot with proper nutritionist_id
    new_slot = Slot(
        nutritionist_id=nutritionist.nutritionist_id,
        slot_date=date,
        start_time=start,
        end_time=end,
        is_available=True,
        is_booked=False
    )
    db.add(new_slot)
    db.commit()
    
    return {"message": "Slot added successfully!", "nutritionist_id": nutritionist.nutritionist_id}

@router.get("/slots/my-slots")
def get_doctor_slots(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Doctor side: Get all slots for the logged-in nutritionist
    nutritionist = db.query(NutritionistModel).filter(NutritionistModel.user_id == current_user.user_id).first()
    if not nutritionist:
        return {"available_slots": [], "booked_slots": []}

    all_slots = db.query(Slot).filter(Slot.nutritionist_id == nutritionist.nutritionist_id).all()
    
    return {
        "available_slots": [s for s in all_slots if s.is_available],
        "booked_slots": [s for s in all_slots if not s.is_available]
    }

@router.delete("/remove-slot/{slot_id}")
def delete_slot(slot_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    nutritionist = db.query(NutritionistModel).filter(NutritionistModel.user_id == current_user.user_id).first()
    
    slot = db.query(Slot).filter(
        Slot.slot_id == slot_id, 
        Slot.doctor_id == nutritionist.nutritionist_id
    ).first()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found!")
    
    db.delete(slot)
    db.commit()
    return {"message": "Slot successfully removed!"}