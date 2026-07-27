from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class SymptomLog(Base):
    __tablename__ = "symptom_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mother_profile_id = Column(Integer, ForeignKey("mother_profiles.id"), nullable=False)
    symptoms = Column(JSON, nullable=False) # Stores a list of symptoms e.g., ["Headache", "Swollen Feet"]
    
    # risk_score: 'green', 'yellow', 'red'
    risk_score = Column(String(10), nullable=True)
    
    # source: 'pwa', 'ussd', 'chw_proxy', 'chatbot'
    source = Column(String(20), nullable=False, default="pwa")
    
    triage_notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, server_default=func.now())
    logged_by_id = Column(Integer, ForeignKey("users.id"), nullable=True) # If proxy entered by CHW

    # Relationships
    mother_profile = relationship("MotherProfile", back_populates="symptom_logs")
    logged_by = relationship("User", foreign_keys=[logged_by_id])
