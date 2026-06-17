from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from auth.routes import router
from dotenv import load_dotenv
import os
from chat.routes import router as chat_router
from agents.utils import debug_print
from postgres_client import init_postgres


load_dotenv()

# Security scheme for Swagger UI
security = HTTPBearer()

app = FastAPI(
    title="Repair Assistant API",
    description="AI-powered repair assistant with iFixit integration. Use the 'Authorize' button to add your Bearer token.",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connections and indexes on startup."""
    init_postgres()
    print("✅ Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    print("👋 Application shutdown complete")


# Health check endpoint (no auth required)
@app.get("/")
def root():
    debug_print("DEBUG: Root endpoint called")
    return {
        "status": "online",
        "message": "Repair Assistant API",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "auth": "/login, /signup",
            "chat": "/chat, /chat/stream"
        }
    }

@app.get("/health")
def health():
    bypass_auth = os.getenv("BYPASS_AUTH", "false").lower() == "true"
    neon_url = os.getenv("NEON_URL", "not set")
    # Hide credentials in health check
    neon_status = "configured" if neon_url != "not set" else "not configured"
    
    return {
        "status": "healthy",
        "auth_mode": "development (bypassed)" if bypass_auth else "production",
        "databases": {
            "Neon Postgres": neon_status
        }
    }

# Enable CORS (for frontend) - must be before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Include routes
app.include_router(router)  # Auth routes
app.include_router(chat_router)  # Chat routes
