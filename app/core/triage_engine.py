from enum import Enum
from pydantic import BaseModel
from typing import List

class RiskLevel(str, Enum):
    RED = "High Risk"
    YELLOW = "Medium Risk"
    GREEN = "Routine"

class SymptomReport(BaseModel):
    symptoms: List[str]
    gestational_week: int
    phase: str = "antenatal" # Added phase tracking

def calculate_risk(report: SymptomReport) -> RiskLevel:
    # 1. Antenatal Danger Signs
    antenatal_danger = [
        "severe_headache", "blurred_vision", "heavy_bleeding", 
        "water_breaking_early", "reduced_fetal_movement", "seizures"
    ]
    
    # 2. Postnatal (Maternal & Neonatal) Danger Signs
    postnatal_danger = [
        "postpartum_hemorrhage", "foul_discharge", "mastitis", 
        "neonatal_lethargy", "cord_infection", "neonatal_fever"
    ]
    
    warning_signs = ["mild_fever", "swollen_feet", "persistent_nausea", "mild_pain"]

    # Combine danger signs for the check
    all_danger_signs = antenatal_danger + postnatal_danger

    for symptom in report.symptoms:
        if symptom in all_danger_signs:
            return RiskLevel.RED
            
    # Context check: Swollen feet late in pregnancy
    if "swollen_feet" in report.symptoms and report.phase == "antenatal" and report.gestational_week > 30:
        return RiskLevel.YELLOW

    for symptom in report.symptoms:
        if symptom in warning_signs:
            return RiskLevel.YELLOW

    return RiskLevel.GREEN