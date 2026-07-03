from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserRegister(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., max_length=255)
    role: str = Field("mother", pattern="^(mother|chw|facility_staff|partner)$")
    location: Optional[str] = Field(None, max_length=500)
    assigned_chw_id: Optional[int] = None

    @model_validator(mode="after")
    def verify_email_or_phone(self) -> 'UserRegister':
        if not self.email and not self.phone_number:
            raise ValueError("Either email or phone number must be provided")
        return self

class UserLogin(BaseModel):
    username: str # Can be email or phone number
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    full_name: str
    role: str
    location: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
