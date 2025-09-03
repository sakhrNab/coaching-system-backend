"""
Main FastAPI application entry point
This file imports and combines all the separate API modules
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get CORS origins from environment or use defaults
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://bosow0kowcgscoc0os4s0sgo.63.250.59.208.sslip.io",
    "https://bosow0kowcgscoc0os4s0sgo.63.250.59.208.sslip.io",
    "http://s8oc4oswwgcc4gw4cwg8kcsw.63.250.59.208.sslip.io",
    "https://s8oc4oswwgcc4gw4cwg8kcsw.63.250.59.208.sslip.io",
    "*"  # Allow all origins for development
]

# Import all our API modules
from .core_api import router as core_router
from .admin_api import router as admin_router
from .webhook_handler import router as webhook_router
from .additional_backend_endpoints import router as additional_router
from .database import db
from .utils.logging_config import setup_logging

# Setup logging
setup_logging()

# Create main FastAPI app
app = FastAPI(
    title="Coaching System API",
    description="AI-powered coaching platform with WhatsApp integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Custom middleware to ensure CORS headers
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Include all routers
app.include_router(core_router, prefix="", tags=["core"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(webhook_router, prefix="/webhook", tags=["webhooks"])
app.include_router(additional_router, prefix="", tags=["additional"])

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

@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """Handle all OPTIONS requests for CORS preflight"""
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)