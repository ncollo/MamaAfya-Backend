from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any
from datetime import date, datetime
from app.schemas.auth import UserResponse

class MotherProfileCreate(BaseModel):
    gestational_age_weeks: Optional[int] = Field(None, ge=1, le=45)
    expected_delivery_date: Optional[date] = None
    last_menstrual_period: Optional[date] = None
    blood_type: Optional[str] = Field(None, max_length=5)
    medical_history: Optional[Dict[str, Any]] = None
    allergies: Optional[str] = None
    nearest_facility: Optional[str] = Field(None, max_length=255)
    partner_user_id: Optional[int] = None

class MotherProfileUpdate(BaseModel):
    gestational_age_weeks: Optional[int] = Field(None, ge=1, le=45)
    expected_delivery_date: Optional[date] = None
    last_menstrual_period: Optional[date] = None
    blood_type: Optional[str] = Field(None, max_length=5)
    medical_history: Optional[Dict[str, Any]] = None
    allergies: Optional[str] = None
    nearest_facility: Optional[str] = Field(None, max_length=255)
    pregnancy_status: Optional[str] = Field(None, pattern="^(antenatal|postpartum)$")
    risk_level: Optional[str] = Field(None, pattern="^(green|yellow|red)$")
    partner_user_id: Optional[int] = None

class MotherProfileResponse(BaseModel):
    id: int
    user_id: int
    gestational_age_weeks: Optional[int] = None
    expected_delivery_date: Optional[date] = None
    last_menstrual_period: Optional[date] = None
    blood_type: Optional[str] = None
    medical_history: Optional[Dict[str, Any]] = None
    allergies: Optional[str] = None
    nearest_facility: Optional[str] = None
    pregnancy_status: str
    risk_level: str
    partner_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
