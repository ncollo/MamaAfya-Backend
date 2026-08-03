import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.symptom_log import SymptomLog
from app.services.event_dispatcher import fetch_patient_context
from app.services.triage_interface import run_triage
from app.services.sms_service import dispatch_emergency_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot Webhook"])

BOTPRESS_SECRET = "MamaBot-Secure-Key-2026"


class BotpressSymptomPayload(BaseModel):
    phone_number: str = Field(..., example="+254797185616")
    symptoms: List[str] = Field(..., example=["heavy_bleeding"])
    notes: Optional[str] = Field(None, example="Reported via MamaBot web app")


@router.post("/webhook")
async def botpress_symptom_webhook(
    payload: BotpressSymptomPayload,
    db: AsyncSession = Depends(get_db),
    x_botpress_secret_token: Optional[str] = Header(None)
):
    """
    Webhook bridge between Botpress Community Chatbot & MamaAfya Triage Engine.
    Processes symptoms captured via conversation, records logs with source='chatbot',
    and triggers emergency alerts if risk is elevated.
    """
    # 1. Security Check: Validate Secret Header Token
    if x_botpress_secret_token != BOTPRESS_SECRET:
        logger.warning("Unauthorized chatbot webhook attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing secret token"
        )

    logger.info(f"MamaBot Webhook received for phone: {payload.phone_number} with symptoms: {payload.symptoms}")

    # 2. Look up mother & assigned CHW context from database
    context = await fetch_patient_context(payload.phone_number, db)
    mother_id = context.get("id")

    if not mother_id:
        logger.warning(f"MamaBot triage attempt failed: No registered mother for {payload.phone_number}")
        return {
            "status": "error",
            "bot_reply": "Samahani, nambari hii haijasajiliwa kwenye mfumo wa MamaAfya. Tafadhali jisajili kwanza au uwasiliane na mhudumu wako wa afya.",
            "risk_level": "unknown",
            "chw_notified": False
        }

    # 3. Persist the symptom log into symptom_logs table
    new_log = SymptomLog(
        mother_profile_id=mother_id,
        symptoms=payload.symptoms,
        source="chatbot",
        triage_notes=payload.notes or "Logged via MamaBot Webchat"
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)

    # 4. Execute the unified triage algorithm
    risk_level = await run_triage(new_log.id, db)

    # 5. Handle emergency escalation if RED risk
    chw_phone = context.get("assigned_chw_phone", "+254700000000")
    first_name = context.get("first_name", "Mama")
    chw_notified = False

    if risk_level == "red":
        symptom_str = ", ".join(payload.symptoms)
        alert_msg = f"EMERGENCY (MamaBot): {first_name} ({payload.phone_number}) reported DANGER SIGNS: {symptom_str}."
        
        await dispatch_emergency_sms(chw_phone, alert_msg)
        chw_notified = True

        bot_reply = (
            f"Pole sana {first_name}. Hizi ni dalili za hatari. "
            f"Tumemjulisha mhudumu wako wa afya ({chw_phone}) mara moja na anakupigia simu hivi punde."
        )

    elif risk_level == "yellow":
        bot_reply = (
            f"Asante {first_name}. Dalili zako zimekodiwa. "
            f"Hali hii inahitaji uchunguzi, tafadhali tembelea kituo cha afya kilicho karibu au uwasiliane na CHW wako."
        )

    else:  # green
        bot_reply = (
            f"Asante {first_name}. Dalili zako zimekodiwa kikamilifu. "
            f"Endelea kufuatilia afya yako na unywe maji ya kutosha."
        )

    return {
        "status": "success",
        "symptom_log_id": new_log.id,
        "risk_level": risk_level,
        "bot_reply": bot_reply,
        "chw_notified": chw_notified
    }