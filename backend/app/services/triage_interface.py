from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
import logging
from typing import List, Optional

from app.models.symptom_log import SymptomLog
from app.models.mother_profile import MotherProfile

logger = logging.getLogger(__name__)

def calculate_risk_level(symptoms: List[str], gestational_age_weeks: Optional[int]) -> str:
    """
    Clinical Triage Algorithm placeholder. Collins will implement his code here.
    
    Collins: Check the symptoms (e.g. ['Severe headache', 'Swollen feet', 'Bleeding'])
    against the gestational_age_weeks.
    
    Risk classifications:
    - 'green': Normal / low risk
    - 'yellow': Moderate risk / needs CHW visit
    - 'red': High risk / emergency triage
    """
    if not symptoms:
        return "green"
        
    symptoms_lower = [s.lower() for s in symptoms]
    
    # High-risk symptoms (Red)
    red_flags = [
        "bleeding", "vaginal bleeding", "severe headache", "blurred vision", 
        "convulsions", "fits", "difficulty breathing", "severe abdominal pain",
        "fever", "high fever", "reduced baby movement", "no baby movement"
    ]
    
    # Moderate-risk symptoms (Yellow)
    yellow_flags = [
        "swollen feet", "swollen hands", "mild headache", "nausea", 
        "vomiting", "dizziness", "constipation", "heartburn"
    ]
    
    for symptom in symptoms_lower:
        if any(flag in symptom for flag in red_flags):
            return "red"
            
    for symptom in symptoms_lower:
        if any(flag in symptom for flag in yellow_flags):
            return "yellow"
            
    # Fallback clinical logic: 3+ mild symptoms trigger medium risk
    if len(symptoms) >= 3:
        return "yellow"
        
    return "green"

async def run_triage(symptom_log_id: int, db: AsyncSession, sio = None) -> str:
    """
    Triage execution pipeline.
    1. Fetches the logged symptoms
    2. Runs calculate_risk_level
    3. Persists risk_score on the log and risk_level on the mother's profile
    4. Triggers Socket.IO dashboard alerts for CHW
    """
    stmt = select(SymptomLog).where(SymptomLog.id == symptom_log_id).options(
        selectinload(SymptomLog.mother_profile).selectinload(MotherProfile.user)
    )
    res = await db.execute(stmt)
    log = res.scalars().first()
    
    if not log:
        logger.error(f"Symptom log {symptom_log_id} not found in database during triage")
        return "green"
        
    mother_profile = log.mother_profile
    risk = calculate_risk_level(log.symptoms, mother_profile.gestational_age_weeks)
    
    # Update log & profile risk
    log.risk_score = risk
    mother_profile.risk_level = risk
    
    await db.commit()
    logger.info(f"Triage completed for mother profile {mother_profile.id}: Risk evaluated as {risk}")
    
    # Emit real-time updates via Socket.IO if mounted
    if sio:
        try:
            chw_id = mother_profile.user.assigned_chw_id
            if chw_id:
                # Notify CHW
                payload = {
                    "patient_id": mother_profile.id,
                    "patient_name": mother_profile.user.full_name,
                    "risk_level": risk,
                    "symptoms": log.symptoms,
                    "timestamp": log.logged_at.isoformat() if log.logged_at else func.now()
                }
                
                await sio.emit("patient_update", payload, room=f"chw_{chw_id}")
                
                # If high risk, push to critical alerts channel too
                if risk == "red":
                    alert_payload = {
                        "alert_type": "symptom_escalation",
                        "patient_id": mother_profile.id,
                        "patient_name": mother_profile.user.full_name,
                        "risk_level": "red",
                        "symptoms": log.symptoms,
                        "message": f"🚨 CRITICAL ALERT: {mother_profile.user.full_name} reported danger signs: {', '.join(log.symptoms)}.",
                        "timestamp": log.logged_at.isoformat() if log.logged_at else func.now()
                    }
                    await sio.emit("new_alert", alert_payload, room=f"chw_{chw_id}")
        except Exception as e:
            logger.error(f"Failed to emit Socket.IO notification: {str(e)}")
            
    return risk
