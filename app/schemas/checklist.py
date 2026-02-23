from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

class ChecklistItemBase(BaseModel):
    item_type: Optional[str] = None
    item_text: str

class ChecklistItemCreate(ChecklistItemBase):
    appointment_id: uuid.UUID

class ChecklistItemUpdate(BaseModel):
    is_completed: Optional[bool] = None

class ChecklistItemInDB(ChecklistItemBase):
    checklist_id: int
    appointment_id: uuid.UUID
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ChecklistItem(ChecklistItemInDB):
    pass