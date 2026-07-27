from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class BirthPlanCreate(BaseModel):
    preferred_facility: Optional[str] = None
    birth_companion_name: Optional[str] = None
    birth_companion_phone: Optional[str] = None
    transport_plan: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    preferred_delivery_method: Optional[str] = None
    special_requests: Optional[str] = None
    items_prepared: Optional[Dict[str, bool]] = None

class BirthPlanUpdate(BaseModel):
    preferred_facility: Optional[str] = None
    birth_companion_name: Optional[str] = None
    birth_companion_phone: Optional[str] = None
    transport_plan: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    preferred_delivery_method: Optional[str] = None
    special_requests: Optional[str] = None
    items_prepared: Optional[Dict[str, bool]] = None

class BirthPlanResponse(BaseModel):
    id: int
    mother_profile_id: int
    preferred_facility: Optional[str] = None
    birth_companion_name: Optional[str] = None
    birth_companion_phone: Optional[str] = None
    transport_plan: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    preferred_delivery_method: Optional[str] = None
    special_requests: Optional[str] = None
    items_prepared: Optional[Dict[str, bool]] = None
    is_finalized: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
