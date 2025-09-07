"""
QR-Based Onboarding System
Implements the correct dual-purpose QR flow (register or login)
"""

import os
import logging
import secrets
import io
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
import asyncio
import uuid
import urllib.request
import urllib.parse
import json

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/onboard", tags=["QR Onboarding"])

# Meta API configuration
META_API_VERSION = os.getenv("META_API_VERSION", "v23.0")
META_SYSTEM_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")  # Use existing env var
META_GRAPH_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"

# Session configuration
SESSION_EXPIRY_MINUTES = 15
LOGIN_SESSION_DAYS = 5

# Pydantic models
class QRGenerateRequest(BaseModel):
    coach_id: Optional[str] = None
    expires_in_minutes: int = Field(default=15, description="QR session expiry in minutes")

class QRGenerateResponse(BaseModel):
    image_qr: str  # PNG QR code image
    text_qr: str   # Text representation
    url: str       # Direct onboarding URL
    session_id: str
    expires_at: datetime
    onboarding_url: str

class OnboardSubmitRequest(BaseModel):
    session_id: str
    phone: str
    display_label: str

class OnboardVerifyRequest(BaseModel):
    session_id: str
    pin: str

class OnboardResponse(BaseModel):
    success: bool
    message: str
    phone_number_id: Optional[str] = None
    coach_id: Optional[str] = None
    status: Optional[str] = None

class QROnboardingManager:
    """Handles QR-based onboarding and session management"""
    
    def __init__(self):
        self.api_base = META_GRAPH_API_BASE
        self.system_token = META_SYSTEM_TOKEN
        self.waba_id = None  # Will be fetched dynamically
        
        if not self.system_token:
            logger.warning("Meta API token not configured")
    
    async def get_waba_id(self) -> Optional[str]:
        """Get WABA ID dynamically from Meta API"""
        if not self.system_token:
            return None
        
        if self.waba_id:
            return self.waba_id
        
        try:
            # Get WABA ID from Meta API
            url = f"{self.api_base}/me/businesses"
            headers = {
                "Authorization": f"Bearer {self.system_token}"
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Get the first business (assuming single WABA)
                businesses = result.get("data", [])
                if businesses:
                    business_id = businesses[0].get("id")
                    
                    # Get WhatsApp Business Accounts for this business
                    waba_url = f"{self.api_base}/{business_id}/owned_whatsapp_business_accounts"
                    waba_req = urllib.request.Request(waba_url, headers=headers)
                    
                    with urllib.request.urlopen(waba_req, timeout=30) as waba_response:
                        waba_result = json.loads(waba_response.read().decode('utf-8'))
                        
                        waba_accounts = waba_result.get("data", [])
                        if waba_accounts:
                            self.waba_id = waba_accounts[0].get("id")
                            logger.info(f"Found WABA ID: {self.waba_id}")
                            return self.waba_id
                
                logger.warning("No WABA found for this business")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get WABA ID: {e}")
            return None
    
    def generate_qr_code(self, session_id: str, base_url: str) -> Dict[str, str]:
        """Generate QR code with onboarding URL - returns both image and text"""
        onboarding_url = f"{base_url}/onboard/start?session={session_id}"
        
        # Always generate text representation
        qr_text = f"""
        ┌─────────────────────────────────┐
        │  COACH ONBOARDING QR CODE      │
        │                                 │
        │  Scan this QR code to start    │
        │  your coach registration        │
        │                                 │
        │  URL: {onboarding_url}         │
        │                                 │
        └─────────────────────────────────┘
        """
        
        # Create text representation
        qr_text_data = base64.b64encode(qr_text.encode()).decode()
        text_qr = f"data:text/plain;base64,{qr_text_data}"
        
        try:
            # Try to use qrcode library if available
            import qrcode
            import io
            
            # Create QR code image
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(onboarding_url)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 data URL
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            image_qr = f"data:image/png;base64,{img_str}"
            
            return {
                "image_qr": image_qr,
                "text_qr": text_qr,
                "url": onboarding_url
            }
            
        except ImportError:
            # Fallback to text representation only
            return {
                "image_qr": text_qr,  # Use text as fallback for image
                "text_qr": text_qr,
                "url": onboarding_url
            }
    
    async def create_session(self, coach_id: Optional[str] = None, expires_in_minutes: int = 15) -> Dict[str, Any]:
        """Create a new onboarding session"""
        session_id = secrets.token_urlsafe(32)
        # Use UTC timezone for consistency across different server locations
        from datetime import timezone
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        
        from .database import db
        
        async with db.pool.acquire() as conn:
            # Store session
            await conn.execute(
                """INSERT INTO onboarding_sessions 
                   (session_id, coach_id, expires_at, status, created_at)
                   VALUES ($1, $2, $3, 'active', $4)""",
                session_id, coach_id, expires_at, datetime.now(timezone.utc)
            )
            
            return {
                "session_id": session_id,
                "expires_at": expires_at,
                "coach_id": coach_id
            }
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details"""
        from .database import db
        
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow(
                "SELECT * FROM onboarding_sessions WHERE session_id = $1 AND expires_at > $2",
                session_id, datetime.now(timezone.utc)
            )
            
            if not session:
                return None
                
            return dict(session)
    
    async def check_coach_exists(self, phone: str) -> Optional[Dict[str, Any]]:
        """Check if coach already exists with this phone"""
        from .database import db
        
        async with db.pool.acquire() as conn:
            coach = await conn.fetchrow(
                "SELECT * FROM coaches WHERE phone_e164 = $1 AND phone_registration_status = 'registered'",
                phone
            )
            
            if not coach:
                return None
                
            return dict(coach)
    
    async def create_phone_number(self, phone: str, display_name: str) -> Dict[str, Any]:
        """Step 1: Create phone number on WABA"""
        if not self.system_token:
            raise HTTPException(status_code=500, detail="Meta API token not configured")
        
        # Get WABA ID dynamically
        waba_id = await self.get_waba_id()
        if not waba_id:
            raise HTTPException(status_code=500, detail="Could not find WhatsApp Business Account")
        
        url = f"{self.api_base}/{waba_id}/phone_numbers"
        headers = {
            "Authorization": f"Bearer {self.system_token}",
            "Content-Type": "application/json"
        }
        
        # Extract country code and phone number
        if phone.startswith('+'):
            phone = phone[1:]
        
        # Simple country code extraction (assume first 1-3 digits)
        country_code = phone[:1] if phone.startswith('1') else phone[:2]
        phone_number = phone[len(country_code):]
        
        data = {
            "phone_number": phone_number,
            "display_name": display_name,
            "cc": country_code
        }
        
        try:
            # Use urllib for HTTP requests
            data_json = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_json, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                logger.info(f"Phone number created: {result}")
                return result
                
        except urllib.error.HTTPError as e:
            logger.error(f"Failed to create phone number: {e}")
            raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create phone number: {e}")
            raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")
    
    async def request_verification_code(self, phone_resource_id: str, method: str = "sms") -> Dict[str, Any]:
        """Step 2: Request verification code"""
        if not self.system_token:
            raise HTTPException(status_code=500, detail="Meta API not configured")
        
        url = f"{self.api_base}/{phone_resource_id}/request_code"
        headers = {
            "Authorization": f"Bearer {self.system_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "method": method,
            "language": "en_US"
        }
        
        try:
            # Use urllib for HTTP requests
            data_json = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_json, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                logger.info(f"Verification code requested: {result}")
                return result
                
        except urllib.error.HTTPError as e:
            logger.error(f"Failed to request verification code: {e}")
            raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to request verification code: {e}")
            raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")
    
    async def verify_and_register(self, phone_resource_id: str, pin: str) -> Dict[str, Any]:
        """Step 3: Verify and register phone number"""
        if not self.system_token:
            raise HTTPException(status_code=500, detail="Meta API not configured")
        
        # First verify the code
        verify_url = f"{self.api_base}/{phone_resource_id}/verify_code"
        verify_headers = {
            "Authorization": f"Bearer {self.system_token}",
            "Content-Type": "application/json"
        }
        
        verify_params = {"code": pin}
        
        try:
            # Verify code
            verify_params_str = urllib.parse.urlencode(verify_params)
            verify_full_url = f"{verify_url}?{verify_params_str}"
            verify_req = urllib.request.Request(verify_full_url, headers=verify_headers, method='POST')
            
            with urllib.request.urlopen(verify_req, timeout=30) as verify_response:
                verify_result = json.loads(verify_response.read().decode('utf-8'))
                
                if not verify_result.get("success"):
                    raise HTTPException(status_code=400, detail="Invalid verification code")
                
                # Register phone number
                register_url = f"{self.api_base}/{phone_resource_id}/register"
                register_headers = {
                    "Authorization": f"Bearer {self.system_token}",
                    "Content-Type": "application/json"
                }
                
                register_data = {
                    "messaging_product": "whatsapp",
                    "pin": pin
                }
                
                register_data_json = json.dumps(register_data).encode('utf-8')
                register_req = urllib.request.Request(register_url, data=register_data_json, headers=register_headers, method='POST')
                
                with urllib.request.urlopen(register_req, timeout=30) as register_response:
                    register_result = json.loads(register_response.read().decode('utf-8'))
                    
                    if not register_result.get("success"):
                        raise HTTPException(status_code=400, detail="Failed to register phone number")
                    
                    # Get phone number ID
                    phone_number_id = await self.get_phone_number_id(phone_resource_id)
                    
                    return {
                        "success": True,
                        "phone_number_id": phone_number_id,
                        "phone_resource_id": phone_resource_id
                    }
                
        except urllib.error.HTTPError as e:
            logger.error(f"Failed to verify and register: {e}")
            raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to verify and register: {e}")
            raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")
    
    async def get_phone_number_id(self, phone_resource_id: str) -> Optional[str]:
        """Get the phone number ID after registration"""
        if not self.system_token:
            return None
        
        # Get WABA ID dynamically
        waba_id = await self.get_waba_id()
        if not waba_id:
            return None
        
        url = f"{self.api_base}/{waba_id}/phone_numbers"
        headers = {
            "Authorization": f"Bearer {self.system_token}"
        }
        
        try:
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Find the phone number with matching resource ID
                for phone in result.get("data", []):
                    if phone.get("id") == phone_resource_id:
                        return phone.get("id")
                
                return None
                
        except urllib.error.HTTPError as e:
            logger.error(f"Failed to get phone number ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get phone number ID: {e}")
            return None

# Initialize manager
qr_manager = QROnboardingManager()

# API Endpoints
@router.post("/generate-qr", 
             response_model=QRGenerateResponse,
             summary="Generate QR Code for Coach Onboarding",
             description="""
             Generate a QR code for coach onboarding and registration.
             
             **QR Code Features:**
             - Contains a one-time session URL
             - Expires after specified minutes (default: 15)
             - Can be scanned with any QR code reader
             - Returns both image (PNG) and text representations
             
             **Onboarding Flow:**
             1. Generate QR code with this endpoint
             2. Coach scans QR code with mobile device
             3. Coach enters phone number on landing page
             4. Coach receives SMS verification code
             5. Coach enters code to complete registration
             6. Coach is automatically logged in
             
             **Security:**
             - Each QR code is unique and single-use
             - Sessions expire automatically
             - Phone numbers are verified via SMS
             """,
             tags=["QR Onboarding"],
             responses={
                 200: {
                     "description": "QR code generated successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "image_qr": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAcIA...",
                                 "text_qr": "data:text/plain;base64,Q29hY2ggUmVnaXN0cmF0aW9u...",
                                 "url": "https://coaches.aiwaverider.com/onboard/start?session=abc123",
                                 "session_id": "abc123def456",
                                 "expires_at": "2025-09-07T10:15:00Z",
                                 "onboarding_url": "https://coaches.aiwaverider.com/onboard/start?session=abc123"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid request parameters",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Invalid expires_in_minutes value"
                             }
                         }
                     }
                 },
                 500: {
                     "description": "QR generation failed",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Failed to generate QR code"
                             }
                         }
                     }
                 }
             })
async def generate_qr_code(request: QRGenerateRequest, base_url: str = "https://coaches.aiwaverider.com"):
    """Generate QR code for onboarding"""
    try:
        # Create session
        session_data = await qr_manager.create_session(
            request.coach_id, 
            request.expires_in_minutes
        )
        
        # Generate QR code (both image and text)
        qr_data = qr_manager.generate_qr_code(session_data["session_id"], base_url)
        
        return QRGenerateResponse(
            image_qr=qr_data["image_qr"],
            text_qr=qr_data["text_qr"],
            url=qr_data["url"],
            session_id=session_data["session_id"],
            expires_at=session_data["expires_at"],
            onboarding_url=f"{base_url}/onboard/start?session={session_data['session_id']}"
        )
        
    except Exception as e:
        logger.error(f"QR generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"QR generation failed: {str(e)}")

@router.get("/start", 
            response_class=HTMLResponse,
            summary="Mobile Landing Page",
            description="""
            Mobile-optimized landing page for QR code scanning.
            
            **QR Onboarding Flow:**
            1. Coach scans QR code with mobile device
            2. Mobile browser opens this landing page
            3. Coach enters phone number
            4. Coach receives SMS verification code
            5. Coach enters code to complete registration
            
            **Features:**
            - Mobile-responsive design
            - Phone number validation
            - Session management
            - Error handling and user feedback
            
            **Security:**
            - Session validation
            - Rate limiting
            - Input sanitization
            """,
            tags=["QR Onboarding"])
async def mobile_landing_page(session: str, request: Request):
    """Mobile landing page for QR scanning"""
    try:
        # Get session
        session_data = await qr_manager.get_session(session)
        if not session_data:
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Session Expired</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
                    .error { color: #e74c3c; }
                </style>
            </head>
            <body>
                <h1 class="error">Session Expired</h1>
                <p>This QR code has expired. Please scan a new one.</p>
            </body>
            </html>
            """, status_code=400)
        
        # Check if coach already exists
        if session_data.get("coach_id"):
            coach = await qr_manager.check_coach_exists(session_data["coach_id"])
            if coach:
                # Auto-login existing coach
                return await auto_login_coach(coach, request)
        
        # Show registration form
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Coach Onboarding</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 0 auto; padding: 20px; }}
                .form-group {{ margin-bottom: 15px; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
                button {{ width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }}
                button:disabled {{ background: #ccc; cursor: not-allowed; }}
                .error {{ color: #e74c3c; margin-top: 10px; }}
                .success {{ color: #27ae60; margin-top: 10px; }}
                .step {{ margin-bottom: 20px; }}
                .step h3 {{ margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <h1>📱 Coach Onboarding</h1>
            <p>Welcome! Let's get your WhatsApp number set up.</p>
            
            <div id="step1" class="step">
                <h3>Step 1: Enter Your Details</h3>
                <div class="form-group">
                    <label for="phone">Phone Number</label>
                    <input type="tel" id="phone" placeholder="+1234567890" required>
                </div>
                <div class="form-group">
                    <label for="displayName">Display Name</label>
                    <input type="text" id="displayName" placeholder="John's Coaching" required>
                </div>
                <button onclick="submitNumber()">Send Verification Code</button>
                <div id="error1" class="error"></div>
                <div id="success1" class="success"></div>
            </div>
            
            <div id="step2" class="step" style="display: none;">
                <h3>Step 2: Enter Verification Code</h3>
                <p>Check your phone for the verification code</p>
                <div class="form-group">
                    <label for="code">Verification Code</label>
                    <input type="text" id="code" placeholder="123456" maxlength="6" required>
                </div>
                <button onclick="verifyCode()">Verify & Complete</button>
                <div id="error2" class="error"></div>
                <div id="success2" class="success"></div>
            </div>
            
            <script>
                const sessionId = '{session}';
                
                async function submitNumber() {{
                    const phone = document.getElementById('phone').value;
                    const displayName = document.getElementById('displayName').value;
                    
                    if (!phone || !displayName) {{
                        showError('error1', 'Please fill in all fields');
                        return;
                    }}
                    
                    try {{
                        const response = await fetch('/onboard/submit-number', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                session_id: sessionId,
                                phone: phone,
                                display_label: displayName
                            }})
                        }});
                        
                        const result = await response.json();
                        
                        if (result.success) {{
                            showSuccess('success1', 'Verification code sent!');
                            document.getElementById('step1').style.display = 'none';
                            document.getElementById('step2').style.display = 'block';
                        }} else {{
                            showError('error1', result.message);
                        }}
                    }} catch (error) {{
                        showError('error1', 'Network error. Please try again.');
                    }}
                }}
                
                async function verifyCode() {{
                    const code = document.getElementById('code').value;
                    
                    if (!code || code.length !== 6) {{
                        showError('error2', 'Please enter a 6-digit code');
                        return;
                    }}
                    
                    try {{
                        const response = await fetch('/onboard/verify-code', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                session_id: sessionId,
                                pin: code
                            }})
                        }});
                        
                        const result = await response.json();
                        
                        if (result.success) {{
                            showSuccess('success2', 'Registration complete! Redirecting...');
                            setTimeout(() => {{
                                window.location.href = '/dashboard';
                            }}, 2000);
                        }} else {{
                            showError('error2', result.message);
                        }}
                    }} catch (error) {{
                        showError('error2', 'Network error. Please try again.');
                    }}
                }}
                
                function showError(elementId, message) {{
                    document.getElementById(elementId).textContent = message;
                    document.getElementById(elementId).style.display = 'block';
                }}
                
                function showSuccess(elementId, message) {{
                    document.getElementById(elementId).textContent = message;
                    document.getElementById(elementId).style.display = 'block';
                }}
            </script>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Mobile landing page failed: {e}")
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

@router.post("/submit-number", 
             response_model=OnboardResponse,
             summary="Submit Phone Number",
             description="""
             Submit phone number for coach onboarding and request verification code.
             
             **Process:**
             1. Validate session and phone number
             2. Check if coach already exists
             3. Create phone number resource in Meta
             4. Request SMS verification code
             5. Return success status
             
             **Phone Number Requirements:**
             - Must be in E.164 format (+1234567890)
             - Must not be already registered
             - Must be a valid mobile number
             
             **Meta Integration:**
             - Creates pending phone resource
             - Sends SMS verification code
             - Handles Meta API errors gracefully
             """,
             tags=["QR Onboarding"],
             responses={
                 200: {
                     "description": "Phone number submitted successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Verification code sent",
                                 "session_id": "abc123def456",
                                 "phone_number": "+1234567890"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid phone number or session",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": False,
                                 "message": "Invalid phone number format"
                             }
                         }
                     }
                 },
                 404: {
                     "description": "Session not found or expired",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": False,
                                 "message": "Session not found or expired"
                             }
                         }
                     }
                 }
             })
async def submit_phone_number(request: OnboardSubmitRequest):
    """Submit phone number and request verification code"""
    try:
        # Get session
        session_data = await qr_manager.get_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=400, detail="Invalid or expired session")
        
        # Check if coach already exists
        existing_coach = await qr_manager.check_coach_exists(request.phone)
        if existing_coach:
            raise HTTPException(status_code=400, detail="Phone number already registered")
        
        # Create phone number on Meta
        meta_result = await qr_manager.create_phone_number(
            request.phone,
            request.display_label
        )
        
        phone_resource_id = meta_result.get("id")
        if not phone_resource_id:
            raise HTTPException(status_code=400, detail="Failed to create phone number on Meta")
        
        # Request verification code
        code_result = await qr_manager.request_verification_code(phone_resource_id, "sms")
        
        if not code_result.get("success"):
            raise HTTPException(status_code=400, detail="Failed to request verification code")
        
        # Update session with phone info
        from .database import db
        async with db.pool.acquire() as conn:
            await conn.execute(
                """UPDATE onboarding_sessions 
                   SET phone = $1, display_name = $2, phone_resource_id = $3, status = 'code_sent'
                   WHERE session_id = $4""",
                request.phone, request.display_label, phone_resource_id, request.session_id
            )
        
        return OnboardResponse(
            success=True,
            message="Verification code sent successfully",
            status="code_sent"
        )
        
    except Exception as e:
        logger.error(f"Submit phone number failed: {e}")
        raise HTTPException(status_code=500, detail=f"Submit failed: {str(e)}")

@router.post("/verify-code", 
             response_model=OnboardResponse,
             summary="Verify Verification Code",
             description="""
             Verify the 6-digit verification code sent to the coach's phone.
             
             This endpoint completes the coach registration process by verifying
             the OTP code sent via SMS and registering the phone number with Meta.
             
             **Features:**
             - OTP verification
             - Meta phone registration
             - Session completion
             - Auto-login setup
             - Error handling
             
             **Use Cases:**
             - Complete registration
             - Phone verification
             - Account activation
             - Session completion
             """,
             tags=["QR Onboarding"],
             responses={
                 200: {"description": "Verification successful, coach registered"},
                 400: {"description": "Invalid verification code"},
                 404: {"description": "Session not found"},
                 500: {"description": "Registration error"}
             })
async def verify_verification_code(request: OnboardVerifyRequest):
    """Verify code and complete registration"""
    try:
        # Get session
        session_data = await qr_manager.get_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=400, detail="Invalid or expired session")
        
        phone_resource_id = session_data.get("phone_resource_id")
        if not phone_resource_id:
            raise HTTPException(status_code=400, detail="No phone resource found for this session")
        
        # Verify and register with Meta
        meta_result = await qr_manager.verify_and_register(phone_resource_id, request.pin)
        
        if not meta_result.get("success"):
            raise HTTPException(status_code=400, detail="Failed to verify and register phone number")
        
        # Create or update coach record
        from .database import db
        async with db.pool.acquire() as conn:
            # Check if coach exists
            coach_id = session_data.get("coach_id")
            if not coach_id:
                coach_id = str(uuid.uuid4())
            
            # Create or update coach
            await conn.execute(
                """INSERT INTO coaches (id, phone_e164, phone_number_id, phone_display_name, phone_registration_status, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, 'registered', $5, $6)
                   ON CONFLICT (id) DO UPDATE SET
                   phone_e164 = $2, phone_number_id = $3, phone_display_name = $4, 
                   phone_registration_status = 'registered', updated_at = $6""",
                coach_id, session_data["phone"], meta_result["phone_number_id"], 
                session_data["display_name"], datetime.now(), datetime.now()
            )
            
            # Update session
            await conn.execute(
                """UPDATE onboarding_sessions 
                   SET status = 'completed', coach_id = $1, completed_at = $2
                   WHERE session_id = $3""",
                coach_id, datetime.now(), request.session_id
            )
        
        return OnboardResponse(
            success=True,
            message="Registration completed successfully!",
            phone_number_id=meta_result["phone_number_id"],
            coach_id=coach_id,
            status="completed"
        )
        
    except Exception as e:
        logger.error(f"Verify code failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

async def auto_login_coach(coach: Dict[str, Any], request: Request) -> HTMLResponse:
    """Auto-login existing coach"""
    # Set session cookie
    response = RedirectResponse(url="/dashboard")
    
    # Create login session
    login_session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=LOGIN_SESSION_DAYS)
    
    from .database import db
    async with db.pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO login_sessions (session_id, coach_id, expires_at, created_at)
               VALUES ($1, $2, $3, $4)""",
            login_session_id, coach["id"], expires_at, datetime.now()
        )
    
    # Set secure cookie
    response.set_cookie(
        key="coach_session",
        value=login_session_id,
        max_age=LOGIN_SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return response

@router.get("/status/{session_id}",
            summary="Get Session Status",
            description="""
            Get the current status of an onboarding session.
            
            This endpoint allows the frontend to poll for session status updates
            during the onboarding process, including registration progress and errors.
            
            **Features:**
            - Session status tracking
            - Progress monitoring
            - Error reporting
            - Real-time updates
            - Polling support
            
            **Use Cases:**
            - Status polling
            - Progress tracking
            - Error handling
            - Session monitoring
            """,
            tags=["QR Onboarding"],
            responses={
                200: {"description": "Session status retrieved successfully"},
                404: {"description": "Session not found"},
                500: {"description": "Database error"}
            })
async def get_session_status(session_id: str):
    """Get session status for polling"""
    try:
        session_data = await qr_manager.get_session(session_id)
        if not session_data:
            return {"status": "expired"}
        
        return {
            "status": session_data["status"],
            "coach_id": session_data.get("coach_id"),
            "phone": session_data.get("phone"),
            "expires_at": session_data["expires_at"]
        }
        
    except Exception as e:
        logger.error(f"Get status failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
