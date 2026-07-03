from fastapi import APIRouter, Depends, HTTPException, status
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
