from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.mother_profile import MotherProfile
from app.models.symptom_log import SymptomLog
from app.schemas.mother_profile import MotherProfileResponse
from app.schemas.symptom_log import SymptomLogProxy, SymptomLogResponse
from app.middleware.auth import require_role
from app.services.triage_interface import run_triage

router = APIRouter(prefix="/api/chw", tags=["CHW Dashboard"])

@router.get("/patients", response_model=List[MotherProfileResponse])
async def get_assigned_patients(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw"))
):
    """Retrieve all patients assigned to this CHW, sorted by risk level (red, yellow, green)"""
    stmt = (
        select(MotherProfile)
        .join(User, MotherProfile.user_id == User.id)
        .where(User.assigned_chw_id == current_user.id, User.is_active == True)
        .options(selectinload(MotherProfile.user))
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()
    
    # Sorting logic: red -> yellow -> green
    def sort_key(p):
        order = {"red": 0, "yellow": 1, "green": 2}
        return order.get(p.risk_level, 3)
        
    return sorted(profiles, key=sort_key)

@router.post("/patients/{profile_id}/proxy-entry", response_model=SymptomLogResponse)
async def proxy_data_entry(
    profile_id: int,
    log_in: SymptomLogProxy,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw"))
):
    """Log symptoms on behalf of a mother (e.g. during home visits or phone calls)"""
    stmt = select(MotherProfile).where(MotherProfile.id == profile_id).options(selectinload(MotherProfile.user))
    res = await db.execute(stmt)
    profile = res.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found"
        )
        
    if profile.user.assigned_chw_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. This mother is not assigned to you."
        )
        
    new_log = SymptomLog(
        mother_profile_id=profile.id,
        symptoms=log_in.symptoms,
        source="chw_proxy",
        triage_notes=log_in.triage_notes,
        logged_by_id=current_user.id
    )
    
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    
    # Run triage and emit Socket.IO notification (fetch sio from app state if exists)
    sio = getattr(request.app.state, "sio", None)
    await run_triage(new_log.id, db, sio=sio)
    
    # Refresh to return populated relations
    stmt_log = select(SymptomLog).where(SymptomLog.id == new_log.id).options(
        selectinload(SymptomLog.logged_by)
    )
    res_log = await db.execute(stmt_log)
    return res_log.scalars().first()

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw"))
):
    """Retrieve statistics for the CHW's dashboard overview"""
    # Total assigned patients
    patients_stmt = (
        select(MotherProfile)
        .join(User, MotherProfile.user_id == User.id)
        .where(User.assigned_chw_id == current_user.id, User.is_active == True)
    )
    patients_res = await db.execute(patients_stmt)
    patients = patients_res.scalars().all()
    
    total = len(patients)
    red = sum(1 for p in patients if p.risk_level == "red")
    yellow = sum(1 for p in patients if p.risk_level == "yellow")
    green = sum(1 for p in patients if p.risk_level == "green")
    
    # Recent alerts: high risk reports in last 24h
    cutoff = datetime.now() - timedelta(hours=24)
    alerts_stmt = (
        select(SymptomLog)
        .join(MotherProfile)
        .join(User, MotherProfile.user_id == User.id)
        .where(User.assigned_chw_id == current_user.id, SymptomLog.risk_score == "red", SymptomLog.logged_at >= cutoff)
        .options(selectinload(SymptomLog.mother_profile).selectinload(MotherProfile.user))
    )
    alerts_res = await db.execute(alerts_stmt)
    alerts = alerts_res.scalars().all()
    
    recent_alerts = [
        {
            "id": a.id,
            "patient_name": a.mother_profile.user.full_name,
            "symptoms": a.symptoms,
            "logged_at": a.logged_at
        }
        for a in alerts
    ]
    
    return {
        "total_patients": total,
        "high_risk_count": red,
        "medium_risk_count": yellow,
        "low_risk_count": green,
        "recent_alerts": recent_alerts
    }

@router.get("/alerts")
async def get_all_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chw"))
):
    """Get all alerts (high-risk reports) in the last 7 days for assigned patients"""
    cutoff = datetime.now() - timedelta(days=7)
    stmt = (
        select(SymptomLog)
        .join(MotherProfile)
        .join(User, MotherProfile.user_id == User.id)
        .where(User.assigned_chw_id == current_user.id, SymptomLog.risk_score == "red", SymptomLog.logged_at >= cutoff)
        .options(selectinload(SymptomLog.mother_profile).selectinload(MotherProfile.user))
        .order_by(SymptomLog.logged_at.desc())
    )
    res = await db.execute(stmt)
    logs = res.scalars().all()
    
    return [
        {
            "id": l.id,
            "patient_id": l.mother_profile_id,
            "patient_name": l.mother_profile.user.full_name,
            "symptoms": l.symptoms,
            "triage_notes": l.triage_notes,
            "logged_at": l.logged_at
        }
        for l in logs
    ]
