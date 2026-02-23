
from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.nutritionist import Nutritionist
from app.models.user import User

# 1. Single Nutritionist fetch karna (with User details)
def get_nutritionist(db: Session, nutritionist_id: int):
    # Join query using correct primary key 'user_id' from your schema
    result = db.query(
        Nutritionist, 
        User.full_name, 
        User.profile_image,
        User.contact_number
    ).join(User, Nutritionist.user_id == User.user_id).filter(
        Nutritionist.nutritionist_id == nutritionist_id
    ).first()
    
    if result:
        nutri, name, image, phone = result
        nutri.full_name = name            # Mapping 'full_name'
        nutri.profile_image = image       # Mapping 'profile_image_url'
        nutri.contact = phone             # Mapping 'contact_number'
        return nutri
    return None

# 2. Saare Nutritionists fetch karna (Cards ke liye)
def get_nutritionists(db: Session, skip: int = 0, limit: int = 100, accepting_patients: Optional[bool] = None):
    query = db.query(
        Nutritionist, 
        User.full_name, 
        User.profile_image, 
        User.contact_number,
        Nutritionist.created_at,
    ).join(User, Nutritionist.user_id == User.user_id) # PK 'user_id' used
    
    if accepting_patients is not None:
        query = query.filter(Nutritionist.accepting_patients == accepting_patients)
    
    results = query.offset(skip).limit(limit).all()
    
    output = []
    for nutri, name, image, phone,created in results:
        # Pydantic schema ke hisaab se attributes set kar rahe hain
        nutri.full_name = name
        nutri.profile_image = image
        nutri.contact = phone
        nutri.location = "Indore, India" # Default static location
        nutri.created_at = created
        output.append(nutri)
        
    return output

# 3. User ID ke base par nutritionist dhundna (Incomplete part fixed)
def get_nutritionist_by_user_id(db: Session, user_id: int):
    result = db.query(
        Nutritionist, 
        User.full_name, 
        User.profile_image,
        User.contact_number
    ).join(User, Nutritionist.user_id == User.user_id).filter(
        Nutritionist.user_id == user_id
    ).first()
    
    if result:
        nutri, name, image, phone = result
        nutri.full_name = name
        nutri.profile_image = image
        nutri.contact = phone
        return nutri
    return None

# 4. Naya Nutritionist create karna
def create_nutritionist(db: Session, nutritionist_data):
    db_nutritionist = Nutritionist(**nutritionist_data.dict())
    db.add(db_nutritionist)
    db.commit()
    db.refresh(db_nutritionist)
    return db_nutritionist

# 5. Nutritionist details update karna
def update_nutritionist(db: Session, nutritionist_id: int, nutritionist_update):
    db_nutritionist = db.query(Nutritionist).filter(
        Nutritionist.nutritionist_id == nutritionist_id
    ).first()
    
    if not db_nutritionist:
        return None
        
    update_data = nutritionist_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_nutritionist, key, value)
        
    db.commit()
    db.refresh(db_nutritionist)
    return db_nutritionist

# 6. Delete Nutritionist
def delete_nutritionist(db: Session, nutritionist_id: int):
    db_nutritionist = db.query(Nutritionist).filter(
        Nutritionist.nutritionist_id == nutritionist_id
    ).first()
    if db_nutritionist:
        db.delete(db_nutritionist)
        db.commit()
        return True
    return False