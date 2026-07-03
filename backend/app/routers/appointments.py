from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.mother_profile import MotherProfile
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appt_in: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw", "facility_staff"))
):
    """Create a new clinical appointment for a mother"""
    # Fetch profile to verify existence
    res = await db.execute(select(MotherProfile).where(MotherProfile.id == appt_in.mother_profile_id))
    profile = res.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found"
        )
        
    new_appt = Appointment(
        mother_profile_id=appt_in.mother_profile_id,
        appointment_type=appt_in.appointment_type,
        scheduled_date=appt_in.scheduled_date,
        facility_name=appt_in.facility_name,
        notes=appt_in.notes,
        status="upcoming"
    )
    
    db.add(new_appt)
    await db.commit()
    await db.refresh(new_appt)
    return new_appt

@router.get("/upcoming", response_model=List[AppointmentResponse])
async def get_upcoming_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get upcoming appointments. If CHW, returns upcoming appointments for all assigned patients."""
    if current_user.role == "chw":
        stmt = (
            select(Appointment)
            .join(MotherProfile)
            .join(User, MotherProfile.user_id == User.id)
            .where(User.assigned_chw_id == current_user.id, Appointment.status == "upcoming")
            .order_by(Appointment.scheduled_date.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    if current_user.role == "mother":
        stmt = (
            select(Appointment)
            .join(MotherProfile)
            .where(MotherProfile.user_id == current_user.id, Appointment.status == "upcoming")
            .order_by(Appointment.scheduled_date.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only mothers and CHWs can view their upcoming schedules here"
    )

@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific appointment"""
    stmt = select(Appointment).where(Appointment.id == appointment_id).options(
        selectinload(Appointment.mother_profile).selectinload(MotherProfile.user)
    )
    res = await db.execute(stmt)
    appt = res.scalars().first()
    
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
        
    # Check permissions
    if current_user.role == "mother" and appt.mother_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. This is not your appointment."
        )
    elif current_user.role == "chw" and appt.mother_profile.user.assigned_chw_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. This patient is not assigned to you."
        )
        
    return appt

@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    appt_in: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw", "facility_staff"))
):
    """Update details of an appointment"""
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    res = await db.execute(stmt)
    appt = res.scalars().first()
    
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
        
    update_data = appt_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appt, field, value)
        
    await db.commit()
    await db.refresh(appt)
    return appt

@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: int,
    new_status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw", "facility_staff"))
):
    """Transition appointment status (e.g. marked as completed or missed)"""
    if new_status not in ["upcoming", "completed", "missed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status transition"
        )
        
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    res = await db.execute(stmt)
    appt = res.scalars().first()
    
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
        
    appt.status = new_status
    await db.commit()
    await db.refresh(appt)
    return appt
