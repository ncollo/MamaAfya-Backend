from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.triage_engine import calculate_risk, SymptomReport
from app.services.sms_service import dispatch_emergency_sms
from app.services.event_dispatcher import notify_chw_dashboard, fetch_patient_context

router = APIRouter()

class PwaSymptomPayload(BaseModel):
    mother_id: str
    gestational_week: int
    symptoms: List[str]

class PwaTriageResponse(BaseModel):
    risk_level: str
    action_required: str
    message: str

@router.post("/submit-symptoms", response_model=PwaTriageResponse)
async def submit_pwa_symptoms(payload: PwaSymptomPayload):
    report = SymptomReport(
        symptoms=payload.symptoms,
        gestational_week=payload.gestational_week
    )
    
    risk = calculate_risk(report)
    
    if risk.value == "High Risk":
        action = "DISPATCH_CHW"
        msg = "We have detected a danger sign. Your Community Health Worker has been notified immediately."
        
        # 1. Get the CHW's phone number from the DB bridge
        patient_context = await fetch_patient_context(payload.mother_id)
        chw_phone = patient_context["assigned_chw_phone"]
        
        # 2. Fire the SMS
        alert_msg = f"URGENT: Mother ID {payload.mother_id} triggered a HIGH RISK alert via the Web App. Please check your dashboard."
        await dispatch_emergency_sms(chw_phone, alert_msg)
        
        # Notify the CHW dashboard
        await notify_chw_dashboard(payload.mother_id, risk.value, payload.symptoms)
        
    else:
        action = "ROUTINE_LOG"
        msg = "Symptoms logged successfully. Please monitor your condition."
        
    return PwaTriageResponse(
        risk_level=risk.value, 
        action_required=action, 
        message=msg
    )