from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, Token, UserResponse
from app.services import auth_service
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user (mother, CHW, partner, or facility staff)"""
    # Check if user already exists
    if user_in.email:
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already registered"
            )
            
    if user_in.phone_number:
        result = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number already registered"
            )

    password_hash = auth_service.hash_password(user_in.password)
    
    new_user = User(
        email=user_in.email,
        phone_number=user_in.phone_number,
        password_hash=password_hash,
        full_name=user_in.full_name,
        role=user_in.role,
        location=user_in.location,
        assigned_chw_id=user_in.assigned_chw_id,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticate via email or phone number and return JWT tokens"""
    # Search by email first, then phone number
    result = await db.execute(
        select(User).where(
            (User.email == form_data.username) | (User.phone_number == form_data.username)
        )
    )
    user = result.scalars().first()
    
    if not user or not auth_service.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username (email/phone) or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
        
    # Generate tokens
    user_data = {"sub": str(user.id), "role": user.role}
    access_token = auth_service.create_access_token(user_data)
    refresh_token = auth_service.create_refresh_token(user_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Get a new access token using a refresh token"""
    payload = auth_service.decode_token(refresh_token)
    token_type = payload.get("type")
    user_id_str = payload.get("sub")
    
    if not user_id_str or token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
        
    user_id = int(user_id_str)
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
        
    user_data = {"sub": str(user.id), "role": user.role}
    access_token = auth_service.create_access_token(user_data)
    new_refresh_token = auth_service.create_refresh_token(user_data)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user info"""
    return current_user
