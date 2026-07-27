from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from fastapi import APIRouter, Form, Response
from typing import Optional
from app.services.triage_interface import run_triage
from app.services.sms_service import dispatch_emergency_sms
from app.services.event_dispatcher import fetch_patient_context

router = APIRouter()

# The Dictionary Router: Defines menus based on the patient's medical phase
MENUS = {
    "antenatal": {
        "title": "CON Karibu MamaAfya (Mjamzito)\nJe, una shida gani?\n",
        "options": {
            "1": {"text": "Kichwa/Macho (Head/Vision)", "symptom": "severe_headache"},
            "2": {"text": "Kutoka damu/Maji (Bleeding/Fluid)", "symptom": "heavy_bleeding"},
            "3": {"text": "Mtoto hachezi (Baby movement)", "symptom": "reduced_fetal_movement"},
            "4": {"text": "Kifafa/Kuzimia (Seizures)", "symptom": "seizures"},
            "5": {"text": "Nyingine (Other/Call me)", "symptom": "other_escalate"}
        }
    },
    "postnatal": {
        "title": "CON Karibu MamaAfya (Mzazi)\nJe, una shida gani?\n",
        "options": {
            "1": {"text": "Kutoka damu nyingi (Heavy bleeding)", "symptom": "postpartum_hemorrhage"},
            "2": {"text": "Maziwa kuuma sana (Breast pain)", "symptom": "mastitis"},
            "3": {"text": "Mtoto hanyonyi/Homa (Sick baby)", "symptom": "neonatal_lethargy"},
            "4": {"text": "Kidonda kutoa usaha (Infection)", "symptom": "foul_discharge"},
            "5": {"text": "Nyingine (Other/Call me)", "symptom": "other_escalate"}
        }
    }
}

@router.post("/callback")
async def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""), 
    db: AsyncSession = Depends(get_db),
    networkCode: Optional[str] = Form(None)
):
    user_path = text.split("*") if text else []
    level = len(user_path)
    response = ""

    # Fetch context: Tells us if she is antenatal or postnatal, and gets her CHW
    context = await fetch_patient_context(phoneNumber)
    phase = context.get("phase", "antenatal")
    chw_phone = context.get("assigned_chw_phone", "+254700000000")
    
    active_menu = MENUS[phase]

    # LEVEL 0: Main Menu
    if level == 0 or text == "":
        response = (
            f"CON Karibu MamaAfya, {context.get('first_name', 'Mama')}.\n"
            "1. Ripoti Dalili (Report Symptoms)\n"
            "2. Msaada wa Dharura (Emergency Alert)"
        )

    # LEVEL 1: Symptom Reporting or Emergency
    elif level == 1:
        if user_path[0] == "1":
            # Dynamically generate the symptom list based on her phase
            response = active_menu["title"]
            for key, value in active_menu["options"].items():
                response += f"{key}. {value['text']}\n"
                
        elif user_path[0] == "2":
            # Direct Emergency
            alert_msg = f"EMERGENCY: {context.get('first_name')} ({phoneNumber}) requested immediate help."
            await dispatch_emergency_sms(chw_phone, alert_msg)
            
            # Send the emergency trigger through the unified engine
            await run_triage(context.get("id"), db, ["emergency_button"])
            
            response = "END Tumeitisha msaada. Mhudumu wako anakuja."
        else:
            response = "END Chaguo sio sahihi."

    # LEVEL 2: Processing the chosen symptom
    elif level == 2 and user_path[0] == "1":
        selected_option = user_path[1]
        options = active_menu["options"]
        
        if selected_option in options:
            symptom_key = options[selected_option]["symptom"]
            
            if symptom_key == "other_escalate":
                # Handle the "Other" option
                alert_msg = f"CALLBACK REQUIRED: {context.get('first_name')} ({phoneNumber}) reported an unlisted symptom. Please call them."
                await dispatch_emergency_sms(chw_phone, alert_msg)
                
                # Send the unlisted symptom through the unified engine
                await run_triage(context.get("id"), db, ["unlisted_symptom"])
                
                response = "END Tumemjulisha mhudumu. Atakupigia simu hivi punde."
                
            else:
                # Run it through the engine
                risk_status = await run_triage(
                    context.get("id"),
                    db, 
                    [symptom_key]
                )
                
                # Check the risk status returned by Nelson's engine
                if risk_status == "red":
                    alert_msg = f"URGENT: {context.get('first_name', 'Mama')} ({phoneNumber}) reported HIGH RISK: {options[selected_option]['text']}."
                    await dispatch_emergency_sms(chw_phone, alert_msg)
                    response = "END Hii ni dalili ya hatari. Tumemjulisha mhudumu mara moja."
                    
                elif risk_status == "yellow":
                    response = "END Dalili imerekodiwa. Tafadhali nenda kituo cha afya kilicho karibu."
                    
                else:
                    response = "END Dalili imerekodiwa. Endelea kufuatilia afya yako."
        else:
            response = "END Chaguo sio sahihi."
            
    else:
        response = "END Hitilafu imetokea."

    return Response(content=response, media_type="text/plain")