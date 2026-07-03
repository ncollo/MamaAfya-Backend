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
