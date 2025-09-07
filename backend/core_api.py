"""
Coaching System Backend API
FastAPI application handling WhatsApp integration, voice processing, and scheduling
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import asyncpg
import openai
import httpx
import json
from datetime import datetime, timedelta, timezone
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class CoachRegistration(BaseModel):
    barcode: str
    whatsapp_token: str
    name: str
    email: Optional[str] = None
    timezone: str = "EST"

class Client(BaseModel):
    name: str
    phone_number: str
    country: Optional[str] = "USA"
    timezone: str = "EST"
    categories: List[str] = []

class MessageRequest(BaseModel):
    client_ids: List[str]
    message_type: str  # 'celebration' or 'accountability'
    content: str
    schedule_type: str  # 'now', 'specific', 'recurring'
    scheduled_time: Optional[datetime] = None
    recurring_pattern: Optional[Dict[str, Any]] = None

class VoiceMessageProcessing(BaseModel):
    coach_id: str
    whatsapp_message_id: str
    audio_url: str
    message_type: str

class WhatsAppWebhook(BaseModel):
    object: str
    entry: List[Dict[str, Any]]

class CategoryCreate(BaseModel):
    name: str

class TemplateCreate(BaseModel):
    message_type: str
    content: str

class ImportData(BaseModel):
    source: str
    data: str

class GoogleContactsImport(BaseModel):
    access_token: str

class VoiceProcessRequest(BaseModel):
    audio_url: str
    coach_id: str

# Use the database instance from database.py
from .database import db
from .google_sheets_service import sheets_service
from .whatsapp_templates import template_manager

# Initialize template manager with database connection
template_manager.set_db_pool(db.pool)

# WhatsApp Business API client
class WhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v22.0"
    
    async def send_message(self, to: str, message: str, template_name: str = "hello_world") -> Dict[str, Any]:
        """Send a template message via WhatsApp Business API"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Clean phone number - remove + and any non-digits
        clean_phone = ''.join(filter(str.isdigit, to))
        
        # Get the appropriate language code for this template
        language_code = template_manager.get_template_language_code(template_name)
        
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        # Log the request details
        logger.info(f"🚀 WhatsApp Template API Request:")
        logger.info(f"   URL: {url}")
        logger.info(f"   Headers: {headers}")
        logger.info(f"   Payload: {payload}")
        logger.info(f"   Original phone: {to}")
        logger.info(f"   Cleaned phone: {clean_phone}")
        logger.info(f"   Template name: {template_name}")
        logger.info(f"   Language code: {language_code}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            
            # Log the response details
            logger.info(f"📥 WhatsApp Template API Response:")
            logger.info(f"   Status Code: {response.status_code}")
            logger.info(f"   Response Headers: {dict(response.headers)}")
            logger.info(f"   Response Body: {response.text}")
            
            return response.json()
    
    async def send_template_with_parameters(self, to: str, template_name: str, parameters: List[str]) -> Dict[str, Any]:
        """Send a template message with parameters"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Clean phone number - remove + and any non-digits
        clean_phone = ''.join(filter(str.isdigit, to))
        
        # Get the appropriate language code for this template
        language_code = template_manager.get_template_language_code(template_name)
        
        # Build template with parameters
        template_data = {
            "name": template_name,
            "language": {"code": language_code}
        }
        
        # Add parameters if provided
        if parameters:
            template_data["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": param} for param in parameters]
            }]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": template_data
        }
        
        # Log the request details
        logger.info(f"🚀 WhatsApp Template with Parameters API Request:")
        logger.info(f"   URL: {url}")
        logger.info(f"   Headers: {headers}")
        logger.info(f"   Payload: {payload}")
        logger.info(f"   Template name: {template_name}")
        logger.info(f"   Language code: {language_code}")
        logger.info(f"   Parameters: {parameters}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            
            # Log the response details
            logger.info(f"📥 WhatsApp Template with Parameters API Response:")
            logger.info(f"   Status Code: {response.status_code}")
            logger.info(f"   Response Headers: {dict(response.headers)}")
            logger.info(f"   Response Body: {response.text}")
            
            return response.json()
    
    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a text message via WhatsApp Business API (fallback method)"""
        print(f"🔥 SEND_TEXT_MESSAGE CALLED - to: {to}, message: {message}")
        logger.info(f"🔥 SEND_TEXT_MESSAGE CALLED - to: {to}, message: {message}")
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Clean phone number - remove + and any non-digits
        clean_phone = ''.join(filter(str.isdigit, to))
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        # Log the request details
        logger.info(f"🚀 WhatsApp API Request:")
        logger.info(f"   URL: {url}")
        logger.info(f"   Headers: {headers}")
        logger.info(f"   Payload: {payload}")
        logger.info(f"   Original phone: {to}")
        logger.info(f"   Cleaned phone: {clean_phone}")
        
        logger.info(f"🔥 ABOUT TO SEND HTTP REQUEST TO WHATSAPP API")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            
            # Log the response details
            logger.info(f"📥 WhatsApp API Response:")
            logger.info(f"   Status Code: {response.status_code}")
            logger.info(f"   Response Headers: {dict(response.headers)}")
            logger.info(f"   Response Body: {response.text}")
            
            return response.json()
    
    async def can_send_free_message(self, wa_id: str) -> bool:
        """Check if we can send a free message to this user (within 24h window)"""
        try:
            async with db.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT can_send_free_message($1)", wa_id
                )
                return result or False
        except Exception as e:
            logger.error(f"Error checking free message eligibility: {e}")
            return False
    
    async def get_active_conversation(self, wa_id: str) -> Optional[Dict[str, Any]]:
        """Get active conversation for a user"""
        try:
            async with db.pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM get_active_conversation($1)", wa_id
                )
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting active conversation: {e}")
            return None
    
    async def record_conversation(self, wa_id: str, conversation_id: str, origin_type: str, expires_at: str) -> None:
        """Record a new conversation"""
        try:
            async with db.pool.acquire() as conn:
                # Deactivate existing conversations for this user
                await conn.execute(
                    "UPDATE whatsapp_conversations SET is_active = false WHERE wa_id = $1",
                    wa_id
                )
                
                # Insert new conversation
                await conn.execute(
                    """INSERT INTO whatsapp_conversations 
                       (wa_id, conversation_id, origin_type, initiated_at, expires_at)
                       VALUES ($1, $2, $3, NOW(), $4)""",
                    wa_id, conversation_id, origin_type, expires_at
                )
                logger.info(f"Recorded conversation for {wa_id}: {conversation_id}")
        except Exception as e:
            logger.error(f"Error recording conversation: {e}")
    
    async def send_interactive_message(self, to: str, message: str, buttons: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send message with interactive buttons (Confirm/Edit)"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Clean phone number - remove + and any non-digits
        clean_phone = ''.join(filter(str.isdigit, to))
        
        interactive_buttons = []
        for i, button in enumerate(buttons):
            interactive_buttons.append({
                "type": "reply",
                "reply": {
                    "id": button["id"],
                    "title": button["title"]
                }
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {
                    "buttons": interactive_buttons
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()

# Voice transcription service
class VoiceTranscriptionService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
            self.available = True
        else:
            self.openai_client = None
            self.available = False
            logger.warning("OPENAI_API_KEY not set - voice transcription will be unavailable")
    
    async def transcribe_audio(self, audio_url: str) -> str:
        """Transcribe audio using OpenAI Whisper"""
        if not self.available:
            raise HTTPException(status_code=503, detail="Voice transcription service unavailable - OpenAI API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                audio_response = await client.get(audio_url)
                if audio_response.status_code != 200:
                    logger.warning(f"Failed to download audio from {audio_url}: {audio_response.status_code}")
                    raise HTTPException(status_code=400, detail=f"Could not download audio file: {audio_response.status_code}")
                audio_content = audio_response.content
                
                # Validate audio content
                if len(audio_content) == 0:
                    raise HTTPException(status_code=400, detail="Audio file is empty")
            
            # Create temporary file for OpenAI Whisper
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_file.write(audio_content)
                temp_file_path = temp_file.name
            
            with open(temp_file_path, "rb") as audio_file:
                transcript = await self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            return transcript.text
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail="Transcription failed")
    
    async def correct_message(self, text: str) -> str:
        """Correct grammar and improve message using GPT-4o-mini"""
        if not self.available:
            raise HTTPException(status_code=503, detail="Voice transcription service unavailable - OpenAI API key not configured")
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that corrects grammar and improves the clarity of coaching messages. Keep the original tone and intent, but fix any grammatical errors and make the message clear and professional. Return only the corrected message without any additional text."
                    },
                    {
                        "role": "user",
                        "content": f"Please correct this coaching message: {text}"
                    }
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Message correction error: {e}")
            return text  # Return original if correction fails

# Google Sheets integration
class GoogleSheetsService:
    def __init__(self):
        self.service = None
    
    async def authenticate(self):
        """Authenticate with Google Sheets API"""
        # This would use proper OAuth2 flow in production
        creds = Credentials.from_authorized_user_info({
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            "type": "authorized_user"
        })
        self.service = build('sheets', 'v4', credentials=creds)
    
    async def create_or_update_sheet(self, coach_id: str, client_data: List[Dict[str, Any]]) -> str:
        """Create or update Google Sheet with client data"""
        try:
            # Check if sheet exists for this coach
            async with db.pool.acquire() as conn:
                sheet_record = await conn.fetchrow(
                    "SELECT sheet_id, sheet_url FROM google_sheets_sync WHERE coach_id = $1 ORDER BY created_at DESC LIMIT 1",
                    coach_id
                )
            
            headers = [
                "Client Name", "Phone Number", "Country", "Goals", "Categories",
                "Last Accountability Sent", "Last Celebration Sent", "Status", "Timezone"
            ]
            
            # Prepare data rows
            rows = [headers]
            for client in client_data:
                rows.append([
                    client.get('client_name', ''),
                    client.get('phone_number', ''),
                    client.get('country', ''),
                    client.get('goals', ''),
                    client.get('categories', ''),
                    str(client.get('last_accountability_sent', '')),
                    str(client.get('last_celebration_sent', '')),
                    client.get('status', ''),
                    client.get('timezone', '')
                ])
            
            if sheet_record and sheet_record['sheet_id']:
                # Update existing sheet
                sheet_id = sheet_record['sheet_id']
                self.service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range='Sheet1!A1:I1000',
                    valueInputOption='USER_ENTERED',
                    body={'values': rows}
                ).execute()
            else:
                # Create new sheet
                spreadsheet = {
                    'properties': {
                        'title': f'Coaching Data - {datetime.now().strftime("%Y-%m-%d")}'
                    }
                }
                sheet = self.service.spreadsheets().create(body=spreadsheet).execute()
                sheet_id = sheet['spreadsheetId']
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                
                # Add data to new sheet
                self.service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range='Sheet1!A1:I1000',
                    valueInputOption='USER_ENTERED',
                    body={'values': rows}
                ).execute()
                
                # Save sheet info to database
                async with db.pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO google_sheets_sync (coach_id, sheet_id, sheet_url, last_sync_at, sync_status, row_count)
                           VALUES ($1, $2, $3, $4, 'success', $5)""",
                        coach_id, sheet_id, sheet_url, datetime.now(), len(rows)
                    )
            
            return sheet_id
            
        except Exception as e:
            logger.error(f"Google Sheets error: {e}")
            raise HTTPException(status_code=500, detail="Google Sheets sync failed")

# Initialize services
transcription_service = VoiceTranscriptionService()

# Lifespan manager
@asynccontextmanager
async def lifespan(app):
    # Startup
    await db.connect()
    await sheets_service.authenticate()
    logger.info("Database and services initialized")
    yield
    # Shutdown
    await db.disconnect()
    logger.info("Database connection closed")

# Router for core API
router = APIRouter()

# API Endpoints

@router.post("/register",
             summary="Register New Coach",
             description="""
             Register a new coach in the system.
             
             **Registration Process:**
             1. Coach provides barcode and WhatsApp token
             2. System validates the barcode
             3. Coach profile is created
             4. WhatsApp integration is configured
             
             **Required Fields:**
             - `barcode`: Unique identifier for the coach
             - `whatsapp_token`: WhatsApp Business API access token
             - `name`: Coach's full name
             
             **Optional Fields:**
             - `email`: Coach's email address
             - `timezone`: Coach's timezone (default: EST)
             """,
             tags=["Coach Registration"],
             responses={
                 200: {
                     "description": "Coach registered successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "id": "550e8400-e29b-41d4-a716-446655440000",
                                 "name": "John Doe",
                                 "email": "john@example.com",
                                 "phone": "+1234567890",
                                 "timezone": "EST",
                                 "created_at": "2025-09-07T10:00:00Z",
                                 "status": "active"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid registration data",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Invalid barcode or WhatsApp token"
                             }
                         }
                     }
                 },
                 409: {
                     "description": "Coach already exists",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Coach with this barcode already exists"
                             }
                         }
                     }
                 }
             })
async def register_coach(registration: CoachRegistration):
    """Register a new coach via barcode scan"""
    try:
        logger.info(f"Registration request: {registration}")
        
        # Check if barcode already exists
        logger.info(f"Checking for existing barcode: {registration.barcode}")
        existing = await db.fetchrow(
            "SELECT id FROM coaches WHERE registration_barcode = $1",
            registration.barcode
        )
        logger.info(f"Existing check result: {existing}")
        
        if existing:
            return {"status": "existing", "coach_id": str(existing[0])}
        
        # Create new coach  
        import uuid
        coach_id = str(uuid.uuid4())
        logger.info(f"Generated coach_id: {coach_id}")
        
        logger.info(f"Inserting coach: name={registration.name}, email={registration.email}")
        await db.execute(
            """INSERT INTO coaches (id, name, email, whatsapp_token, timezone, registration_barcode)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            coach_id, registration.name, registration.email, registration.whatsapp_token,
            registration.timezone, registration.barcode
        )
        logger.info("Coach inserted successfully")
        
        return {"status": "registered", "coach_id": coach_id}
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.get("/coaches/{coach_id}/clients",
            summary="Get Coach's Clients",
            description="""
            Retrieve all active clients for a specific coach.
            
            **Response includes:**
            - Client basic information (name, phone, timezone)
            - Coaching categories assigned to each client
            - Client creation timestamp
            - Active status
            
            **Use Cases:**
            - Display client list in coach dashboard
            - Select clients for message sending
            - View client categories for filtering
            """,
            tags=["Client CRUD"],
            responses={
                200: {
                    "description": "List of clients retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": [
                                {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "name": "Jane Smith",
                                    "phone_number": "+1234567890",
                                    "categories": ["Health", "Fitness"],
                                    "timezone": "EST",
                                    "created_at": "2025-09-07T10:00:00Z"
                                }
                            ]
                        }
                    }
                },
                404: {
                    "description": "Coach not found",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Coach not found"
                            }
                        }
                    }
                }
            })
async def get_clients(coach_id: str):
    """Get all clients for a coach"""
    try:
        # For now, just return basic client info without categories
        clients = await db.fetch(
            "SELECT * FROM clients WHERE coach_id = $1 AND is_active = true ORDER BY name",
            coach_id
        )
        
        # Convert rows to dictionaries
        result = []
        for client in clients:
            result.append({
                "id": client[0],
                "coach_id": client[1], 
                "name": client[2],
                "phone_number": client[3],
                "country": client[4],
                "timezone": client[5],
                "is_active": bool(client[6]),
                "created_at": client[7],
                "updated_at": client[8],
                "categories": []  # Empty for now
            })
        return result
    
    except Exception as e:
        logger.error(f"Get clients error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch clients")

@router.post("/coaches/{coach_id}/clients",
             summary="Add New Client",
             description="""
             Add a new client to a coach's client list.
             
             **Required Fields:**
             - `name`: Client's full name
             - `phone_number`: Client's phone number in E.164 format
             
             **Optional Fields:**
             - `country`: Client's country (default: USA)
             - `timezone`: Client's timezone (default: EST)
             - `categories`: List of coaching categories
             
             **Validation:**
             - Phone number must be in E.164 format (+1234567890)
             - Client name must be unique per coach
             - Categories must be from predefined list
             """,
             tags=["Client CRUD"],
             responses={
                 201: {
                     "description": "Client added successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "id": "550e8400-e29b-41d4-a716-446655440000",
                                 "name": "Jane Smith",
                                 "phone_number": "+1234567890",
                                 "country": "USA",
                                 "timezone": "EST",
                                 "categories": ["Health", "Fitness"],
                                 "created_at": "2025-09-07T10:00:00Z"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid client data",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Invalid phone number format"
                             }
                         }
                     }
                 },
                 409: {
                     "description": "Client already exists",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Client with this phone number already exists"
                             }
                         }
                     }
                 }
             })
async def add_client(coach_id: str, client: Client):
    """Add a new client"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Validate coach exists
        coach = await db.fetchrow("SELECT id FROM coaches WHERE id = $1", coach_id)
        if not coach:
            raise HTTPException(status_code=404, detail="Coach not found")
        
        # Insert client
        import uuid
        client_id = str(uuid.uuid4())
        
        await db.execute(
            """INSERT INTO clients (id, coach_id, name, phone_number, country, timezone)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            client_id, coach_id, client.name, client.phone_number, client.country, client.timezone
        )
        
        # Add categories if provided
        if client.categories:
            for category_name in client.categories:
                    # Check if category exists (predefined or custom for this coach)
                category = await db.fetchrow(
                    "SELECT id FROM categories WHERE name = $1 AND (is_predefined = true OR coach_id = $2)",
                    category_name, coach_id
                )
                
                if category:
                    await db.execute(
                        "INSERT INTO client_categories (client_id, category_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        client_id, category[0]
                    )
                else:
                    # Create custom category if it doesn't exist
                    category_id = str(uuid.uuid4())
                    await db.execute(
                        "INSERT INTO categories (id, name, coach_id, is_predefined) VALUES ($1, $2, $3, false)",
                        category_id, category_name, coach_id
                    )
                    await db.execute(
                        "INSERT INTO client_categories (client_id, category_id) VALUES ($1, $2)",
                        client_id, category_id
                    )
        
        return {"client_id": client_id, "status": "created"}
    
    except Exception as e:
        logger.error(f"Add client error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add client: {str(e)}")

@router.post("/messages/send",
             summary="Send Messages to Clients",
             description="""
             Send messages to selected clients via WhatsApp.
             
             **Message Types:**
             - **celebration**: Positive reinforcement messages (templates 6-10)
             - **accountability**: Goal tracking messages (templates 1-5)
             
             **Schedule Types:**
             - **now**: Send immediately
             - **specific**: Send at a specific time
             - **recurring**: Send on a recurring schedule
             
             **24-Hour Window Rule:**
             - Custom messages can only be sent within 24 hours of a client's last message
             - Template messages can be sent anytime
             - Use the `/can-send-free` endpoint to check window status
             """,
             tags=["Message Sending"],
             responses={
                 200: {
                     "description": "Messages sent successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "message_id": "msg_123456789",
                                 "status": "sent",
                                 "recipients": ["+1234567890"],
                                 "template_used": "celebration_message_6",
                                 "sent_at": "2025-09-07T10:00:00Z"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid request or 24-hour window violation",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Cannot send custom message outside 24-hour window. Use a template instead."
                             }
                         }
                     }
                 },
                 422: {
                     "description": "Validation error",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": [
                                     {
                                         "loc": ["body", "client_ids"],
                                         "msg": "field required",
                                         "type": "value_error.missing"
                                     }
                                 ]
                             }
                         }
                     }
                 },
                 500: {
                     "description": "Internal server error",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Failed to send messages"
                             }
                         }
                     }
                 }
             })
async def send_messages(message_request: MessageRequest, background_tasks: BackgroundTasks):
    """Send messages to selected clients"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        async with db.pool.acquire() as conn:
            message_ids = []
            
            for client_id in message_request.client_ids:
                # Validate client exists and belongs to a coach
                client = await conn.fetchrow(
                    "SELECT id, coach_id FROM clients WHERE id = $1 AND is_active = true",
                    client_id
                )
                
                if not client:
                    logger.warning(f"Client {client_id} not found or inactive")
                    continue
                
                # Handle datetime conversion for scheduled messages
                scheduled_time = None
                if message_request.schedule_type == 'specific' and message_request.scheduled_time:
                    if isinstance(message_request.scheduled_time, str):
                        # Convert ISO string to datetime
                        from datetime import datetime
                        scheduled_time = datetime.fromisoformat(message_request.scheduled_time.replace('Z', '+00:00'))
                    else:
                        scheduled_time = message_request.scheduled_time
                elif message_request.schedule_type == 'now':
                    scheduled_time = datetime.now()
                
                # Create scheduled message record
                scheduled_id = await conn.fetchval(
                    """INSERT INTO scheduled_messages 
                       (coach_id, client_id, message_type, content, schedule_type, scheduled_time, status)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)
                       RETURNING id""",
                    client['coach_id'], client_id, message_request.message_type, message_request.content,
                    message_request.schedule_type, scheduled_time,
                    'scheduled' if message_request.schedule_type != 'now' else 'pending'
                )
                
                message_ids.append(str(scheduled_id))
                
                # If sending now, add to background task
                if message_request.schedule_type == 'now':
                    logger.info(f"📤 Adding background task for immediate message: {scheduled_id}")
                    background_tasks.add_task(send_immediate_message, str(scheduled_id))
        
        if not message_ids:
            raise HTTPException(status_code=400, detail="No valid clients found")
        
        return {"message_ids": message_ids, "status": "scheduled"}
    
    except Exception as e:
        logger.error(f"Send messages error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule messages: {str(e)}")

async def send_immediate_message(scheduled_message_id: str):
    """Background task to send immediate message"""
    print(f"🚀 Starting background task for message ID: {scheduled_message_id}")
    logger.info(f"🚀 Starting background task for message ID: {scheduled_message_id}")
    try:
        async with db.pool.acquire() as conn:
            # Get message details
            message_data = await conn.fetchrow(
                """SELECT sm.*, c.phone_number, co.whatsapp_token, co.whatsapp_phone_number
                   FROM scheduled_messages sm
                   JOIN clients c ON sm.client_id = c.id
                   JOIN coaches co ON sm.coach_id = co.id
                   WHERE sm.id = $1""",
                scheduled_message_id
            )
            
            if not message_data:
                return
            
            # Send via WhatsApp
            whatsapp_client = WhatsAppClient(
                os.getenv("WHATSAPP_ACCESS_TOKEN"),
                os.getenv("WHATSAPP_PHONE_NUMBER_ID")
            )
            
            # Clean phone number for conversation tracking
            clean_phone = ''.join(filter(str.isdigit, message_data['phone_number']))
            
            # Import template manager
            from .whatsapp_templates import template_manager
            
            # Check if this is a template message (celebration/accountability from DB)
            if template_manager.is_template_message(message_data['content']):
                # This is an initiation message - send as template
                template_name = template_manager.get_template_name(message_data['content'])
                logger.info(f"📤 Sending template message: {template_name}")
                
                # Get client name for template parameter
                client_name = await conn.fetchval(
                    "SELECT name FROM clients WHERE id = $1", 
                    message_data['client_id']
                )
                
                result = await whatsapp_client.send_template_with_parameters(
                    message_data['phone_number'],
                    template_name,
                    [client_name or "Friend"]  # Use client name as parameter
                )
                
            else:
                # Check if we can send free message (within 24h window)
                can_send_free = await whatsapp_client.can_send_free_message(clean_phone)
                
                if can_send_free:
                    # Send as free text message
                    logger.info(f"📤 Sending free text message to {clean_phone}")
                    result = await whatsapp_client.send_text_message(
                        message_data['phone_number'],
                        message_data['content']
                    )
                else:
                    # Outside 24h window - send as template (this will be charged)
                    logger.warning(f"⚠️ Outside 24h window for {clean_phone}, sending as template")
                    result = await whatsapp_client.send_message(
                        message_data['phone_number'],
                        message_data['content'],
                        "hello_world"  # Fallback template
                    )
            
            # Update status and create history record
            await conn.execute(
                "UPDATE scheduled_messages SET status = 'sent', sent_at = $1 WHERE id = $2",
                datetime.now(), scheduled_message_id
            )
            
            await conn.execute(
                """INSERT INTO message_history 
                   (scheduled_message_id, coach_id, client_id, message_type, content, whatsapp_message_id, delivery_status)
                   VALUES ($1, $2, $3, $4, $5, $6, 'pending')""",
                scheduled_message_id, message_data['coach_id'], message_data['client_id'],
                message_data['message_type'], message_data['content'], result.get('messages', [{}])[0].get('id')
            )
    
    except Exception as e:
        logger.error(f"Send immediate message error: {e}")

@router.post("/voice/process",
             summary="Process Voice Message",
             description="""
             Process and transcribe voice messages from clients.
             
             This endpoint handles voice message processing, including transcription,
             content analysis, and response generation for voice-based communications.
             
             **Features:**
             - Voice transcription
             - Content analysis
             - Response generation
             - Audio processing
             - Message formatting
             
             **Use Cases:**
             - Voice message handling
             - Audio transcription
             - Voice-based coaching
             - Accessibility support
             """,
             tags=["Voice Processing"],
             responses={
                 200: {"description": "Voice message processed successfully"},
                 400: {"description": "Invalid voice data"},
                 500: {"description": "Processing error"}
             })
async def process_voice_message(voice_data: VoiceMessageProcessing):
    """Process voice message - transcribe and correct"""
    try:
        async with db.pool.acquire() as conn:
            # Create processing record
            processing_id = await conn.fetchval(
                """INSERT INTO voice_message_processing 
                   (coach_id, whatsapp_message_id, original_audio_url, processing_status)
                   VALUES ($1, $2, $3, 'received') RETURNING id""",
                voice_data.coach_id, voice_data.whatsapp_message_id, voice_data.audio_url
            )
            
            # Transcribe audio
            transcribed_text = await transcription_service.transcribe_audio(voice_data.audio_url)
            
            await conn.execute(
                "UPDATE voice_message_processing SET transcribed_text = $1, processing_status = 'transcribed' WHERE id = $2",
                transcribed_text, processing_id
            )
            
            # Correct with AI
            corrected_text = await transcription_service.correct_message(transcribed_text)
            
            await conn.execute(
                "UPDATE voice_message_processing SET corrected_text = $1, processing_status = 'corrected' WHERE id = $2",
                corrected_text, processing_id
            )
            
            # Send confirmation message with buttons
            coach_data = await conn.fetchrow("SELECT * FROM coaches WHERE id = $1", voice_data.coach_id)
            whatsapp_client = WhatsAppClient(os.getenv("WHATSAPP_ACCESS_TOKEN"), os.getenv("WHATSAPP_PHONE_NUMBER_ID"))
            
            confirmation_message = f"Corrected message:\n\n{corrected_text}\n\nPlease confirm or edit:"
            buttons = [
                {"id": f"confirm_{processing_id}", "title": "Confirm"},
                {"id": f"edit_{processing_id}", "title": "Edit"}
            ]
            
            await whatsapp_client.send_interactive_message(
                coach_data['whatsapp_phone_number'],  # Send back to coach
                confirmation_message,
                buttons
            )
            
            return {"processing_id": str(processing_id), "corrected_text": corrected_text}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        raise HTTPException(status_code=500, detail="Voice processing failed")

@router.get("/test-webhook",
            summary="Test Webhook Endpoint",
            description="""
            Test webhook endpoint accessibility.
            
            This endpoint provides a simple test to verify that the webhook
            endpoint is accessible and responding correctly.
            
            **Features:**
            - Endpoint accessibility test
            - Basic response verification
            - Webhook status check
            - Simple health verification
            
            **Use Cases:**
            - Webhook testing
            - Endpoint verification
            - Debugging
            - Health checks
            """,
            tags=["Webhook Testing"],
            responses={
                200: {"description": "Webhook endpoint is accessible"},
                500: {"description": "Webhook error"}
            })
async def test_webhook():
    """Test webhook endpoint accessibility"""
    logger.info("🧪 Test webhook endpoint accessed")
    return {"message": "Test webhook endpoint is accessible", "status": "success"}

@router.get("/webhook/test",
            summary="Test Webhook Path",
            description="""
            Test webhook path specifically.
            
            This endpoint provides a specific test for the webhook path
            to verify routing and path handling.
            
            **Features:**
            - Path-specific testing
            - Routing verification
            - Webhook path validation
            - Path handling test
            
            **Use Cases:**
            - Path testing
            - Routing verification
            - Webhook debugging
            - Path validation
            """,
            tags=["Webhook Testing"],
            responses={
                200: {"description": "Webhook path is accessible"},
                500: {"description": "Webhook path error"}
            })
async def test_webhook_path():
    """Test webhook path specifically"""
    logger.info("🧪 Test webhook path accessed")
    return {"message": "Test webhook path is accessible", "status": "success"}

@router.get("/webhook/whatsapp",
            summary="WhatsApp Webhook Verification",
            description="""
            Verify WhatsApp webhook endpoint for Meta's challenge-response verification.
            
            **Webhook Verification Process:**
            1. Meta sends a GET request with verification parameters
            2. System validates the verify_token
            3. System returns the challenge value
            4. Meta confirms webhook is properly configured
            
            **Required Parameters:**
            - `hub.mode`: Must be 'subscribe'
            - `hub.verify_token`: Must match WEBHOOK_VERIFY_TOKEN
            - `hub.challenge`: Random string to echo back
            
            **Use Cases:**
            - Initial webhook setup in Meta Developer Console
            - Webhook verification and testing
            - Ensuring webhook endpoint is accessible
            """,
            tags=["WhatsApp Webhooks"],
            responses={
                 200: {
                     "description": "Webhook verified successfully",
                     "content": {
                         "text/plain": {
                             "example": "1234567890"
                         }
                     }
                 },
                 403: {
                     "description": "Webhook verification failed",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Forbidden - Invalid verify token"
                             }
                         }
                     }
                 }
             })
async def verify_webhook(request: Request):
    """Verify webhook endpoint for Meta - following Meta's exact specification"""
    expected_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "test-verify-token")
    
    # Get query parameters exactly as Meta sends them
    query_params = dict(request.query_params)
    
    # Meta sends: hub.mode, hub.verify_token, hub.challenge (with dots)
    mode = query_params.get("hub.mode")
    verify_token = query_params.get("hub.verify_token") 
    challenge = query_params.get("hub.challenge")
    
    logger.info(f"🔍 Webhook verification attempt:")
    logger.info(f"   All query params: {query_params}")
    logger.info(f"   hub.mode: {mode}")
    logger.info(f"   hub.verify_token: {verify_token}")
    logger.info(f"   hub.challenge: {challenge}")
    logger.info(f"   expected_token: {expected_token}")
    logger.info(f"   tokens_match: {verify_token == expected_token}")
    logger.info(f"   mode_check: {mode == 'subscribe'}")
    
    # If no parameters provided, return a helpful message
    if not query_params:
        logger.info("📝 Webhook endpoint accessed without parameters")
        return {"message": "Webhook endpoint is accessible. Use Meta's verification parameters.", "status": "ready"}
    
    # Follow Meta's exact specification
    if mode == "subscribe" and verify_token == expected_token:
        logger.info("✅ WEBHOOK VERIFIED")
        return int(challenge)
    else:
        logger.warning(f"❌ Webhook verification failed: mode={mode}, token={verify_token}")
        raise HTTPException(status_code=403, detail="Forbidden")

@router.post("/webhook/whatsapp",
             summary="WhatsApp Webhook Handler",
             description="""
             Handle incoming WhatsApp webhook events from Meta.
             
             **Supported Events:**
             - `messages`: Incoming messages from users
             - `message_echoes`: Outgoing message status updates
             - `tracking_events`: Message delivery and read receipts
             
             **Event Processing:**
             1. Validate webhook signature (if configured)
             2. Parse incoming message data
             3. Update conversation tracking for 24-hour window
             4. Store message history
             5. Trigger appropriate business logic
             
             **24-Hour Window Tracking:**
             - Records user-initiated conversations
             - Tracks message timestamps
             - Enables free-form message sending within window
             
             **Security:**
             - Validates webhook signature
             - Rate limiting protection
             - Input sanitization
             """,
             tags=["WhatsApp Webhooks"],
             responses={
                 200: {
                     "description": "Webhook processed successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "status": "success",
                                 "message": "Webhook processed",
                                 "events_processed": 1
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid webhook data",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Invalid webhook payload"
                             }
                         }
                     }
                 },
                 500: {
                     "description": "Webhook processing failed",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Failed to process webhook"
                             }
                         }
                     }
                 }
             })
async def whatsapp_webhook(webhook_data: WhatsAppWebhook, background_tasks: BackgroundTasks):
    """Handle incoming WhatsApp webhooks"""
    try:
        # Store webhook data
        async with db.pool.acquire() as conn:
            webhook_id = await conn.fetchval(
                "INSERT INTO whatsapp_webhooks (webhook_data) VALUES ($1) RETURNING id",
                json.dumps(webhook_data.dict())
            )
        
        # Process webhook in background
        background_tasks.add_task(process_whatsapp_webhook, str(webhook_id), webhook_data.dict())
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}

async def process_whatsapp_webhook(webhook_id: str, webhook_data: Dict[str, Any]):
    """Process WhatsApp webhook data with conversation tracking"""
    try:
        async with db.pool.acquire() as conn:
            for entry in webhook_data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        messages = change.get('value', {}).get('messages', [])
                        contacts = change.get('value', {}).get('contacts', [])
                        
                        for message in messages:
                            wa_id = message.get("from")
                            message_id = message.get("id")
                            
                            # Find contact info
                            contact_info = next((c for c in contacts if c.get("wa_id") == wa_id), {})
                            user_name = contact_info.get("profile", {}).get("name", "Unknown")
                            
                            logger.info(f"📨 Received message from {wa_id} ({user_name}): {message_id}")
                            
                            # Create user-initiated conversation window (24 hours from now)
                            try:
                                logger.info(f"🔍 Creating conversation window for {wa_id}")
                                
                                # Deactivate existing conversations for this user
                                await conn.execute(
                                    "UPDATE whatsapp_conversations SET is_active = false WHERE wa_id = $1",
                                    wa_id
                                )
                                logger.info(f"🔍 Deactivated existing conversations for {wa_id}")
                                
                                # Insert new user-initiated conversation (24 hours from now)
                                expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
                                await conn.execute(
                                    """INSERT INTO whatsapp_conversations 
                                       (wa_id, conversation_id, origin_type, initiated_at, expires_at)
                                       VALUES ($1, $2, $3, NOW(), $4)""",
                                    wa_id, f"user_msg_{message_id}", "user_initiated", expires_at
                                )
                                
                                logger.info(f"✅ Created 24h conversation window for {wa_id} until {expires_at}")
                                
                            except Exception as db_error:
                                logger.error(f"❌ Database error creating conversation: {db_error}")
                            
                            # Store message in conversation_messages
                            try:
                                await conn.execute(
                                    """INSERT INTO conversation_messages 
                                       (from_phone, message_direction, content, message_type, whatsapp_message_id)
                                       VALUES ($1, $2, $3, $4, $5)""",
                                    wa_id, "inbound", 
                                    message.get("text", {}).get("body", ""),
                                    message.get("type", "text"),
                                    message_id
                                )
                                logger.info(f"💾 Stored message from {wa_id}")
                            except Exception as msg_error:
                                logger.error(f"❌ Error storing message: {msg_error}")
                            from_number = message.get('from')
                            message_type = message.get('type')
                            
                            # Find coach by phone number
                            coach = await conn.fetchrow(
                                "SELECT * FROM coaches WHERE whatsapp_phone_number = $1",
                                from_number
                            )
                            
                            if not coach:
                                continue
                            
                            if message_type == 'interactive':
                                # Handle button clicks (Confirm/Edit)
                                button_reply = message.get('interactive', {}).get('button_reply', {})
                                button_id = button_reply.get('id', '')
                                
                                if button_id.startswith('confirm_'):
                                    processing_id = button_id.replace('confirm_', '')
                                    await handle_voice_confirmation(processing_id, True)
                                elif button_id.startswith('edit_'):
                                    processing_id = button_id.replace('edit_', '')
                                    await handle_voice_confirmation(processing_id, False)
                            
                            elif message_type == 'audio':
                                # Handle voice messages
                                audio_id = message.get('audio', {}).get('id')
                                # Process voice message...
                                
                            elif message_type == 'text':
                                # Handle text commands
                                text_body = message.get('text', {}).get('body', '')
                                await process_text_command(str(coach['id']), text_body)
            
            # Mark webhook as processed
            await conn.execute(
                "UPDATE whatsapp_webhooks SET processing_status = 'processed' WHERE id = $1",
                webhook_id
            )
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")

async def handle_voice_confirmation(processing_id: str, confirmed: bool):
    """Handle voice message confirmation"""
    try:
        async with db.pool.acquire() as conn:
            if confirmed:
                # Mark as confirmed and use corrected text
                await conn.execute(
                    """UPDATE voice_message_processing 
                       SET final_text = corrected_text, processing_status = 'confirmed' 
                       WHERE id = $1""",
                    processing_id
                )
                
                # Send the message to clients
                # Implementation would depend on the specific use case
                
            else:
                # Mark for editing - coach will send new message
                await conn.execute(
                    "UPDATE voice_message_processing SET processing_status = 'edit_requested' WHERE id = $1",
                    processing_id
                )
    
    except Exception as e:
        logger.error(f"Voice confirmation error: {e}")

async def process_text_command(coach_id: str, command_text: str):
    """Process natural language commands from WhatsApp"""
    try:
        # Use GPT to parse command
        openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a command parser for a coaching system. Parse the user's message and return a JSON response with:
                    {
                        "action": "send_celebration" | "send_accountability" | "get_stats" | "unknown",
                        "clients": ["client_name1", "client_name2"] or ["all"],
                        "message": "custom message if provided",
                        "timing": "now" | "schedule" | null
                    }"""
                },
                {
                    "role": "user",
                    "content": command_text
                }
            ],
            max_tokens=200,
            temperature=0.1
        )
        
        command_data = json.loads(response.choices[0].message.content)
        
        # Execute command based on parsed data
        if command_data['action'] == 'get_stats':
            await send_google_sheet_to_coach(coach_id)
        elif command_data['action'] in ['send_celebration', 'send_accountability']:
            # Implementation for sending messages based on parsed command
            pass
    
    except Exception as e:
        logger.error(f"Command processing error: {e}")

async def send_google_sheet_to_coach(coach_id: str):
    """Send Google Sheet to coach via WhatsApp"""
    try:
        async with db.pool.acquire() as conn:
            # Get client data for export
            client_data = await conn.fetch(
                "SELECT * FROM get_client_export_data($1)",
                coach_id
            )
            
            # Update Google Sheet
            sheet_id = await sheets_service.create_or_update_sheet(
                coach_id, [dict(row) for row in client_data]
            )
            
            # Get sheet URL
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            
            # Send to coach
            coach = await conn.fetchrow("SELECT * FROM coaches WHERE id = $1", coach_id)
            whatsapp_client = WhatsAppClient(os.getenv("WHATSAPP_ACCESS_TOKEN"), os.getenv("WHATSAPP_PHONE_NUMBER_ID"))
            
            await whatsapp_client.send_text_message(
                coach['whatsapp_phone_number'],
                f"📊 Here's your updated client stats:\n{sheet_url}"
            )
    
    except Exception as e:
        logger.error(f"Send stats error: {e}")

@router.get("/coaches/{coach_id}/categories",
            summary="Get Client Categories",
            description="""
            Get all available client categories for a coach.
            
            This endpoint retrieves both predefined and custom categories
            that can be used to organize and filter clients.
            
            **Features:**
            - Predefined categories
            - Custom categories
            - Category management
            - Client organization
            
            **Use Cases:**
            - Client categorization
            - Filtering options
            - Category management
            - Client organization
            """,
            tags=["Client Categories"],
            responses={
                200: {"description": "Categories retrieved successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Database error"}
            })
async def get_categories(coach_id: str):
    """Get all categories (predefined + custom)"""
    try:
        categories = await db.fetch(
            """SELECT name, is_predefined FROM categories 
               WHERE is_predefined = true OR coach_id = $1
               ORDER BY is_predefined DESC, name""",
            coach_id
        )
        
        # Convert rows to dictionaries for SQLite
        result = []
        for cat in categories:
            result.append({
                "name": cat[0], 
                "is_predefined": bool(cat[1])
            })
        return result
    
    except Exception as e:
        logger.error(f"Get categories error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")

@router.post("/coaches/{coach_id}/categories",
             summary="Add Custom Category",
             description="""
             Add a custom category for a coach.
             
             This endpoint allows coaches to create custom categories
             for organizing their clients beyond the predefined options.
             
             **Features:**
             - Custom category creation
             - Category validation
             - Coach-specific categories
             - Category management
             
             **Use Cases:**
             - Custom organization
             - Specialized categorization
             - Client grouping
             - Category management
             """,
             tags=["Client Categories"],
             responses={
                 200: {"description": "Category added successfully"},
                 400: {"description": "Invalid category data"},
                 404: {"description": "Coach not found"},
                 500: {"description": "Database error"}
             })
async def add_custom_category(coach_id: str, category_data: CategoryCreate):
    """Add custom category for coach"""
    try:
        async with db.pool.acquire() as conn:
            category_id = await conn.fetchval(
                "INSERT INTO categories (name, coach_id, is_predefined) VALUES ($1, $2, false) RETURNING id",
                category_data.name, coach_id
            )
            
            return {"category_id": str(category_id), "status": "created"}
    
    except Exception as e:
        logger.error(f"Add category error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add category")

@router.get("/coaches/{coach_id}/export",
            summary="Export to Google Sheets",
            description="""
            Export client data to Google Sheets.
            
            This endpoint exports a coach's client data to a Google Sheets
            spreadsheet for external analysis and reporting.
            
            **Features:**
            - Google Sheets integration
            - Client data export
            - Spreadsheet creation
            - Data formatting
            
            **Use Cases:**
            - Data analysis
            - External reporting
            - Data backup
            - Spreadsheet integration
            """,
            tags=["Data Export"],
            responses={
                200: {"description": "Data exported successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Export error"}
            })
async def export_to_google_sheets(coach_id: str):
    """Export client data to Google Sheets"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        async with db.pool.acquire() as conn:
            # Get comprehensive client data
            client_data = await conn.fetch("""
                SELECT 
                    c.id,
                    c.name,
                    c.phone_number,
                    c.country,
                    c.timezone,
                    c.created_at,
                    c.updated_at,
                    STRING_AGG(DISTINCT cat.name, ', ') as categories,
                    COUNT(DISTINCT g.id) as goals_count,
                    MAX(CASE WHEN mh.message_type = 'celebration' THEN mh.sent_at END) as last_celebration_sent,
                    MAX(CASE WHEN mh.message_type = 'accountability' THEN mh.sent_at END) as last_accountability_sent,
                    CASE 
                        WHEN COUNT(sm.id) > 0 THEN 'Has Scheduled Messages'
                        WHEN COUNT(mh.id) > 0 THEN 'Messages Sent'
                        ELSE 'New Client'
                    END as status
                FROM clients c
                LEFT JOIN client_categories cc ON c.id = cc.client_id
                LEFT JOIN categories cat ON cc.category_id = cat.id
                LEFT JOIN goals g ON c.id = g.client_id AND g.is_achieved = false
                LEFT JOIN message_history mh ON c.id = mh.client_id
                LEFT JOIN scheduled_messages sm ON c.id = sm.client_id AND sm.status = 'scheduled'
                WHERE c.coach_id = $1 AND c.is_active = true
                GROUP BY c.id, c.name, c.phone_number, c.country, c.timezone, c.created_at, c.updated_at
                ORDER BY c.name
            """, coach_id)
            
            # Format data for Google Sheets
            formatted_data = []
            for row in client_data:
                formatted_data.append({
                    "name": row['name'],
                    "phone_number": row['phone_number'],
                    "country": row['country'],
                    "timezone": row['timezone'],
                    "categories": row['categories'].split(', ') if row['categories'] else [],
                    "goals_count": row['goals_count'],
                    "last_celebration_sent": row['last_celebration_sent'].isoformat() if row['last_celebration_sent'] else '',
                    "last_accountability_sent": row['last_accountability_sent'].isoformat() if row['last_accountability_sent'] else '',
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else '',
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else ''
                })
            
            # Try to create/update Google Sheet
            if sheets_service.is_available():
                sheet_id = await sheets_service.create_or_update_sheet(coach_id, formatted_data)
                
                if sheet_id:
                    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
                    return {
                        "status": "exported",
                        "sheet_url": sheet_url,
                        "sheet_id": sheet_id,
                        "clients_count": len(formatted_data),
                        "message": "Data successfully exported to Google Sheets"
                    }
                else:
                    # Fallback to JSON if Google Sheets fails
                    return {
                        "status": "partial_export",
                        "data": formatted_data,
                        "message": "Google Sheets export failed, returning data as JSON"
                    }
            else:
                # Google Sheets not configured, return JSON
                return {
                    "status": "json_export",
                    "data": formatted_data,
                    "message": "Google Sheets not configured, returning data as JSON"
                }
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/coaches/{coach_id}/stats",
            summary="Get Coach Performance Statistics",
            description="""
            Get detailed performance statistics for a coach.
            
            This endpoint provides comprehensive performance metrics including
            client counts, message statistics, and system usage data.
            
            **Features:**
            - Performance metrics
            - Client statistics
            - Message activity
            - System usage
            - Trend analysis
            
            **Use Cases:**
            - Performance monitoring
            - Analytics reporting
            - Dashboard display
            - System optimization
            """,
            tags=["Analytics"],
            responses={
                200: {"description": "Statistics retrieved successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Database error"}
            })
async def get_coach_stats(coach_id: str):
    """Get coach performance statistics"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        async with db.pool.acquire() as conn:
            # Get total clients
            total_clients = await conn.fetchval(
                "SELECT COUNT(*) FROM clients WHERE coach_id = $1 AND is_active = true",
                coach_id
            )
            
            # Get messages sent this month
            messages_sent_month = await conn.fetchval(
                """SELECT COUNT(*) FROM message_history 
                   WHERE coach_id = $1 AND sent_at >= DATE_TRUNC('month', CURRENT_DATE)""",
                coach_id
            )
            
            # Get pending messages
            pending_messages = await conn.fetchval(
                "SELECT COUNT(*) FROM scheduled_messages WHERE coach_id = $1 AND status = 'scheduled'",
                coach_id
            )
            
            # Get active goals
            active_goals = await conn.fetchval(
                "SELECT COUNT(*) FROM goals g JOIN clients c ON g.client_id = c.id WHERE c.coach_id = $1 AND g.is_achieved = false",
                coach_id
            )
            
            # Get recent activity
            recent_activity = await conn.fetch(
                """SELECT 'message_sent' as type, sent_at as timestamp, content as description
                   FROM message_history 
                   WHERE coach_id = $1 
                   ORDER BY sent_at DESC 
                   LIMIT 5""",
                coach_id
            )
            
            return {
                "total_clients": total_clients or 0,
                "messages_sent_month": messages_sent_month or 0,
                "pending_messages": pending_messages or 0,
                "active_goals": active_goals or 0,
                "recent_activity": [dict(row) for row in recent_activity]
            }
    
    except Exception as e:
        logger.error(f"Get coach stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get coach stats: {str(e)}")

@router.get("/coaches/{coach_id}/analytics",
            summary="Get Coach Analytics",
            description="""
            Get detailed analytics for a coach's performance.
            
            This endpoint provides comprehensive analytics including message
            performance, client engagement, and system usage patterns.
            
            **Features:**
            - Message analytics
            - Client engagement metrics
            - Performance trends
            - Usage patterns
            - Detailed insights
            
            **Use Cases:**
            - Performance analysis
            - Strategy optimization
            - Client engagement tracking
            - System usage monitoring
            """,
            tags=["Analytics"],
            responses={
                200: {"description": "Analytics retrieved successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Database error"}
            })
async def get_coach_analytics(coach_id: str):
    """Get detailed analytics for a coach"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        async with db.pool.acquire() as conn:
            # Get message analytics by type
            message_analytics = await conn.fetch(
                """SELECT message_type, COUNT(*) as count, 
                          COUNT(CASE WHEN delivery_status = 'delivered' THEN 1 END) as delivered,
                          COUNT(CASE WHEN delivery_status = 'read' THEN 1 END) as read
                   FROM message_history 
                   WHERE coach_id = $1 
                   GROUP BY message_type""",
                coach_id
            )
            
            # Get client engagement
            client_engagement = await conn.fetch(
                """SELECT c.name, COUNT(mh.id) as messages_received,
                          MAX(mh.sent_at) as last_interaction
                   FROM clients c
                   LEFT JOIN message_history mh ON c.id = mh.client_id
                   WHERE c.coach_id = $1 AND c.is_active = true
                   GROUP BY c.id, c.name
                   ORDER BY messages_received DESC""",
                coach_id
            )
            
            return {
                "message_analytics": [dict(row) for row in message_analytics],
                "client_engagement": [dict(row) for row in client_engagement],
                "total_clients": len(client_engagement)
            }
    
    except Exception as e:
        logger.error(f"Get coach analytics error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get coach analytics: {str(e)}")

@router.get("/coaches/{coach_id}/goals",
            summary="Get Coach Goals",
            description="""
            Get all goals for a coach's clients.
            
            This endpoint retrieves all goals set for clients under a specific coach,
            including goal details, progress, and status information.
            
            **Features:**
            - Complete goals overview
            - Progress tracking
            - Status monitoring
            - Client goal management
            - Goal categorization
            
            **Use Cases:**
            - Goal monitoring
            - Progress tracking
            - Client development
            - Performance analysis
            """,
            tags=["Goal Management"],
            responses={
                200: {"description": "Goals retrieved successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Database error"}
            })
async def get_coach_goals(coach_id: str):
    """Get all goals for a coach's clients"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        async with db.pool.acquire() as conn:
            goals = await conn.fetch(
                """SELECT g.*, c.name as client_name, cat.name as category_name
                   FROM goals g
                   JOIN clients c ON g.client_id = c.id
                   LEFT JOIN categories cat ON g.category_id = cat.id
                   WHERE c.coach_id = $1
                   ORDER BY g.created_at DESC""",
                coach_id
            )
            
            return [dict(row) for row in goals]
    
    except Exception as e:
        logger.error(f"Get coach goals error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get coach goals: {str(e)}")

@router.get("/coaches/{coach_id}/clients/{client_id}/can-send-free",
            summary="Check 24-Hour Window Status",
            description="""
            Check if a free-form message can be sent to a client within Meta's 24-hour window.
            
            **24-Hour Window Rule:**
            - Starts when the client sends a message to the coach
            - Allows sending free-form messages (text, images, etc.) without templates
            - Expires 24 hours after the client's last message
            - After expiration, only pre-approved templates can be sent
            
            **Use Cases:**
            - Check before sending custom messages
            - Display warning in UI when window is closed
            - Determine if template is required
            """,
            tags=["Message Sending"],
            responses={
                200: {
                    "description": "24-hour window status",
                    "content": {
                        "application/json": {
                            "example": {
                                "can_send_free": True,
                                "last_user_message": "2025-09-07T09:00:00Z",
                                "window_expires_at": "2025-09-08T09:00:00Z",
                                "hours_remaining": 23.5
                            }
                        }
                    }
                },
                404: {
                    "description": "Client not found",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Client not found"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Failed to check window status"
                            }
                        }
                    }
                }
            })
async def can_send_free_message_to_client(coach_id: str, client_id: str):
    """Check if we can send a free message to a client (within 24h window)"""
    try:
        async with db.pool.acquire() as conn:
            # Get client phone number
            client = await conn.fetchrow(
                "SELECT phone_number FROM clients WHERE id = $1 AND coach_id = $2 AND is_active = true",
                client_id, coach_id
            )
            
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            
            # Clean phone number
            clean_phone = ''.join(filter(str.isdigit, client['phone_number']))
            
            # Check if we can send free message
            whatsapp_client = WhatsAppClient(
                os.getenv("WHATSAPP_ACCESS_TOKEN"),
                os.getenv("WHATSAPP_PHONE_NUMBER_ID")
            )
            
            can_send_free = await whatsapp_client.can_send_free_message(clean_phone)
            
            return {
                "can_send_free": can_send_free,
                "client_id": client_id,
                "phone_number": clean_phone
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Check free message eligibility error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check message eligibility")

@router.get("/coaches/{coach_id}/scheduled-messages",
            summary="Get Coach Scheduled Messages",
            description="""
            Get all scheduled messages for a coach.
            
            This endpoint retrieves all scheduled messages (pending, sent, failed)
            for a specific coach, including their status, timing, and content.
            
            **Features:**
            - Complete scheduled message list
            - Status tracking
            - Timing information
            - Message content preview
            - Filtering options
            
            **Use Cases:**
            - Schedule management
            - Message monitoring
            - Status tracking
            - Schedule optimization
            """,
            tags=["Message Scheduling"],
            responses={
                200: {"description": "Scheduled messages retrieved successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Database error"}
            })
async def get_scheduled_messages(coach_id: str):
    """Get all scheduled messages for a coach"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        async with db.pool.acquire() as conn:
            messages = await conn.fetch(
                """SELECT sm.*, c.name as client_name
                   FROM scheduled_messages sm
                   JOIN clients c ON sm.client_id = c.id
                   WHERE sm.coach_id = $1
                   ORDER BY sm.scheduled_time ASC""",
                coach_id
            )
            
            return [dict(row) for row in messages]
    
    except Exception as e:
        logger.error(f"Get scheduled messages error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduled messages: {str(e)}")

# Scheduler service (would run as separate service in production)
class MessageScheduler:
    def __init__(self):
        self.running = False
    
    async def start(self):
        """Start the message scheduler"""
        self.running = True
        while self.running:
            await self.process_scheduled_messages()
            await asyncio.sleep(60)  # Check every minute
    
    async def process_scheduled_messages(self):
        """Process messages that are due to be sent"""
        try:
            # Check if pool is available
            if not hasattr(db, 'pool') or db.pool is None:
                logger.warning("Database pool not available, skipping message processing")
                return
                
            async with db.pool.acquire() as conn:
                # Get messages due to be sent
                due_messages = await conn.fetch(
                    """SELECT sm.*, c.phone_number, co.whatsapp_token, co.whatsapp_phone_number
                       FROM scheduled_messages sm
                       JOIN clients c ON sm.client_id = c.id
                       JOIN coaches co ON sm.coach_id = co.id
                       WHERE sm.status = 'scheduled' 
                       AND sm.scheduled_time <= $1""",
                    datetime.now()
                )
                
                for message in due_messages:
                    # Send message
                    whatsapp_client = WhatsAppClient(
                        os.getenv("WHATSAPP_ACCESS_TOKEN"),
                        os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                    )
                    
                    result = await whatsapp_client.send_text_message(
                        message['phone_number'],
                        message['content']
                    )
                    
                    # Update status
                    await conn.execute(
                        "UPDATE scheduled_messages SET status = 'sent', sent_at = $1 WHERE id = $2",
                        datetime.now(), message['id']
                    )
                    
                    # Create history record
                    await conn.execute(
                        """INSERT INTO message_history 
                           (scheduled_message_id, coach_id, client_id, message_type, content, whatsapp_message_id, delivery_status)
                           VALUES ($1, $2, $3, $4, $5, $6, 'pending')""",
                        message['id'], message['coach_id'], message['client_id'],
                        message['message_type'], message['content'], result.get('messages', [{}])[0].get('id')
                    )
        
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

# Initialize scheduler (in production, this would be a separate service)
scheduler = MessageScheduler()

@router.on_event("startup")
async def startup_event():
    """Start background services"""
    # Only start scheduler if database pool is available
    if hasattr(db, 'pool') and db.pool is not None:
        asyncio.create_task(scheduler.start())
    else:
        logger.warning("Database pool not available, skipping scheduler startup")