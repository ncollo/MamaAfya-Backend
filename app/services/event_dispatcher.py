import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


logger = logging.getLogger(__name__)

async def notify_chw_dashboard(mother_phone_or_id: str, risk_level: str, symptoms: list):
    """
    BRIDGE FUNCTION: 
    Hands off triage alert data to the Socket.IO server so connected CHW dashboards receive live notifications.
    """
    logger.info(f"SOCKET EMIT TRIGGERED: Alerting dashboard for {mother_phone_or_id} with {risk_level} risk.")
    try:
        from app.main import sio
        from datetime import datetime
        payload = {
            "patient_id": str(mother_phone_or_id),
            "risk_level": str(risk_level),
            "symptoms": symptoms,
            "timestamp": datetime.now().isoformat(),
            "alert_type": "high_risk_alert" if str(risk_level).lower() in ["red", "high", "high risk"] else "routine_update"
        }
        # Broadcast to all connected CHWs and to any specific rooms
        await sio.emit("notify_chw_dashboard", payload)
        await sio.emit("patient_update", payload)
        if str(risk_level).lower() in ["red", "high", "high risk"]:
            await sio.emit("new_alert", payload)
    except Exception as e:
        logger.error(f"Failed to emit WebSocket alert in notify_chw_dashboard: {e}")
    return True

async def fetch_patient_context(phone_number: str, db: AsyncSession) -> dict:
    """
    Queries the live database for the mother's profile using her phone number.
    Joins the users and mother_profiles tables, and does a self-join to fetch the CHW's phone number.
    """
    query = text("""
        SELECT 
            mp.id AS mother_profile_id, 
            u.full_name, 
            mp.pregnancy_status, 
            chw.phone_number AS chw_phone 
        FROM users u
        JOIN mother_profiles mp ON u.id = mp.user_id
        LEFT JOIN users chw ON u.assigned_chw_id = chw.id
        WHERE u.phone_number = :phone_number 
        LIMIT 1
    """)
    
    result = await db.execute(query, {"phone_number": phone_number})
    row = result.fetchone()
    
    if row:
        # 1. Extract just the first name for the USSD greeting
        first_name = row.full_name.split(" ")[0] if row.full_name else "Mama"
        
        # 2. Map Nelson's "postpartum" database value to our USSD "postnatal" menu key
        phase = "postnatal" if row.pregnancy_status == "postpartum" else "antenatal"
        
        return {
            "id": row.mother_profile_id,
            "first_name": first_name,
            "phase": phase,
            "assigned_chw_phone": row.chw_phone or "+254700000000"
        }
    
    # Fallback if the number dialing is not registered in the system yet
    return {
        "id": None, 
        "first_name": "Mama", 
        "phase": "antenatal", 
        "assigned_chw_phone": "+254700000000"
    }