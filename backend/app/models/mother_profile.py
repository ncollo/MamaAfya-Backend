from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import relationship
from app.database import Base

class MotherProfile(Base):
    __tablename__ = "mother_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    gestational_age_weeks = Column(Integer, nullable=True)
    expected_delivery_date = Column(Date, nullable=True)
    last_menstrual_period = Column(Date, nullable=True)
    blood_type = Column(String(5), nullable=True)
    medical_history = Column(JSON, nullable=True, default=dict)
    allergies = Column(Text, nullable=True)
    nearest_facility = Column(String(255), nullable=True)
    
    # pregnancy_status: 'antenatal', 'postpartum'
    pregnancy_status = Column(String(20), default="antenatal")
    
    # risk_level: 'green', 'yellow', 'red'
    risk_level = Column(String(10), default="green")
    
    partner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="mother_profile", foreign_keys=[user_id])
    partner = relationship("User", back_populates="partner_profiles", foreign_keys=[partner_user_id])
    
    birth_plan = relationship("BirthPlan", back_populates="mother_profile", uselist=False, cascade="all, delete-orphan")
    symptom_logs = relationship("SymptomLog", back_populates="mother_profile", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="mother_profile", cascade="all, delete-orphan")
