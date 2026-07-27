from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    
    # Roles: 'mother', 'chw', 'facility_staff', 'partner'
    role = Column(String(20), nullable=False, default="mother")
    
    location = Column(String(500), nullable=True)
    assigned_chw_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    assigned_chw = relationship("User", remote_side=[id], backref="assigned_patients")
    mother_profile = relationship("MotherProfile", back_populates="user", uselist=False, foreign_keys="[MotherProfile.user_id]")
    partner_profiles = relationship("MotherProfile", back_populates="partner", foreign_keys="[MotherProfile.partner_user_id]")
