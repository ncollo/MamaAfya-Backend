from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.mother_profile import MotherProfile
from app.models.symptom_log import SymptomLog
from app.models.appointment import Appointment
from app.schemas.mother_profile import MotherProfileCreate, MotherProfileUpdate, MotherProfileResponse
from app.schemas.symptom_log import SymptomLogResponse
from app.schemas.appointment import AppointmentResponse
from app.middleware.auth import get_current_user, require_role
from pydantic import BaseModel
from app.services.triage_interface import run_triage

class SOSRequest(BaseModel):
    note: Optional[str] = None
    
class BotpressSymptomPayload(BaseModel):
    phone_number: str
    symptoms: List[str]
    risk_level: str = "yellow"
    notes: Optional[str] = None
    
class BookVisitRequest(BaseModel):
    reason: Optional[str] = None
    phone_number: Optional[str] = None

router = APIRouter(prefix="/api/mothers", tags=["Mother Profiles"])

@router.post("/profile", response_model=MotherProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_in: MotherProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Create a profile for the currently logged-in mother"""
    # Check if profile already exists
    result = await db.execute(select(MotherProfile).where(MotherProfile.user_id == current_user.id))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mother profile already exists for this user"
        )
        
    db_profile = MotherProfile(
        user_id=current_user.id,
        gestational_age_weeks=profile_in.gestational_age_weeks,
        expected_delivery_date=profile_in.expected_delivery_date,
        last_menstrual_period=profile_in.last_menstrual_period,
        blood_type=profile_in.blood_type,
        medical_history=profile_in.medical_history or {},
        allergies=profile_in.allergies,
        nearest_facility=profile_in.nearest_facility,
        partner_user_id=profile_in.partner_user_id
    )
    
    db.add(db_profile)
    await db.commit()
    
    # Refresh with loaded user relation
    stmt = select(MotherProfile).where(MotherProfile.id == db_profile.id).options(selectinload(MotherProfile.user))
    res = await db.execute(stmt)
    return res.scalars().first()

@router.post("/profile-by-chw/{new_user_id}", response_model=MotherProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile_for_patient(
    new_user_id: int,
    profile_in: MotherProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw", "facility_staff"))
):
    """Allows a CHW to create a medical profile for a newly registered mother"""
    
    # 1. Verify the profile doesn't already exist
    result = await db.execute(select(MotherProfile).where(MotherProfile.user_id == new_user_id))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists for this patient"
        )

    # 2. Create the profile mapping it to the NEW user's ID, not the CHW's ID
    db_profile = MotherProfile(
        user_id=new_user_id,
        last_menstrual_period=profile_in.last_menstrual_period,
        medical_history={},
        allergies=None,
        nearest_facility=None
    )
    
    db.add(db_profile)
    await db.commit()
    
    # 3. Refresh and return
    stmt = select(MotherProfile).where(MotherProfile.id == db_profile.id).options(selectinload(MotherProfile.user))
    res = await db.execute(stmt)
    return res.scalars().first()

@router.get("/profile", response_model=MotherProfileResponse)
async def get_own_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Get the profile of the current authenticated mother"""
    stmt = select(MotherProfile).where(MotherProfile.user_id == current_user.id).options(selectinload(MotherProfile.user))
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found. Please create one."
        )
    return profile

@router.get("/profile/{profile_id}", response_model=MotherProfileResponse)
async def get_mother_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw", "facility_staff"))
):
    """Get any mother's profile (accessible by CHWs and facility staff)"""
    stmt = select(MotherProfile).where(MotherProfile.id == profile_id).options(selectinload(MotherProfile.user))
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found"
        )
    return profile

@router.put("/profile/{profile_id}", response_model=MotherProfileResponse)
async def update_profile(
    profile_id: int,
    profile_in: MotherProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a mother's profile. Mothers can update their own. CHWs can update their assigned mothers' profiles."""
    stmt = select(MotherProfile).where(MotherProfile.id == profile_id).options(selectinload(MotherProfile.user))
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found"
        )
        
    # Check permissions
    if current_user.role == "mother" and profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    elif current_user.role == "chw" and profile.user.assigned_chw_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update profiles of mothers assigned to you"
        )
    elif current_user.role not in ["mother", "chw", "facility_staff"]:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to update profiles"
        )

    # Apply updates
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
        
    await db.commit()
    await db.refresh(profile)
    return profile

@router.delete("/profile/{profile_id}", status_code=status.HTTP_200_OK)
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("facility_staff"))
):
    """Soft delete a profile by marking the user as inactive"""
    stmt = select(MotherProfile).where(MotherProfile.id == profile_id).options(selectinload(MotherProfile.user))
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found"
        )
        
    profile.user.is_active = False
    await db.commit()
    return {"detail": "Mother profile soft deleted successfully"}

@router.get("/symptom-logs", response_model=List[SymptomLogResponse])
async def get_own_symptom_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Get the current logged-in mother's symptom history"""
    # Fetch profile first
    res = await db.execute(select(MotherProfile).where(MotherProfile.user_id == current_user.id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found"
        )
        
    logs_res = await db.execute(
        select(SymptomLog)
        .where(SymptomLog.mother_profile_id == profile.id)
        .order_by(SymptomLog.logged_at.desc()) # Order latest first
    )
    return logs_res.scalars().all()

@router.get("/appointments", response_model=List[AppointmentResponse])
async def get_own_appointments(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Get the current logged-in mother's upcoming/completed appointments"""
    res = await db.execute(select(MotherProfile).where(MotherProfile.user_id == current_user.id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found"
        )
        
    query = select(Appointment).where(Appointment.mother_profile_id == profile.id)
    if status_filter:
        query = query.where(Appointment.status == status_filter)
        
    query = query.order_by(Appointment.scheduled_date.asc())
    appointments_res = await db.execute(query)
    return appointments_res.scalars().all()

from fastapi import Request
from app.models.symptom_log import SymptomLog
from app.services.triage_interface import run_triage

@router.post("/sos", status_code=status.HTTP_200_OK)
async def trigger_sos(
    payload: SOSRequest,
    request: Request, # Added Request to access the Socket.IO instance if you have one
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Trigger an emergency SOS alert from the React frontend"""
    
    # 1. Get the mother's profile ID
    result = await db.execute(select(MotherProfile).where(MotherProfile.user_id == current_user.id))
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Mother profile not found. Please complete your profile first."
        )

    # 2. Create a critical, red-alert symptom log
    emergency_log = SymptomLog(
        mother_profile_id=profile.id,
        symptoms="EMERGENCY SOS BUTTON ACTIVATED",
        source="app_sos",
        risk_score="red", # Forces the CHW dashboard to flag this immediately
        triage_notes=payload.note or "Mother triggered the emergency panic button from the dashboard.",
        logged_by_id=current_user.id
    )
    
    db.add(emergency_log)
    await db.commit()
    await db.refresh(emergency_log)

    # 3. Trigger the triage interface (This will eventually fire off your Africa's Talking SMS)
    sio = getattr(request.app.state, "sio", None)
    await run_triage(emergency_log.id, db, sio=sio)

    return {"detail": "SOS alert sent successfully and logged in your medical record."}


@router.post("/book-visit", status_code=status.HTTP_200_OK)
async def book_visit(
    payload: BookVisitRequest,
    db: AsyncSession = Depends(get_db)
    # Note: We omit require_role("mother") here so the Botpress webhook 
    # can successfully POST to this endpoint without an auth token.
):
    """Book a clinic visit or receive a triage alert from Botpress"""
    # Later: Look up the mother by payload.phone_number and notify the CHW
    return {"detail": "Visit booked successfully"}


@router.post("/botpress-webhook", status_code=status.HTTP_200_OK)
async def botpress_symptom_webhook(
    payload: BotpressSymptomPayload,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Webhook for Botpress to log AI-gathered symptoms into the triage system."""
    
    # 1. Look up the mother by the phone number passed from the React webchat
    user_res = await db.execute(select(User).where(User.phone_number == payload.phone_number))
    user = user_res.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No user found with this phone number."
        )
        
    # 2. Get her medical profile
    profile_res = await db.execute(select(MotherProfile).where(MotherProfile.user_id == user.id))
    profile = profile_res.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Mother profile not found."
        )
        
    # 3. Log the symptom into the database
    new_log = SymptomLog(
        mother_profile_id=profile.id,
        symptoms=payload.symptoms,
        source="botpress_ai",
        risk_score=payload.risk_level,
        triage_notes=payload.summary or "Symptoms reported via MamaBot AI chat.",
        logged_by_id=user.id
    )
    
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    
    # 4. Run the triage engine to update the CHW dashboard
    sio = getattr(request.app.state, "sio", None)
    await run_triage(new_log.id, db, sio=sio)
    
    return {"status": "success", "message": "Symptoms logged successfully. CHW notified."}
