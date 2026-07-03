import uvicorn
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.routers import ussd
from app.routers.auth import router as auth_router
from app.routers.mothers import router as mothers_router
from app.routers.birth_plans import router as birth_plans_router
from app.routers.chw import router as chw_router
from app.routers.appointments import router as appointments_router
from app.sockets.dashboard import register_socket_events

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing database tables...")
    await init_db()
    logger.info("Database tables initialized successfully!")
    yield
    # Shutdown actions
    logger.info("Shutting down API server...")

# Initialize FastAPI App
app = FastAPI(
    title="MamaAfya API",
    description="Maternal Health Information System (MHIS) Backend for Kenya",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*" # Allows all origins for development
)

# Combine Socket.IO server and FastAPI app as a single ASGI application
combined_asgi_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path="/socket.io"
)

# Register Socket.IO event handlers
register_socket_events(sio)

# Attach Socket.IO instance to app state so routers can emit events
app.state.sio = sio

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(mothers_router)
app.include_router(birth_plans_router)
app.include_router(chw_router)
app.include_router(appointments_router)
app.include_router(ussd.router, prefix="/api/ussd", tags=["USSD Webhook"])

@app.get("/api/health", tags=["Health Checks"])
async def health_check():
    """Service health state check"""
    return {
        "status": "healthy",
        "service": "MamaAfya Backend API",
        "version": "1.0.0"
    }

@app.get("/", tags=["Root"])
async def root():
    """Welcome index endpoint"""
    return {
        "message": "Welcome to the MamaAfya Maternal Health API!",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:combined_asgi_app", host="0.0.0.0", port=8000, reload=True)
