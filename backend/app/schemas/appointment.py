from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AppointmentCreate(BaseModel):
    mother_profile_id: int
    appointment_type: str
    scheduled_date: datetime
    facility_name: Optional[str] = None
    notes: Optional[str] = None

class AppointmentUpdate(BaseModel):
    appointment_type: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    status: Optional[str] = None # upcoming, completed, missed, cancelled
    facility_name: Optional[str] = None
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: int
    mother_profile_id: int
    appointment_type: str
    scheduled_date: datetime
    status: str
    facility_name: Optional[str] = None
    notes: Optional[str] = None
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
