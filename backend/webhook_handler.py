"""
WhatsApp Webhook Handler & Background Worker
Complete implementation for WhatsApp Business API integration
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
import hmac
import hashlib
import json
import os
import logging

logger = logging.getLogger(__name__)
from celery import Celery
import redis
import asyncio
from datetime import datetime, timedelta
import os

router = APIRouter()

# WhatsApp Webhook Verification (required by Meta)
@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token")
):
    """Verify WhatsApp webhook with Meta"""
    verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("Webhook verified successfully")
        return PlainTextResponse(hub_challenge)
    else:
        logger.warning("Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

# Enhanced WhatsApp Webhook Handler
@router.post("/whatsapp")
async def handle_whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp webhooks with security verification"""
    try:
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        # Verify webhook signature
        if not verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        webhook_data = json.loads(body)
        
        # Store webhook for processing
        async with db.pool.acquire() as conn:
            webhook_id = await conn.fetchval(
                "INSERT INTO whatsapp_webhooks (webhook_data, processed) VALUES ($1, false) RETURNING id",
                json.dumps(webhook_data)
            )
        
        # Process webhook asynchronously
        process_webhook_async.delay(str(webhook_id), webhook_data)
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Webhook handling error: {e}")
        return {"status": "error", "message": str(e)}

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify WhatsApp webhook signature"""
    try:
        app_secret = os.getenv("META_APP_SECRET")
        expected_signature = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        signature = signature.replace("sha256=", "")
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False

# Celery Configuration for Background Tasks
celery_app = Celery(
    "coaching_system",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Background Tasks

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def process_webhook_async(self, webhook_id: str, webhook_data: dict):
    """Process WhatsApp webhook asynchronously"""
    try:
        # This runs the webhook processing logic
        asyncio.run(process_whatsapp_webhook_detailed(webhook_id, webhook_data))
    except Exception as e:
        logger.error(f"Webhook processing failed for {webhook_id}: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 30})
def send_scheduled_message_task(self, scheduled_message_id: str):
    """Send a scheduled message"""
    try:
        asyncio.run(send_immediate_message(scheduled_message_id))
    except Exception as e:
        logger.error(f"Scheduled message sending failed for {scheduled_message_id}: {e}")
        raise self.retry(exc=e)

@celery_app.task
def process_voice_message_task(voice_processing_id: str, audio_url: str):
    """Process voice message transcription and correction"""
    try:
        asyncio.run(process_voice_message_complete(voice_processing_id, audio_url))
    except Exception as e:
        logger.error(f"Voice processing failed for {voice_processing_id}: {e}")

@celery_app.task
def sync_google_sheets_task(coach_id: str):
    """Sync data to Google Sheets"""
    try:
        asyncio.run(sync_coach_data_to_sheets(coach_id))
    except Exception as e:
        logger.error(f"Google Sheets sync failed for {coach_id}: {e}")

# Enhanced webhook processing
async def process_whatsapp_webhook_detailed(webhook_id: str, webhook_data: dict):
    """Detailed WhatsApp webhook processing"""
    try:
        async with db.pool.acquire() as conn:
            for entry in webhook_data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        
                        # Process incoming messages
                        for message in value.get('messages', []):
                            await process_incoming_message(conn, message)
                        
                        # Process message status updates
                        for status in value.get('statuses', []):
                            await process_message_status(conn, status)
            
            # Mark webhook as processed
            await conn.execute(
                "UPDATE whatsapp_webhooks SET processed = true WHERE id = $1",
                webhook_id
            )
    
    except Exception as e:
        logger.error(f"Detailed webhook processing error: {e}")
        raise

async def process_incoming_message(conn, message: dict):
    """Process individual incoming WhatsApp message"""
    try:
        from_number = message.get('from')
        message_type = message.get('type')
        message_id = message.get('id')
        
        # Find coach by phone number mapping
        coach = await conn.fetchrow(
            """SELECT c.* FROM coaches c 
               WHERE EXISTS (
                   SELECT 1 FROM clients cl 
                   WHERE cl.coach_id = c.id AND cl.phone_number = $1
               )""",
            from_number
        )
        
        if not coach:
            logger.warning(f"No coach found for phone number: {from_number}")
            return
        
        if message_type == 'text':
            # Process text commands
            text_body = message.get('text', {}).get('body', '')
            await process_text_command_enhanced(str(coach['id']), from_number, text_body)
        
        elif message_type == 'audio':
            # Process voice messages
            audio = message.get('audio', {})
            audio_id = audio.get('id')
            
            if audio_id:
                # Get audio file URL from WhatsApp
                audio_url = await get_whatsapp_media_url(os.getenv("WHATSAPP_ACCESS_TOKEN"), audio_id)
                
                # Start voice processing
                processing_id = await conn.fetchval(
                    """INSERT INTO voice_message_processing 
                       (coach_id, whatsapp_message_id, original_audio_url, processing_status)
                       VALUES ($1, $2, $3, 'received') RETURNING id""",
                    str(coach['id']), message_id, audio_url
                )
                
                # Process asynchronously
                process_voice_message_task.delay(str(processing_id), audio_url)
        
        elif message_type == 'interactive':
            # Handle button responses (Confirm/Edit)
            interactive = message.get('interactive', {})
            if interactive.get('type') == 'button_reply':
                button_reply = interactive.get('button_reply', {})
                button_id = button_reply.get('id', '')
                
                if button_id.startswith('confirm_'):
                    processing_id = button_id.replace('confirm_', '')
                    await handle_voice_confirmation(processing_id, True)
                elif button_id.startswith('edit_'):
                    processing_id = button_id.replace('edit_', '')
                    await handle_voice_confirmation(processing_id, False)
    
    except Exception as e:
        logger.error(f"Process incoming message error: {e}")

async def process_message_status(conn, status: dict):
    """Process WhatsApp message status updates"""
    try:
        message_id = status.get('id')
        recipient_id = status.get('recipient_id')
        status_type = status.get('status')  # sent, delivered, read, failed
        timestamp = status.get('timestamp')
        
        # Update message history with delivery status
        await conn.execute(
            """UPDATE message_history 
               SET delivery_status = $1, 
                   delivered_at = CASE WHEN $1 = 'delivered' THEN to_timestamp($2) END,
                   read_at = CASE WHEN $1 = 'read' THEN to_timestamp($2) END
               WHERE whatsapp_message_id = $3""",
            status_type, timestamp, message_id
        )
    
    except Exception as e:
        logger.error(f"Process message status error: {e}")

async def get_whatsapp_media_url(access_token: str, media_id: str) -> str:
    """Get media URL from WhatsApp for voice messages"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            # Get media info
            response = await client.get(
                f"https://graph.facebook.com/v22.0/{media_id}",
                headers=headers
            )
            media_info = response.json()
            
            # Get actual media file
            media_response = await client.get(
                media_info['url'],
                headers=headers
            )
            
            return media_info['url']
    
    except Exception as e:
        logger.error(f"Get media URL error: {e}")
        return None

async def process_text_command_enhanced(coach_id: str, from_number: str, command_text: str):
    """Enhanced natural language command processing"""
    try:
        # Use GPT to parse and understand the command
        openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Get coach's client list for context
        async with db.pool.acquire() as conn:
            clients = await conn.fetch(
                "SELECT name, phone_number FROM clients WHERE coach_id = $1 AND is_active = true",
                coach_id
            )
            
            client_names = [client['name'] for client in clients]
            
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a command parser for a coaching system. Parse the user's message and return a JSON response.
                        
                        Available clients: {', '.join(client_names)}
                        
                        Return JSON with:
                        {{
                            "action": "send_celebration" | "send_accountability" | "get_stats" | "add_client" | "schedule_message" | "unknown",
                            "clients": ["client_name1", "client_name2"] or ["all"] or [],
                            "message": "custom message if provided" or null,
                            "timing": "now" | "schedule" | null,
                            "schedule_time": "HH:MM" or null,
                            "additional_data": {{}} // any extra context
                        }}
                        
                        Examples:
                        "send celebration to Mike" -> {{"action": "send_celebration", "clients": ["Mike"], "timing": "now"}}
                        "send accountability to all at 3pm" -> {{"action": "send_accountability", "clients": ["all"], "timing": "schedule", "schedule_time": "15:00"}}
                        "get my client stats" -> {{"action": "get_stats", "clients": []}}
                        """
                    },
                    {
                        "role": "user",
                        "content": command_text
                    }
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            try:
                command_data = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                command_data = {"action": "unknown", "clients": [], "message": "Sorry, I couldn't understand that command."}
            
            # Execute the parsed command
            await execute_parsed_command(coach_id, from_number, command_data)
    
    except Exception as e:
        logger.error(f"Enhanced command processing error: {e}")

async def execute_parsed_command(coach_id: str, from_number: str, command_data: dict):
    """Execute the parsed command"""
    try:
        async with db.pool.acquire() as conn:
            coach = await conn.fetchrow("SELECT * FROM coaches WHERE id = $1", coach_id)
            whatsapp_client = WhatsAppClient(os.getenv("WHATSAPP_ACCESS_TOKEN"), os.getenv("WHATSAPP_PHONE_NUMBER_ID"))
            
            action = command_data.get('action')
            
            if action == 'get_stats':
                # Send Google Sheet with stats
                await send_google_sheet_to_coach(coach_id)
                await whatsapp_client.send_text_message(
                    from_number,
                    "📊 I've updated your Google Sheet with the latest client stats and sent it to you!"
                )
            
            elif action in ['send_celebration', 'send_accountability']:
                clients_to_message = []
                
                if command_data.get('clients') == ['all']:
                    clients_to_message = await conn.fetch(
                        "SELECT * FROM clients WHERE coach_id = $1 AND is_active = true",
                        coach_id
                    )
                else:
                    # Find specific clients by name
                    for client_name in command_data.get('clients', []):
                        client = await conn.fetchrow(
                            "SELECT * FROM clients WHERE coach_id = $1 AND name ILIKE $2 AND is_active = true",
                            coach_id, f"%{client_name}%"
                        )
                        if client:
                            clients_to_message.append(client)
                
                if not clients_to_message:
                    await whatsapp_client.send_text_message(
                        from_number,
                        "I couldn't find any matching clients. Please check the names and try again."
                    )
                    return
                
                # Get appropriate message content
                message_content = command_data.get('message')
                if not message_content:
                    # Use default message
                    if action == 'send_celebration':
                        message_content = "🎉 What are we celebrating today?"
                    else:
                        message_content = "How are you progressing toward your goals today?"
                
                # Schedule messages
                message_ids = []
                for client in clients_to_message:
                    scheduled_id = await conn.fetchval(
                        """INSERT INTO scheduled_messages 
                           (coach_id, client_id, message_type, content, schedule_type, status)
                           VALUES ($1, $2, $3, $4, 'now', 'pending') RETURNING id""",
                        coach_id, client['id'], action.replace('send_', ''), message_content
                    )
                    message_ids.append(str(scheduled_id))
                
                # Send messages
                for message_id in message_ids:
                    send_scheduled_message_task.delay(message_id)
                
                client_names = [client['name'] for client in clients_to_message]
                await whatsapp_client.send_text_message(
                    from_number,
                    f"✅ {action.replace('send_', '').title()} messages sent to: {', '.join(client_names)}"
                )
            
            else:
                # Unknown command
                await whatsapp_client.send_text_message(
                    from_number,
                    """I didn't understand that command. Here are some examples:
                    
📝 "send celebration to Mike"
📝 "send accountability to all"  
📝 "get my client stats"
📝 "send accountability to Sarah at 3pm"

What would you like to do?"""
                )
    
    except Exception as e:
        logger.error(f"Execute command error: {e}")

async def process_voice_message_complete(processing_id: str, audio_url: str):
    """Complete voice message processing pipeline"""
    try:
        async with db.pool.acquire() as conn:
            # Get processing record
            processing_record = await conn.fetchrow(
                "SELECT * FROM voice_message_processing WHERE id = $1",
                processing_id
            )
            
            if not processing_record:
                return
            
            # Transcribe audio
            transcribed_text = await transcription_service.transcribe_audio(audio_url)
            
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
            
            # Get coach info
            coach = await conn.fetchrow("SELECT * FROM coaches WHERE id = $1", processing_record['coach_id'])
            whatsapp_client = WhatsAppClient(os.getenv("WHATSAPP_ACCESS_TOKEN"), os.getenv("WHATSAPP_PHONE_NUMBER_ID"))
            
            # Send confirmation message with buttons
            confirmation_message = f"""🎤 Voice message processed:

📝 **Transcribed**: {transcribed_text}

✨ **Corrected**: {corrected_text}

Please choose:"""
            
            buttons = [
                {"id": f"confirm_{processing_id}", "title": "✅ Confirm & Send"},
                {"id": f"edit_{processing_id}", "title": "✏️ Edit Message"}
            ]
            
            await whatsapp_client.send_interactive_message(
                coach['whatsapp_phone_number'],
                confirmation_message,
                buttons
            )
    
    except Exception as e:
        logger.error(f"Voice message processing error: {e}")

# Background scheduler for timed messages
@celery_app.task
def check_scheduled_messages():
    """Check and send due scheduled messages"""
    try:
        asyncio.run(process_due_messages())
    except Exception as e:
        logger.error(f"Scheduled message check error: {e}")

async def process_due_messages():
    """Process messages that are due to be sent"""
    try:
        async with db.pool.acquire() as conn:
            # Get messages due now (with 1-minute buffer)
            due_messages = await conn.fetch(
                """SELECT sm.id FROM scheduled_messages sm
                   WHERE sm.status = 'scheduled' 
                   AND sm.scheduled_time <= $1
                   AND sm.scheduled_time > $2""",
                datetime.now() + timedelta(minutes=1),
                datetime.now() - timedelta(minutes=5)  # Prevent duplicate processing
            )
            
            for message in due_messages:
                send_scheduled_message_task.delay(str(message['id']))
    
    except Exception as e:
        logger.error(f"Process due messages error: {e}")

# Set up periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'check-scheduled-messages': {
        'task': 'check_scheduled_messages',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-old-data': {
        'task': 'cleanup_old_webhooks',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'sync-google-sheets': {
        'task': 'sync_all_coach_sheets',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
}

@celery_app.task
def cleanup_old_webhooks():
    """Clean up old webhook data"""
    try:
        asyncio.run(cleanup_old_data())
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

async def cleanup_old_data():
    """Clean up old data from database"""
    try:
        async with db.pool.acquire() as conn:
            # Clean old webhooks (older than 7 days)
            await conn.execute(
                "DELETE FROM whatsapp_webhooks WHERE created_at < $1",
                datetime.now() - timedelta(days=7)
            )
            
            # Clean old voice processing records (older than 30 days)
            await conn.execute(
                "DELETE FROM voice_message_processing WHERE created_at < $1 AND processing_status = 'confirmed'",
                datetime.now() - timedelta(days=30)
            )
            
            logger.info("Old data cleanup completed")
    
    except Exception as e:
        logger.error(f"Cleanup old data error: {e}")

@celery_app.task
def sync_all_coach_sheets():
    """Sync Google Sheets for all coaches"""
    try:
        asyncio.run(sync_all_coaches_to_sheets())
    except Exception as e:
        logger.error(f"Sync all coaches error: {e}")

async def sync_all_coaches_to_sheets():
    """Sync Google Sheets for all active coaches"""
    try:
        async with db.pool.acquire() as conn:
            coaches = await conn.fetch("SELECT id FROM coaches WHERE is_active = true")
            
            for coach in coaches:
                try:
                    await sync_coach_data_to_sheets(str(coach['id']))
                except Exception as e:
                    logger.error(f"Sheet sync failed for coach {coach['id']}: {e}")
    
    except Exception as e:
        logger.error(f"Sync all coaches to sheets error: {e}")

async def sync_coach_data_to_sheets(coach_id: str):
    """Sync individual coach data to Google Sheets"""
    try:
        async with db.pool.acquire() as conn:
            # Get client data
            client_data = await conn.fetch(
                "SELECT * FROM get_client_export_data($1)",
                coach_id
            )
            
            # Update Google Sheet
            await sheets_service.create_or_update_sheet(
                coach_id, [dict(row) for row in client_data]
            )
            
            logger.info(f"Google Sheets synced for coach {coach_id}")
    
    except Exception as e:
        logger.error(f"Sync coach data error for {coach_id}: {e}")

# Worker startup
if __name__ == "__main__":
    # This file can also be run as a Celery worker
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        celery_app.start(['worker', '--loglevel=info'])
    elif len(sys.argv) > 1 and sys.argv[1] == "beat":
        celery_app.start(['beat', '--loglevel=info'])
    else:
        # Run FastAPI
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)