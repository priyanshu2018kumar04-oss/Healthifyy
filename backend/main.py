"""
Healthify AI Agent — FastAPI application entry point.
"""
import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Allow importing the standalone LangGraph agent from /agent at repo root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import engine, Base
from routers import auth_router, health_router, plan_router, progress_router
from services.scheduler import create_scheduler

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("healthify")

# ─── App Lifecycle ─────────────────────────────────────────────────────────────

scheduler = create_scheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables on startup
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")

    # Start background scheduler
    scheduler.start()
    logger.info("Background scheduler started (weekly reports every Sunday 8AM IST).")

    yield  # App is running

    # Shutdown scheduler gracefully
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped. Healthify shutting down.")


# ─── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Healthify AI Agent API",
    description=(
        "AI-powered personal health monitoring and planning system. "
        "Powered by LangGraph + Groq (LLaMA 3.3-70b)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

ALLOWED_ORIGINS = [
    # Local development
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    # Vercel production deployments
    "https://healthifyy-65xydnp3m-healthify1.vercel.app",
    "https://healthifyy-healthify1.vercel.app",
    "https://healthifyy.vercel.app",
    # Render backend (for health checks)
    "https://healthifyy-1healthifyy-backend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router.router,     prefix="/api/auth",     tags=["🔐 Authentication"])
app.include_router(health_router.router,   prefix="/api/health",   tags=["❤️ Health Tracking"])
app.include_router(plan_router.router,     prefix="/api/plan",     tags=["🤖 AI Plans"])
app.include_router(progress_router.router, prefix="/api/progress", tags=["📊 Progress"])

# ─── Root ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {
        "app": "Healthify AI Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "description": "AI-powered personal health agent with LangGraph + Groq",
    }

@app.get("/api/ping", tags=["Root"])
def ping():
    return {"status": "pong", "service": "Healthify API"}
