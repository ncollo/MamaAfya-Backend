from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class BirthPlan(Base):
    __tablename__ = "birth_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mother_profile_id = Column(Integer, ForeignKey("mother_profiles.id"), unique=True, nullable=False)
    preferred_facility = Column(String(255), nullable=True)
    birth_companion_name = Column(String(255), nullable=True)
    birth_companion_phone = Column(String(20), nullable=True)
    transport_plan = Column(Text, nullable=True)
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    preferred_delivery_method = Column(String(50), nullable=True)
    special_requests = Column(Text, nullable=True)
    items_prepared = Column(JSON, nullable=True, default=dict)
    is_finalized = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    mother_profile = relationship("MotherProfile", back_populates="birth_plan")
