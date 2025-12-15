from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from backend.auth.routes import router
from dotenv import load_dotenv
import os
from backend.chat.routes import router as chat_router


load_dotenv()

# Security scheme for Swagger UI
security = HTTPBearer()

app = FastAPI(
    title="Repair Assistant API",
    description="AI-powered repair assistant with iFixit integration. Use the 'Authorize' button to add your Bearer token.",
    version="1.0.0"
)

# Health check endpoint (no auth required)
@app.get("/")
def root():
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
    return {
        "status": "healthy",
        "auth_mode": "development (bypassed)" if bypass_auth else "production",
        "supabase_url": os.getenv("SUPABASE_URL", "not set")
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
