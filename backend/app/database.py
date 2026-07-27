from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings

# Determine if we are using SQLite or PostgreSQL
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# For SQLite, we want to allow concurrent operations if possible, but async handles it nicely.
# We also use connect_args for SQLite specifically.
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
    "echo": False,
}

if not is_sqlite:
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables for SQLite development"""
    # Import models here to ensure they are registered on Base
    from app.models.user import User
    from app.models.mother_profile import MotherProfile
    from app.models.birth_plan import BirthPlan
    from app.models.symptom_log import SymptomLog
    from app.models.appointment import Appointment
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
