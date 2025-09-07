"""
Meta API Internal Endpoints for Testing

These endpoints expose internal Meta API calls for testing and debugging purposes.
They are not part of the main public API but are useful for development and testing.

Note: These are internal service calls that your backend makes to Meta's Graph API.
They are exposed here for testing purposes only.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import httpx
import os
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/meta", tags=["Meta API - Internal Testing"])

# Debug endpoint to test if router is working
@router.get("/test",
            summary="Test Meta API Router",
            description="Test endpoint to verify Meta API router is working",
            tags=["Meta API - Internal Testing"])
async def test_meta_router():
    """Test endpoint to verify Meta API router is working"""
    return {
        "success": True,
        "message": "Meta API router is working!",
        "endpoints": [
            "/meta/waba-id",
            "/meta/phone-number/register",
            "/meta/phone-number/verify",
            "/meta/message/send",
            "/meta/phone-numbers",
            "/meta/webhook/verify",
            "/meta/status"
        ]
    }

# Meta API configuration
META_API_VERSION = os.getenv("META_API_VERSION", "v23.0")
META_SYSTEM_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
META_GRAPH_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"

# Dependency function for Meta system token
def get_meta_system_token() -> str:
    """Get Meta system token for API calls"""
    if not META_SYSTEM_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Meta system token not configured. Please set WHATSAPP_ACCESS_TOKEN environment variable."
        )
    return META_SYSTEM_TOKEN

class PhoneNumberRequest(BaseModel):
    """Request model for phone number registration"""
    phone_number: str = Field(..., description="Phone number in E.164 format", example="+1234567890")
    display_phone_number: str = Field(..., description="Display phone number", example="+1 (234) 567-8900")

class OTPVerificationRequest(BaseModel):
    """Request model for OTP verification"""
    phone_number_id: str = Field(..., description="Phone number ID from Meta", example="123456789012345")
    pin: str = Field(..., description="6-digit verification code", example="123456")

class MessageSendRequest(BaseModel):
    """Request model for sending messages via Meta API"""
    phone_number_id: str = Field(..., description="Phone number ID", example="123456789012345")
    to: str = Field(..., description="Recipient phone number", example="+1234567890")
    message: str = Field(..., description="Message content", example="Hello from Meta API!")

class WABAResponse(BaseModel):
    """Response model for WABA operations"""
    success: bool
    waba_id: Optional[str] = None
    message: str
    data: Optional[Dict[str, Any]] = None

@router.get("/waba-id",
            summary="Get WABA ID from Meta",
            description="""
            Get the WhatsApp Business Account ID from Meta's Graph API.
            
            **Note:** This is an internal API call that your backend makes to Meta.
            Exposed here for testing and debugging purposes.
            
            **Internal URL:** `GET https://graph.facebook.com/v23.0/me`
            
            **Features:**
            - Fetches WABA ID from Meta
            - Uses system token authentication
            - Error handling and logging
            - Testing and debugging support
            
            **Use Cases:**
            - Testing Meta API connectivity
            - Debugging WABA ID issues
            - Verifying system token
            - Development testing
            """,
            responses={
                200: {"description": "WABA ID retrieved successfully"},
                401: {"description": "Meta API authentication failed"},
                500: {"description": "Meta API error"}
            })
async def get_waba_id():
    """Get WABA ID from Meta API for testing"""
    if not META_SYSTEM_TOKEN:
        raise HTTPException(status_code=500, detail="Meta API token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/me",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return WABAResponse(
                    success=True,
                    waba_id=data.get("id"),
                    message="WABA ID retrieved successfully",
                    data=data
                )
            else:
                return WABAResponse(
                    success=False,
                    message=f"Meta API error: {response.status_code} - {response.text}"
                )
                
    except Exception as e:
        logger.error(f"Get WABA ID error: {e}")
        raise HTTPException(status_code=500, detail=f"Meta API error: {str(e)}")

@router.post("/phone-number/register",
             summary="Register Phone Number with Meta",
             description="""
             Register a phone number with Meta's WhatsApp Business API.
             
            **Note:** This is an internal API call that your backend makes to Meta.
            Exposed here for testing and debugging purposes.
            
            **Internal URLs:** 
            - `GET https://graph.facebook.com/v23.0/me` (get WABA ID)
            - `POST https://graph.facebook.com/v23.0/{waba_id}/phone_numbers` (register phone)
            
            **Features:**
            - Phone number registration
            - Meta API integration
            - Error handling
            - Testing support
             
             **Use Cases:**
             - Testing phone registration
             - Debugging Meta API calls
             - Development testing
             - API validation
             """,
             responses={
                 200: {"description": "Phone number registered successfully"},
                 400: {"description": "Invalid phone number or Meta API error"},
                 500: {"description": "Registration error"}
             })
async def register_phone_number(request: PhoneNumberRequest):
    """Register phone number with Meta for testing"""
    if not META_SYSTEM_TOKEN:
        raise HTTPException(status_code=500, detail="Meta API token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # First, get WABA ID
            waba_response = await client.get(
                f"{META_GRAPH_API_BASE}/me",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"}
            )
            
            if waba_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get WABA ID")
            
            waba_data = waba_response.json()
            waba_id = waba_data.get("id")
            
            # Register phone number
            phone_data = {
                "display_phone_number": request.display_phone_number,
                "phone_number": request.phone_number
            }
            
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{waba_id}/phone_numbers",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"},
                json=phone_data
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "Phone number registered successfully",
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": f"Meta API error: {response.status_code} - {response.text}"
                }
                
    except Exception as e:
        logger.error(f"Register phone number error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

@router.post("/phone-number/verify",
             summary="Verify Phone Number with Meta",
             description="""
             Verify a phone number with Meta using OTP code.
             
            **Note:** This is an internal API call that your backend makes to Meta.
            Exposed here for testing and debugging purposes.
            
            **Internal URL:** `POST https://graph.facebook.com/v23.0/{phone_number_id}/verify`
            
            **Features:**
            - OTP verification
            - Phone number activation
            - Meta API integration
            - Testing support
             
             **Use Cases:**
             - Testing OTP verification
             - Debugging phone activation
             - Development testing
             - API validation
             """,
             responses={
                 200: {"description": "Phone number verified successfully"},
                 400: {"description": "Invalid OTP or Meta API error"},
                 500: {"description": "Verification error"}
             })
async def verify_phone_number(request: OTPVerificationRequest):
    """Verify phone number with Meta using OTP for testing"""
    if not META_SYSTEM_TOKEN:
        raise HTTPException(status_code=500, detail="Meta API token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # Verify phone number
            verify_data = {
                "code": request.pin
            }
            
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{request.phone_number_id}/verify",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"},
                json=verify_data
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "Phone number verified successfully",
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": f"Meta API error: {response.status_code} - {response.text}"
                }
                
    except Exception as e:
        logger.error(f"Verify phone number error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")

@router.post("/message/send",
             summary="Send Message via Meta API",
             description="""
             Send a message directly through Meta's WhatsApp Business API.
             
            **Note:** This is an internal API call that your backend makes to Meta.
            Exposed here for testing and debugging purposes.
            
            **Internal URL:** `POST https://graph.facebook.com/v23.0/{phone_number_id}/messages`
            
            **Features:**
            - Direct message sending
            - Meta API integration
            - Error handling
            - Testing support
             
             **Use Cases:**
             - Testing message sending
             - Debugging Meta API calls
             - Development testing
             - API validation
             """,
             responses={
                 200: {"description": "Message sent successfully"},
                 400: {"description": "Invalid message data or Meta API error"},
                 500: {"description": "Message sending error"}
             })
async def send_message_meta(request: MessageSendRequest):
    """Send message via Meta API for testing"""
    if not META_SYSTEM_TOKEN:
        raise HTTPException(status_code=500, detail="Meta API token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # Send message
            message_data = {
                "messaging_product": "whatsapp",
                "to": request.to,
                "type": "text",
                "text": {"body": request.message}
            }
            
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{request.phone_number_id}/messages",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"},
                json=message_data
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "Message sent successfully",
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": f"Meta API error: {response.status_code} - {response.text}"
                }
                
    except Exception as e:
        logger.error(f"Send message error: {e}")
        raise HTTPException(status_code=500, detail=f"Message sending error: {str(e)}")

@router.get("/phone-numbers",
            summary="Get Registered Phone Numbers",
            description="""
            Get all registered phone numbers from Meta's WhatsApp Business API.
            
            **Note:** This is an internal API call that your backend makes to Meta.
            Exposed here for testing and debugging purposes.
            
            **Internal URLs:**
            - `GET https://graph.facebook.com/v23.0/me` (get WABA ID)
            - `GET https://graph.facebook.com/v23.0/{waba_id}/phone_numbers` (list phones)
            
            **Features:**
            - List phone numbers
            - Meta API integration
            - Error handling
            - Testing support
            
            **Use Cases:**
            - Testing phone number listing
            - Debugging Meta API calls
            - Development testing
            - API validation
            """,
            responses={
                200: {"description": "Phone numbers retrieved successfully"},
                401: {"description": "Meta API authentication failed"},
                500: {"description": "Meta API error"}
            })
async def get_phone_numbers():
    """Get registered phone numbers from Meta API for testing"""
    if not META_SYSTEM_TOKEN:
        raise HTTPException(status_code=500, detail="Meta API token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # First, get WABA ID
            waba_response = await client.get(
                f"{META_GRAPH_API_BASE}/me",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"}
            )
            
            if waba_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get WABA ID")
            
            waba_data = waba_response.json()
            waba_id = waba_data.get("id")
            
            # Get phone numbers
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{waba_id}/phone_numbers",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "Phone numbers retrieved successfully",
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": f"Meta API error: {response.status_code} - {response.text}"
                }
                
    except Exception as e:
        logger.error(f"Get phone numbers error: {e}")
        raise HTTPException(status_code=500, detail=f"Meta API error: {str(e)}")

@router.get("/webhook/verify",
            summary="Verify Meta Webhook Configuration",
            description="""
            Verify Meta webhook configuration and test webhook endpoint.
            
            **Note:** This is an internal API call that your backend makes to Meta.
            Exposed here for testing and debugging purposes.
            
            **Internal URL:** `GET https://graph.facebook.com/v23.0/me/subscribed_apps`
            
            **Features:**
            - Webhook verification
            - Meta API integration
            - Error handling
            - Testing support
            
            **Use Cases:**
            - Testing webhook configuration
            - Debugging Meta webhook setup
            - Development testing
            - API validation
            """,
            responses={
                200: {"description": "Webhook verification successful"},
                400: {"description": "Webhook verification failed"},
                500: {"description": "Verification error"}
            })
async def verify_webhook_config():
    """Verify Meta webhook configuration for testing"""
    if not META_SYSTEM_TOKEN:
        raise HTTPException(status_code=500, detail="Meta API token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # Get webhook configuration
            response = await client.get(
                f"{META_GRAPH_API_BASE}/me/subscribed_apps",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "Webhook configuration retrieved successfully",
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": f"Meta API error: {response.status_code} - {response.text}"
                }
                
    except Exception as e:
        logger.error(f"Verify webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")

@router.get("/status",
            summary="Meta API Status Check",
            description="""
            Check Meta API connectivity and authentication status.
            
            **Note:** This is an internal API call that your backend makes to Meta.
            Exposed here for testing and debugging purposes.
            
            **Internal URL:** `GET https://graph.facebook.com/v23.0/me`
            
            **Features:**
            - API connectivity check
            - Authentication verification
            - Error handling
            - Testing support
            
            **Use Cases:**
            - Testing Meta API connectivity
            - Debugging authentication issues
            - Development testing
            - API validation
            """,
            responses={
                200: {"description": "Meta API status check successful"},
                401: {"description": "Meta API authentication failed"},
                500: {"description": "Status check error"}
            })
async def check_meta_api_status():
    """Check Meta API status for testing"""
    if not META_SYSTEM_TOKEN:
        return {
            "success": False,
            "message": "Meta API token not configured",
            "status": "not_configured"
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/me",
                headers={"Authorization": f"Bearer {META_SYSTEM_TOKEN}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "Meta API is accessible and authenticated",
                    "status": "connected",
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": f"Meta API error: {response.status_code} - {response.text}",
                    "status": "error"
                }
                
    except Exception as e:
        logger.error(f"Meta API status check error: {e}")
        return {
            "success": False,
            "message": f"Meta API error: {str(e)}",
            "status": "error"
        }
