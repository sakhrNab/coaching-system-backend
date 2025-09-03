"""
Main FastAPI application entry point
This file imports and combines all the separate API modules
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Import all our API modules
from .core_api import router as core_router
from .admin_api import router as admin_router
from .webhook_handler import router as webhook_router
from .additional_backend_endpoints import router as additional_router
from .database import db

# Create main FastAPI app
app = FastAPI(
    title="Coaching System API",
    description="AI-powered coaching platform with WhatsApp integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(core_router, prefix="", tags=["core"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(webhook_router, prefix="/webhook", tags=["webhooks"])
app.include_router(additional_router, tags=["additional"])

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await db.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()

@app.get("/")
async def root():
    return {"message": "Coaching System API", "status": "operational"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "cors_enabled": True}

@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive system health monitoring"""
    try:
        # Check database connection
        db_status = "connected" if hasattr(db, 'pool') and db.pool else "disconnected"
        
        # Check environment variables
        env_status = {
            "db_host": bool(os.getenv("DB_HOST")),
            "db_password": bool(os.getenv("DB_PASSWORD")),
            "openai_key": bool(os.getenv("OPENAI_API_KEY")),
            "whatsapp_token": bool(os.getenv("WHATSAPP_ACCESS_TOKEN"))
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_status,
            "environment": env_status,
            "services": {
                "api": "running",
                "database": db_status,
                "cors": "enabled"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)