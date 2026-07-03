# MamaAfya Maternal Health API Backend

The centralized backend Maternal Health Information System (MHIS) for the MamaAfya platform in Kenya. It handles user management, expectant mother profiles, clinical birth plans, appointment reminders, and live risk-level triage alerting.

## Technology Stack
- **Framework**: FastAPI (Asynchronous Python REST API)
- **Real-Time Communication**: Socket.IO (over ASGI)
- **Database**: Supabase PostgreSQL via `asyncpg` (SQLite remains available as a local fallback)
- **ORM & Sessions**: SQLAlchemy 2.0 (AsyncIO)
- **Authentication**: OAuth2 password flow with JWT (JSON Web Tokens)

---

## Workspace Setup & Execution

### Prerequisites
- Python 3.10+ installed on your machine.
- A Supabase project with a PostgreSQL connection string.

### Installation Instructions

1. **Navigate to the Backend Directory**:
   ```bash
   cd backend
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   
   # Windows Command Prompt
   python -m venv venv
   .\venv\Scripts\activate.bat
   
   # macOS / Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Copy the `.env.example` file to `.env`:
   ```bash
   copy .env.example .env
   ```
   Open `.env` and set `DATABASE_URL` to the Supabase Session Pooler URI using SQLAlchemy's async driver format:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres.project-ref:your-password@aws-0-region.pooler.supabase.com:5432/postgres
   ```

   Keep `.env` private because it contains your real database password.

5. **Run the Development Server**:
   ```bash
   uvicorn app.main:combined_asgi_app --reload
   ```

   On startup, the app initializes the required database tables if they are missing.

6. **Interactive Documentation**:
   Once the server starts, open your browser and navigate to:
   [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI) to interact with and test all the endpoints.

---

## Integration Guide for Collins (Triage Engine)

Collins, the clinical triage system is integrated directly into Nelson's patient management system.

The code entry point is located in [triage_interface.py](file:///c:/Users/nelso/OneDrive/Desktop/MAMA%20AFYA%20mobile%20responsive/backend/app/services/triage_interface.py).

### How to Implement
1. Open [triage_interface.py](file:///c:/Users/nelso/OneDrive/Desktop/MAMA%20AFYA%20mobile%20responsive/backend/app/services/triage_interface.py).
2. Locate the function `calculate_risk_level(symptoms: list[str], gestational_age_weeks: int | None) -> str`.
3. Replace the placeholder rules with the clinical triage calculations:
   - Perform safety overrides (e.g., check for vaginal bleeding, convulsions, blurred vision, severe headache).
   - Evaluate symptoms against the pregnancy trimester/gestational week.
   - Return one of the string statuses: `"green"`, `"yellow"`, or `"red"`.
4. The caller function `run_triage` will automatically persist your evaluated risk on the database records, update the mother's dashboard status, and dispatch real-time dashboard events (`patient_update` and `new_alert` rooms) over Socket.IO.
