from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.auth import UserResponse

class SymptomLogCreate(BaseModel):
    symptoms: List[str]
    source: str = "pwa" # pwa, ussd, chatbot
    triage_notes: Optional[str] = None

class SymptomLogProxy(BaseModel):
    symptoms: List[str]
    triage_notes: Optional[str] = None

class SymptomLogResponse(BaseModel):
    id: int
    mother_profile_id: int
    symptoms: List[str]
    risk_score: Optional[str] = None
    source: str
    triage_notes: Optional[str] = None
    logged_at: datetime
    logged_by_id: Optional[int] = None
    logged_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
