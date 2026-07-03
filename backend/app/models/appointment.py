from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mother_profile_id = Column(Integer, ForeignKey("mother_profiles.id"), nullable=False)
    appointment_type = Column(String(100), nullable=False) # e.g., 'ANC Visit', 'Tetanus Vaccine'
    scheduled_date = Column(DateTime, nullable=False)
    
    # status: 'upcoming', 'completed', 'missed', 'cancelled'
    status = Column(String(20), default="upcoming")
    
    facility_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    mother_profile = relationship("MotherProfile", back_populates="appointments")
