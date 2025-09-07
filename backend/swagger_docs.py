"""
Swagger documentation for key API endpoints
This file contains detailed documentation for the most important endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# Import common response schemas
from .swagger_config import COMMON_RESPONSES

# Pydantic models for documentation
class CoachRegistrationDoc(BaseModel):
    """Coach registration request model"""
    barcode: str = Field(..., description="Unique barcode identifier for the coach", example="COACH123")
    whatsapp_token: str = Field(..., description="WhatsApp access token for the coach", example="EAAUt7DLYKPc...")
    name: str = Field(..., description="Full name of the coach", example="John Doe")
    email: Optional[str] = Field(None, description="Email address of the coach", example="john@example.com")
    timezone: str = Field("EST", description="Coach's timezone", example="EST")

class ClientDoc(BaseModel):
    """Client information model"""
    name: str = Field(..., description="Full name of the client", example="Jane Smith")
    phone_number: str = Field(..., description="Client's phone number in E.164 format", example="+1234567890")
    country: Optional[str] = Field("USA", description="Client's country", example="USA")
    timezone: str = Field("EST", description="Client's timezone", example="EST")
    categories: List[str] = Field([], description="List of coaching categories", example=["Health", "Fitness"])

class MessageRequestDoc(BaseModel):
    """Message sending request model"""
    client_ids: List[str] = Field(..., description="List of client IDs to send message to", example=["550e8400-e29b-41d4-a716-446655440000"])
    message_type: str = Field(..., description="Type of message", example="celebration", enum=["celebration", "accountability"])
    content: str = Field(..., description="Message content", example="🎉 What are we celebrating today?")
    schedule_type: str = Field(..., description="When to send the message", example="now", enum=["now", "specific", "recurring"])
    scheduled_time: Optional[datetime] = Field(None, description="Specific time to send (for 'specific' schedule_type)", example="2025-09-07T15:30:00Z")
    recurring_pattern: Optional[Dict[str, Any]] = Field(None, description="Recurring pattern (for 'recurring' schedule_type)")

class QRGenerateRequestDoc(BaseModel):
    """QR code generation request model"""
    expires_in_minutes: int = Field(15, description="Minutes until QR code expires", example=15, ge=1, le=60)

class QRGenerateResponseDoc(BaseModel):
    """QR code generation response model"""
    image_qr: str = Field(..., description="Base64 encoded PNG QR code image", example="data:image/png;base64,iVBORw0KGgo...")
    text_qr: str = Field(..., description="Base64 encoded text QR code", example="data:text/plain;base64,Q29hY2ggUmVnaXN0cmF0aW9u...")
    url: str = Field(..., description="Direct onboarding URL", example="https://coach.aiwaverider.com/onboard/start?session=abc123")
    session_id: str = Field(..., description="Unique session ID", example="abc123def456")
    expires_at: datetime = Field(..., description="QR code expiration time", example="2025-09-07T10:15:00Z")
    onboarding_url: str = Field(..., description="Mobile-friendly onboarding URL", example="https://coach.aiwaverider.com/onboard/start?session=abc123")

class OnboardSubmitRequestDoc(BaseModel):
    """Phone number submission for onboarding"""
    session_id: str = Field(..., description="QR session ID", example="abc123def456")
    phone: str = Field(..., description="Phone number in E.164 format", example="+1234567890")

class OnboardVerifyRequestDoc(BaseModel):
    """OTP verification for onboarding"""
    session_id: str = Field(..., description="QR session ID", example="abc123def456")
    code: str = Field(..., description="6-digit verification code", example="123456")

class ClientResponseDoc(BaseModel):
    """Client response model"""
    id: str = Field(..., description="Unique client ID", example="550e8400-e29b-41d4-a716-446655440000")
    name: str = Field(..., description="Client name", example="Jane Smith")
    phone_number: str = Field(..., description="Phone number", example="+1234567890")
    categories: List[str] = Field(..., description="Coaching categories", example=["Health", "Fitness"])
    timezone: str = Field(..., description="Client timezone", example="EST")
    created_at: datetime = Field(..., description="Creation timestamp", example="2025-09-07T10:00:00Z")

class MessageTemplateDoc(BaseModel):
    """Message template model"""
    id: str = Field(..., description="Template ID", example="550e8400-e29b-41d4-a716-446655440000")
    message_type: str = Field(..., description="Template type", example="celebration", enum=["celebration", "accountability"])
    content: str = Field(..., description="Template content", example="🎉 What are we celebrating today?")
    is_default: bool = Field(..., description="Is default template", example=True)
    whatsapp_template_name: Optional[str] = Field(None, description="WhatsApp template name", example="celebration_message_6")
    language_code: Optional[str] = Field(None, description="Template language code", example="en")

class FreeMessageStatusDoc(BaseModel):
    """24-hour window status model"""
    can_send_free: bool = Field(..., description="Can send free-form message", example=True)
    last_user_message: Optional[datetime] = Field(None, description="Last user message timestamp", example="2025-09-07T09:00:00Z")
    window_expires_at: Optional[datetime] = Field(None, description="24-hour window expiration", example="2025-09-08T09:00:00Z")

# Example responses for documentation
EXAMPLE_RESPONSES = {
    "coach_registration": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "timezone": "EST",
        "created_at": "2025-09-07T10:00:00Z",
        "status": "active"
    },
    "client_list": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Jane Smith",
            "phone_number": "+1234567890",
            "categories": ["Health", "Fitness"],
            "timezone": "EST",
            "created_at": "2025-09-07T10:00:00Z"
        }
    ],
    "message_sent": {
        "message_id": "msg_123456789",
        "status": "sent",
        "recipients": ["+1234567890"],
        "template_used": "celebration_message_6",
        "sent_at": "2025-09-07T10:00:00Z"
    },
    "qr_generated": {
        "image_qr": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAcIA...",
        "text_qr": "data:text/plain;base64,Q29hY2ggUmVnaXN0cmF0aW9u...",
        "url": "https://coach.aiwaverider.com/onboard/start?session=abc123",
        "session_id": "abc123def456",
        "expires_at": "2025-09-07T10:15:00Z",
        "onboarding_url": "https://coach.aiwaverider.com/onboard/start?session=abc123"
    },
    "templates_list": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "message_type": "celebration",
            "content": "🎉 What are we celebrating today?",
            "is_default": True,
            "whatsapp_template_name": "celebration_message_6",
            "language_code": "en"
        }
    ],
    "free_message_status": {
        "can_send_free": True,
        "last_user_message": "2025-09-07T09:00:00Z",
        "window_expires_at": "2025-09-08T09:00:00Z"
    }
}

