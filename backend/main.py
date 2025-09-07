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
from .qr_onboarding import router as qr_onboarding_router
# Removed duplicate webhook handlers - using core_api webhook only
from .additional_backend_endpoints import router as additional_router
from .meta_api_endpoints import router as meta_api_router
from .sql_documentation import router as sql_docs_router
from .database import db
from .swagger_config import create_swagger_app, custom_openapi
from .custom_swagger_ui import setup_custom_swagger_routes

# Create main FastAPI app with Swagger
app = create_swagger_app()
app.openapi = lambda: custom_openapi(app)

# Add CORS middleware with explicit production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins
        "https://coach.aiwaverider.com",  # New backend domain
        "https://coach-system.aiwaverider.com",  # New frontend domain
        "http://bosow0kowcgscoc0os4s0sgo.63.250.59.208.sslip.io",  # Legacy domain (for transition)
        "https://bosow0kowcgscoc0os4s0sgo.63.250.59.208.sslip.io",  # Legacy HTTPS (for transition)
        "http://localhost:3000",  # Local development
        "http://localhost:8000",  # Local development
        "http://localhost:8001",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "*",
        "Content-Type",
        "Authorization", 
        "Accept",
        "Origin",
        "User-Agent",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Include all routers with proper tags
app.include_router(core_router, prefix="", tags=["System Health", "Coach Registration", "Client CRUD", "Message Sending", "WhatsApp Webhooks", "Voice Processing", "Webhook Testing", "Data Export", "Analytics", "Goal Management", "Message Scheduling"])
app.include_router(admin_router, prefix="/admin", tags=["Admin - System Statistics", "Admin - Coach Management", "Admin - System Monitoring", "Admin - System Management", "Admin - Analytics"])
app.include_router(qr_onboarding_router, tags=["QR Onboarding", "Coach Registration"])
# Removed duplicate webhook router - using core_api webhook only
app.include_router(additional_router, tags=["Client CRUD", "Client Import/Export", "Client Categories", "Client History", "Message Templates", "Message Scheduling", "Analytics", "Goal Management", "Message Sending", "System Health", "System Configuration"])
app.include_router(meta_api_router, tags=["Meta API - Internal Testing"])
app.include_router(sql_docs_router, tags=["SQL Documentation"])

# Setup custom Swagger UI with environment switching
# setup_custom_swagger_routes(app)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await db.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()

@app.get("/", 
         summary="API Root",
         description="Get basic API information and status",
         tags=["Health & Status"],
         responses={
             200: {
                 "description": "API is operational",
                 "content": {
                     "application/json": {
                         "example": {
                             "message": "Coaching System API",
                             "status": "operational",
                             "version": "1.0.0"
                         }
                     }
                 }
             }
         })
async def root():
    return {"message": "Coaching System API", "status": "operational", "version": "1.0.0"}

@app.get("/health",
         summary="Basic Health Check",
         description="Quick health check to verify API is running",
         tags=["Health & Status"],
         responses={
             200: {
                 "description": "API is healthy",
                 "content": {
                     "application/json": {
                         "example": {
                             "status": "healthy",
                             "cors_enabled": True,
                             "timestamp": "2025-09-07T10:00:00Z"
                         }
                     }
                 }
             }
         })
async def health_check():
    return {"status": "healthy", "cors_enabled": True, "timestamp": datetime.now().isoformat()}

@app.get("/health/detailed",
         summary="Detailed Health Check",
         description="Comprehensive system health monitoring including database, environment variables, and service status",
         tags=["Health & Status"],
         responses={
             200: {
                 "description": "Detailed health information",
                 "content": {
                     "application/json": {
                         "example": {
                             "status": "healthy",
                             "timestamp": "2025-09-07T10:00:00Z",
                             "database": "connected",
                             "environment": {
                                 "db_host": True,
                                 "db_password": True,
                                 "openai_key": True,
                                 "whatsapp_token": True
                             },
                             "services": {
                                 "api": "running",
                                 "database": "connected",
                                 "cors": "enabled"
                             }
                         }
                     }
                 }
             },
             500: {
                 "description": "System unhealthy",
                 "content": {
                     "application/json": {
                         "example": {
                             "status": "unhealthy",
                             "error": "Database connection failed",
                             "timestamp": "2025-09-07T10:00:00Z"
                         }
                     }
                 }
             }
         })
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

# Explicit CORS preflight handler for all routes
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle all OPTIONS requests for CORS preflight"""
    from fastapi import Response
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, User-Agent, X-Requested-With"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)