"""
Swagger/OpenAPI configuration for the Coaching System API
"""
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
import os

def create_swagger_app() -> FastAPI:
    """Create FastAPI app with comprehensive Swagger documentation"""
    
    app = FastAPI(
        title="Coaching System API",
        description="""
        ## 🏆 Coaching System API Documentation
        
        A comprehensive API for managing coaches, clients, and WhatsApp messaging in a coaching system.
        
        ### 🔧 Features
        - **Coach Management**: Registration, authentication, and profile management
        - **Client Management**: Add, update, and manage client information
        - **WhatsApp Integration**: Send messages, templates, and track conversations
        - **QR Onboarding**: Generate QR codes for coach registration
        - **Message Scheduling**: Schedule celebration and accountability messages
        - **24-Hour Window Tracking**: Monitor Meta's messaging window compliance
        
        ### 🌐 Environment Switching
        Use the environment selector in the top-right to switch between:
        - **Development**: `http://localhost:8001`
        - **Production**: `https://coach.aiwaverider.com`
        
        ### 🔐 Authentication
        Most endpoints require a valid coach ID. Some endpoints use JWT tokens for authentication.
        
        ### 📱 WhatsApp Integration
        The API integrates with Meta's WhatsApp Business API for:
        - Sending template messages
        - Sending custom messages (within 24-hour window)
        - Webhook handling for message status updates
        - Phone number registration and verification
        
        ### 🎯 Message Types
        - **Celebration Messages**: Templates 6-10 for positive reinforcement
        - **Accountability Messages**: Templates 1-5 for goal tracking
        - **Custom Messages**: Free-form text (subject to 24-hour window rules)
        
        ### 📊 Database Schema
        The API uses PostgreSQL with the following main tables:
        - `coaches`: Coach profiles and authentication
        - `clients`: Client information and categories
        - `message_templates`: WhatsApp template definitions
        - `scheduled_messages`: Message scheduling
        - `whatsapp_conversations`: 24-hour window tracking
        - `onboarding_sessions`: QR code session management
        """,
        version="1.0.0",
        contact={
            "name": "Coaching System Support",
            "email": "support@aiwaverider.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "http://localhost:8001",
                "description": "Development Server",
            },
            {
                "url": "https://coach.aiwaverider.com",
                "description": "Production Server",
            },
        ],
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "https://coach-system.aiwaverider.com",
            "https://coach.aiwaverider.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI schema with enhanced documentation"""
    
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Coaching System API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
        servers=[
            {
                "url": "http://localhost:8001",
                "description": "Development Server",
            },
            {
                "url": "https://coach.aiwaverider.com",
                "description": "Production Server",
            },
        ],
    )
    
    # Add custom tags for better organization
    openapi_schema["tags"] = [
        # === SYSTEM & HEALTH ===
        {
            "name": "System Health",
            "description": "System health checks, monitoring, and status",
        },
        {
            "name": "System Configuration", 
            "description": "App configuration and system settings",
        },
        
        # === COACH MANAGEMENT ===
        {
            "name": "Coach Registration",
            "description": "Coach registration, authentication, and onboarding",
        },
        {
            "name": "Coach Profile",
            "description": "Coach profile management and settings",
        },
        {
            "name": "QR Onboarding",
            "description": "QR code generation and coach onboarding process",
        },
        
        # === CLIENT MANAGEMENT ===
        {
            "name": "Client CRUD",
            "description": "Client create, read, update, delete operations",
        },
        {
            "name": "Client Import/Export",
            "description": "Bulk client import, export, and data migration",
        },
        {
            "name": "Client Categories",
            "description": "Client categorization and grouping",
        },
        {
            "name": "Client History",
            "description": "Client message history and activity tracking",
        },
        
        # === MESSAGING ===
        {
            "name": "Message Sending",
            "description": "Send individual and bulk messages",
        },
        {
            "name": "Message Templates",
            "description": "Template management and customization",
        },
        {
            "name": "Message Scheduling",
            "description": "Schedule messages and automation",
        },
        {
            "name": "Voice Processing",
            "description": "Voice message transcription and processing",
        },
        
        # === WHATSAPP INTEGRATION ===
        {
            "name": "WhatsApp Webhooks",
            "description": "Webhook handling and message processing",
        },
        {
            "name": "Webhook Testing",
            "description": "Webhook testing and debugging tools",
        },
        {
            "name": "Meta API - Internal Testing",
            "description": "Internal Meta API calls for testing and debugging",
        },
        
        # === ANALYTICS & REPORTING ===
        {
            "name": "Analytics",
            "description": "Message analytics and performance metrics",
        },
        {
            "name": "Data Export",
            "description": "Export data and generate reports",
        },
        
        # === GOAL MANAGEMENT ===
        {
            "name": "Goal Management",
            "description": "Client goal setting and tracking",
        },
        
        # === ADMIN FUNCTIONS ===
        {
            "name": "Admin - System Statistics",
            "description": "System-wide statistics and metrics",
        },
        {
            "name": "Admin - Coach Management",
            "description": "Admin coach management and oversight",
        },
        {
            "name": "Admin - System Monitoring",
            "description": "System monitoring and performance tracking",
        },
        {
            "name": "Admin - System Management",
            "description": "System maintenance and management tasks",
        },
        {
            "name": "Admin - Analytics",
            "description": "Admin-level analytics and reporting",
        },
        
        # === DOCUMENTATION ===
        {
            "name": "SQL Documentation",
            "description": "Password-protected SQL queries and database documentation",
        },
    ]
    
    # Add example responses and request bodies
    openapi_schema["components"]["examples"] = {
        "CoachRegistration": {
            "summary": "Coach Registration Example",
            "value": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "barcode": "COACH123"
            }
        },
        "ClientCreation": {
            "summary": "Client Creation Example", 
            "value": {
                "name": "Jane Smith",
                "phone_number": "+1987654321",
                "categories": ["Health", "Fitness"],
                "timezone": "EST"
            }
        },
        "MessageSending": {
            "summary": "Message Sending Example",
            "value": {
                "client_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                "message_type": "celebration",
                "content": "🎉 What are we celebrating today?",
                "schedule_type": "now"
            }
        },
        "QRGeneration": {
            "summary": "QR Code Generation Example",
            "value": {
                "expires_in_minutes": 15
            }
        }
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for authentication"
        },
        "CoachIdAuth": {
            "type": "apiKey",
            "in": "path",
            "name": "coach_id",
            "description": "Coach ID in the URL path"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Common response schemas
COMMON_RESPONSES = {
    200: {
        "description": "Success",
        "content": {
            "application/json": {
                "example": {"status": "success", "message": "Operation completed successfully"}
            }
        }
    },
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {"detail": "Invalid request parameters"}
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {"detail": "Authentication required"}
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {"detail": "Resource not found"}
            }
        }
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {"detail": [{"loc": ["body", "field"], "msg": "field required", "type": "value_error.missing"}]}
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {"detail": "Internal server error occurred"}
            }
        }
    }
}
