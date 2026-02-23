from sqlalchemy.orm import Session
from typing import List
import uuid
from app.models.checklist import PreparationChecklist
from app.schemas.checklist import ChecklistItemCreate, ChecklistItemUpdate

def get_checklist_item(db: Session, checklist_id: int):
    return db.query(PreparationChecklist).filter(PreparationChecklist.checklist_id == checklist_id).first()

def get_checklist_by_appointment(db: Session, appointment_id: uuid.UUID):
    return db.query(PreparationChecklist).filter(
        PreparationChecklist.appointment_id == appointment_id
    ).all()

def create_checklist_item(db: Session, checklist_item: ChecklistItemCreate):
    db_item = PreparationChecklist(**checklist_item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def create_bulk_checklist_items(db: Session, appointment_id: uuid.UUID, items: List[ChecklistItemCreate]):
    db_items = []
    for item in items:
        item_data = item.dict()
        item_data["appointment_id"] = appointment_id
        db_item = PreparationChecklist(**item_data)
        db.add(db_item)
        db_items.append(db_item)
    
    db.commit()
    for item in db_items:
        db.refresh(item)
    
    return db_items

def update_checklist_item(db: Session, checklist_id: int, checklist_update: ChecklistItemUpdate):
    db_item = get_checklist_item(db, checklist_id)
    if not db_item:
        return None
    
    update_data = checklist_update.dict(exclude_unset=True)
    if update_data.get("is_completed") and not db_item.is_completed:
        from datetime import datetime
        update_data["completed_at"] = datetime.utcnow()
    
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item