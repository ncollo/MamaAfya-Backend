from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.mother_profile import MotherProfile
from app.models.birth_plan import BirthPlan
from app.schemas.birth_plan import BirthPlanCreate, BirthPlanUpdate, BirthPlanResponse
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/birth-plans", tags=["Birth Plans"])

@router.post("/", response_model=BirthPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_birth_plan(
    plan_in: BirthPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Create a digital birth plan for the current logged-in mother"""
    # Fetch profile
    res = await db.execute(select(MotherProfile).where(MotherProfile.user_id == current_user.id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mother profile not found. Create a profile before making a birth plan."
        )

    # Check if plan already exists
    res_plan = await db.execute(select(BirthPlan).where(BirthPlan.mother_profile_id == profile.id))
    if res_plan.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Birth plan already exists. Use PUT to update."
        )

    new_plan = BirthPlan(
        mother_profile_id=profile.id,
        preferred_facility=plan_in.preferred_facility,
        birth_companion_name=plan_in.birth_companion_name,
        birth_companion_phone=plan_in.birth_companion_phone,
        transport_plan=plan_in.transport_plan,
        emergency_contact_name=plan_in.emergency_contact_name,
        emergency_contact_phone=plan_in.emergency_contact_phone,
        preferred_delivery_method=plan_in.preferred_delivery_method,
        special_requests=plan_in.special_requests,
        items_prepared=plan_in.items_prepared or {},
        is_finalized=False
    )
    
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return new_plan

@router.get("/{plan_id}", response_model=BirthPlanResponse)
async def get_birth_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get birth plan by ID (accessible by mother, assigned CHW, or facility staff)"""
    stmt = select(BirthPlan).where(BirthPlan.id == plan_id).options(
        selectinload(BirthPlan.mother_profile).selectinload(MotherProfile.user)
    )
    result = await db.execute(stmt)
    plan = result.scalars().first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Birth plan not found"
        )
        
    # Access checks
    if current_user.role == "mother" and plan.mother_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. This is not your birth plan."
        )
    elif current_user.role == "chw" and plan.mother_profile.user.assigned_chw_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. This mother is not assigned to you."
        )
        
    return plan

@router.put("/{plan_id}", response_model=BirthPlanResponse)
async def update_birth_plan(
    plan_id: int,
    plan_in: BirthPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Update own birth plan (only allowed if not finalized)"""
    stmt = select(BirthPlan).where(BirthPlan.id == plan_id).options(selectinload(BirthPlan.mother_profile))
    result = await db.execute(stmt)
    plan = result.scalars().first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Birth plan not found"
        )
        
    if plan.mother_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own birth plan"
        )
        
    if plan.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a finalized birth plan"
        )
        
    update_data = plan_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
        
    await db.commit()
    await db.refresh(plan)
    return plan

@router.patch("/{plan_id}/finalize", response_model=BirthPlanResponse)
async def finalize_birth_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("mother"))
):
    """Finalize a birth plan to lock edits"""
    stmt = select(BirthPlan).where(BirthPlan.id == plan_id).options(selectinload(BirthPlan.mother_profile))
    result = await db.execute(stmt)
    plan = result.scalars().first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Birth plan not found"
        )
        
    if plan.mother_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only finalize your own birth plan"
        )
        
    plan.is_finalized = True
    await db.commit()
    await db.refresh(plan)
    return plan
