import asyncio
from datetime import date, datetime, timedelta
from sqlalchemy.future import select
from app.database import engine, Base, AsyncSessionLocal
from app.models.user import User
from app.models.mother_profile import MotherProfile
from app.models.birth_plan import BirthPlan
from app.models.symptom_log import SymptomLog
from app.models.appointment import Appointment
from app.services.auth_service import hash_password

async def seed():
    print("Creating tables in PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

    async with AsyncSessionLocal() as db:
        print("Seeding users...")
        pwd = hash_password("password123")

        # 1. CHW
        chw = User(
            email="chw@mamaafya.org",
            phone_number="+254711000001",
            password_hash=pwd,
            full_name="Jane Mutua",
            role="chw",
            location="Mathare Ward 4, Nairobi",
            is_active=True
        )
        db.add(chw)
        await db.flush()

        # 2. Facility Staff
        staff = User(
            email="clinic@mamaafya.org",
            phone_number="+254711000002",
            password_hash=pwd,
            full_name="Dr. Omondi",
            role="facility_staff",
            location="Mathare Sub-County Hospital",
            is_active=True
        )
        db.add(staff)

        # 3. Partner
        partner = User(
            email="partner@mamaafya.org",
            phone_number="+254700000003",
            password_hash=pwd,
            full_name="John Wanjiru",
            role="partner",
            location="Mathare, Nairobi",
            is_active=True
        )
        db.add(partner)
        await db.flush()

        # 4. Mother 1: Amina Wanjiru (High Risk, Antenatal)
        mother1 = User(
            email="amina@mamaafya.org",
            phone_number="+254700000001",
            password_hash=pwd,
            full_name="Amina Wanjiru",
            role="mother",
            location="Mathare, Nairobi",
            assigned_chw_id=chw.id,
            is_active=True
        )
        db.add(mother1)
        await db.flush()

        prof1 = MotherProfile(
            user_id=mother1.id,
            gestational_age_weeks=32,
            expected_delivery_date=date.today() + timedelta(weeks=8),
            last_menstrual_period=date.today() - timedelta(weeks=32),
            blood_type="O+",
            pregnancy_status="antenatal",
            risk_level="red",
            partner_user_id=partner.id,
            nearest_facility="Mathare Sub-County Hospital",
            allergies="Penicillin",
            medical_history={"gravida": 2, "para": 1, "previous_c_section": False}
        )
        db.add(prof1)
        await db.flush()

        # Symptoms for Amina (Danger signs: Red)
        symp1 = SymptomLog(
            mother_profile_id=prof1.id,
            symptoms=["severe_headache", "blurred_vision"],
            risk_score="red",
            source="pwa",
            triage_notes="Mother reported severe headache with blurred vision via PWA.",
            logged_at=datetime.utcnow() - timedelta(minutes=25)
        )
        db.add(symp1)

        # Birth plan for Amina
        bp1 = BirthPlan(
            mother_profile_id=prof1.id,
            preferred_facility="Mathare Sub-County Hospital",
            birth_companion_name="John Wanjiru",
            birth_companion_phone="+254700000003",
            transport_plan="Boda Boda voucher & Local Emergency Taxi (Driver Ouma: +254722998877)",
            emergency_contact_name="John Wanjiru",
            emergency_contact_phone="+254700000003",
            preferred_delivery_method="Spontaneous Vaginal Delivery (SVD)",
            special_requests="Partner presence in delivery room, delayed cord clamping.",
            items_prepared={"basin": True, "cotton_wool": True, "baby_clothes": True, "maternity_pads": True},
            is_finalized=False
        )
        db.add(bp1)

        # Appointment for Amina
        apt1 = Appointment(
            mother_profile_id=prof1.id,
            facility_name="Mathare Sub-County Hospital",
            appointment_type="ANC Visit 4 (Ultrasound & BP Check)",
            scheduled_date=datetime.utcnow() + timedelta(days=3, hours=2),
            status="scheduled",
            notes="Follow-up on high blood pressure and headache."
        )
        db.add(apt1)

        # 5. Mother 2: Beatrice Atieno (Medium Risk / Monitor)
        mother2 = User(
            email="beatrice@mamaafya.org",
            phone_number="+254700000002",
            password_hash=pwd,
            full_name="Beatrice Atieno",
            role="mother",
            location="Huruma, Nairobi",
            assigned_chw_id=chw.id,
            is_active=True
        )
        db.add(mother2)
        await db.flush()

        prof2 = MotherProfile(
            user_id=mother2.id,
            gestational_age_weeks=24,
            expected_delivery_date=date.today() + timedelta(weeks=16),
            last_menstrual_period=date.today() - timedelta(weeks=24),
            blood_type="A+",
            pregnancy_status="antenatal",
            risk_level="yellow",
            nearest_facility="Pumwani Maternity Hospital",
            medical_history={"gravida": 1, "para": 0}
        )
        db.add(prof2)
        await db.flush()

        symp2 = SymptomLog(
            mother_profile_id=prof2.id,
            symptoms=["swollen_feet", "mild_headache"],
            risk_score="yellow",
            source="pwa",
            triage_notes="Mild swelling in ankles and slight fatigue.",
            logged_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.add(symp2)

        # 6. Mother 3: Faith Cherono (Postpartum / Routine)
        mother3 = User(
            email="faith@mamaafya.org",
            phone_number="+254700000004",
            password_hash=pwd,
            full_name="Faith Cherono",
            role="mother",
            location="Mathare Area 3",
            assigned_chw_id=chw.id,
            is_active=True
        )
        db.add(mother3)
        await db.flush()

        prof3 = MotherProfile(
            user_id=mother3.id,
            gestational_age_weeks=None,
            delivery_date=date.today() - timedelta(days=14),
            is_postnatal=True,
            pregnancy_status="postpartum",
            risk_level="green",
            nearest_facility="Mathare Health Centre",
            blood_type="B+",
            medical_history={"delivery": "Normal delivery, healthy boy 3.2kg", "immunization_bcg": True}
        )
        db.add(prof3)
        await db.flush()

        symp3 = SymptomLog(
            mother_profile_id=prof3.id,
            symptoms=["routine_check"],
            risk_score="green",
            source="chw_proxy",
            triage_notes="Home visit: Baby latching well, mother recovering well without fever.",
            logged_by_id=chw.id,
            logged_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(symp3)

        apt3 = Appointment(
            mother_profile_id=prof3.id,
            facility_name="Mathare Health Centre",
            appointment_type="6-Week Postnatal & Baby Immunization",
            scheduled_date=datetime.utcnow() + timedelta(days=28),
            status="scheduled",
            notes="Penta 1, OPV 1, PCV 1 vaccinations scheduled."
        )
        db.add(apt3)

        # 7. Mother 4: Grace Nyambura (Routine / Antenatal)
        mother4 = User(
            email="grace@mamaafya.org",
            phone_number="+254700000005",
            password_hash=pwd,
            full_name="Grace Nyambura",
            role="mother",
            location="Mathare Ward 4",
            assigned_chw_id=chw.id,
            is_active=True
        )
        db.add(mother4)
        await db.flush()

        prof4 = MotherProfile(
            user_id=mother4.id,
            gestational_age_weeks=16,
            expected_delivery_date=date.today() + timedelta(weeks=24),
            last_menstrual_period=date.today() - timedelta(weeks=16),
            blood_type="O-",
            pregnancy_status="antenatal",
            risk_level="green",
            nearest_facility="Mathare Health Centre"
        )
        db.add(prof4)
        await db.flush()

        await db.commit()
        print("Database seeded successfully with all 4 doors test data!")

if __name__ == "__main__":
    asyncio.run(seed())
