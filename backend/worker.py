"""
worker.py - Dedicated Celery Worker Service
Handles all background processing tasks for the coaching system
"""

import os
import asyncio
import logging
from celery import Celery
from celery.schedules import crontab
import asyncpg
import openai
import httpx
import json
from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .whatsapp_templates import template_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Celery app configuration
celery_app = Celery(
    'coaching_worker',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    include=['worker']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_routes={
        'worker.send_whatsapp_message': {'queue': 'messages'},
        'worker.process_voice_message': {'queue': 'voice'},
        'worker.sync_google_sheets': {'queue': 'sheets'},
        'worker.send_bulk_messages': {'queue': 'bulk'},
    }
)

# Database connection helper
async def get_db_connection():
    """Get database connection"""
    return await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'coaching_system')
    )

# WhatsApp API Client
class WhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v22.0"
    
    async def send_message(self, to: str, message: str, template_name: str = "hello_world") -> dict:
        """Send WhatsApp template message"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Clean phone number - remove all non-digits
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()
    
    async def send_text_message(self, to: str, message: str) -> dict:
        """Send WhatsApp text message (fallback)"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Clean phone number - remove all non-digits
        clean_phone = ''.join(filter(str.isdigit, to))
        
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "text",
            "text": {"body": message}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()
    
    async def send_interactive_message(self, to: str, message: str, buttons: list) -> dict:
        """Send interactive message with buttons"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        interactive_buttons = []
        for button in buttons:
            interactive_buttons.append({
                "type": "reply",
                "reply": {
                    "id": button["id"],
                    "title": button["title"]
                }
            })
        
        # Clean phone number - remove all non-digits
        clean_phone = ''.join(filter(str.isdigit, to))
        
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {"buttons": interactive_buttons}
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()

# Core Background Tasks

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def send_whatsapp_message(self, scheduled_message_id: str):
    """Send individual WhatsApp message"""
    try:
        async def _send_message():
            conn = await get_db_connection()
            try:
                # Get message details
                message_data = await conn.fetchrow(
                    """SELECT sm.*, c.phone_number, c.name as client_name, 
                              co.whatsapp_token, co.whatsapp_phone_number, co.name as coach_name
                       FROM scheduled_messages sm
                       JOIN clients c ON sm.client_id = c.id
                       JOIN coaches co ON sm.coach_id = co.id
                       WHERE sm.id = $1 AND sm.status IN ('pending', 'scheduled')""",
                    scheduled_message_id
                )
                
                if not message_data:
                    logger.warning(f"Message {scheduled_message_id} not found or already sent")
                    return
                
                # Create WhatsApp client
                whatsapp_client = WhatsAppClient(
                    os.getenv("WHATSAPP_ACCESS_TOKEN"),
                    os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                )
                
                # Send message
                result = await whatsapp_client.send_text_message(
                    message_data['phone_number'],
                    message_data['content']
                )
                
                # Update status
                if 'error' in result:
                    await conn.execute(
                        "UPDATE scheduled_messages SET status = 'failed', updated_at = $1 WHERE id = $2",
                        datetime.now(), scheduled_message_id
                    )
                    logger.error(f"WhatsApp API error for message {scheduled_message_id}: {result}")
                else:
                    await conn.execute(
                        "UPDATE scheduled_messages SET status = 'sent', sent_at = $1 WHERE id = $2",
                        datetime.now(), scheduled_message_id
                    )
                    
                    # Create message history record
                    whatsapp_msg_id = result.get('messages', [{}])[0].get('id')
                    await conn.execute(
                        """INSERT INTO message_history 
                           (scheduled_message_id, coach_id, client_id, message_type, content, 
                            whatsapp_message_id, delivery_status, sent_at)
                           VALUES ($1, $2, $3, $4, $5, $6, 'sent', $7)""",
                        scheduled_message_id, message_data['coach_id'], message_data['client_id'],
                        message_data['message_type'], message_data['content'], 
                        whatsapp_msg_id, datetime.now()
                    )
                    
                    logger.info(f"Message sent successfully to {message_data['client_name']} ({message_data['phone_number']})")
            
            finally:
                await conn.close()
        
        # Run async function
        asyncio.run(_send_message())
        
    except Exception as e:
        logger.error(f"Send message task failed for {scheduled_message_id}: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 120})
def process_voice_message(self, voice_processing_id: str):
    """Process voice message transcription and correction"""
    try:
        async def _process_voice():
            conn = await get_db_connection()
            try:
                # Get processing record
                processing_record = await conn.fetchrow(
                    "SELECT * FROM voice_message_processing WHERE id = $1",
                    voice_processing_id
                )
                
                if not processing_record:
                    logger.warning(f"Voice processing record {voice_processing_id} not found")
                    return
                
                # Step 1: Download and transcribe audio
                audio_url = processing_record['original_audio_url']
                
                # Download audio file
                async with httpx.AsyncClient(timeout=60.0) as client:
                    audio_response = await client.get(audio_url)
                    audio_content = audio_response.content
                
                # Transcribe with OpenAI Whisper
                openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                    temp_file.write(audio_content)
                    temp_file_path = temp_file.name
                
                try:
                    with open(temp_file_path, "rb") as audio_file:
                        transcript = await openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file
                        )
                    
                    transcribed_text = transcript.text
                    
                    # Update database with transcription
                    await conn.execute(
                        "UPDATE voice_message_processing SET transcribed_text = $1, processing_status = 'transcribed' WHERE id = $2",
                        transcribed_text, voice_processing_id
                    )
                    
                    # Step 2: Correct message with GPT-4o-mini
                    correction_response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful assistant that corrects grammar and improves the clarity of coaching messages. Keep the original tone and intent, but fix any grammatical errors and make the message clear and professional. Return only the corrected message without any additional text."
                            },
                            {
                                "role": "user",
                                "content": f"Please correct this coaching message: {transcribed_text}"
                            }
                        ],
                        max_tokens=200,
                        temperature=0.3
                    )
                    
                    corrected_text = correction_response.choices[0].message.content.strip()
                    
                    # Update database with correction
                    await conn.execute(
                        "UPDATE voice_message_processing SET corrected_text = $1, processing_status = 'corrected' WHERE id = $2",
                        corrected_text, voice_processing_id
                    )
                    
                    # Step 3: Send confirmation message to coach
                    coach = await conn.fetchrow("SELECT * FROM coaches WHERE id = $1", processing_record['coach_id'])
                    
                    whatsapp_client = WhatsAppClient(
                        os.getenv("WHATSAPP_ACCESS_TOKEN"),
                        os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                    )
                    
                    confirmation_message = f"""🎤 **Voice Message Processed**

📝 **Original**: {transcribed_text}

✨ **Corrected**: {corrected_text}

Please choose what to do next:"""
                    
                    buttons = [
                        {"id": f"confirm_{voice_processing_id}", "title": "✅ Confirm & Send"},
                        {"id": f"edit_{voice_processing_id}", "title": "✏️ Edit Message"}
                    ]
                    
                    await whatsapp_client.send_interactive_message(
                        coach['whatsapp_phone_number'],
                        confirmation_message,
                        buttons
                    )
                    
                    logger.info(f"Voice message processed and confirmation sent for {voice_processing_id}")
                
                finally:
                    # Clean up temp file
                    os.unlink(temp_file_path)
            
            finally:
                await conn.close()
        
        asyncio.run(_process_voice())
        
    except Exception as e:
        logger.error(f"Voice processing task failed for {voice_processing_id}: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2, "countdown": 300})
def sync_google_sheets(self, coach_id: str):
    """Sync coach data to Google Sheets"""
    try:
        async def _sync_sheets():
            conn = await get_db_connection()
            try:
                # Get client data for export
                client_data = await conn.fetch(
                    """SELECT 
                        c.name as client_name,
                        c.phone_number,
                        c.country,
                        STRING_AGG(DISTINCT g.title, ', ') as goals,
                        ARRAY_TO_STRING(ARRAY_AGG(DISTINCT cat.name), ', ') as categories,
                        MAX(CASE WHEN mh.message_type = 'accountability' THEN mh.sent_at END) as last_accountability_sent,
                        MAX(CASE WHEN mh.message_type = 'celebration' THEN mh.sent_at END) as last_celebration_sent,
                        CASE 
                            WHEN EXISTS (SELECT 1 FROM scheduled_messages sm WHERE sm.client_id = c.id AND sm.status = 'scheduled') 
                            THEN 'Scheduled' 
                            WHEN EXISTS (SELECT 1 FROM message_history mh WHERE mh.client_id = c.id) 
                            THEN 'Sent' 
                            ELSE 'Not set up yet' 
                        END as status,
                        c.timezone
                    FROM clients c
                    LEFT JOIN client_categories cc ON c.id = cc.client_id
                    LEFT JOIN categories cat ON cc.category_id = cat.id
                    LEFT JOIN goals g ON c.id = g.client_id AND g.is_achieved = false
                    LEFT JOIN message_history mh ON c.id = mh.client_id
                    WHERE c.coach_id = $1 AND c.is_active = true
                    GROUP BY c.id, c.name, c.phone_number, c.country, c.timezone
                    ORDER BY c.name""",
                    coach_id
                )
                
                # Get or create Google Sheets service
                creds = Credentials.from_authorized_user_info({
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
                    "type": "authorized_user"
                })
                
                service = build('sheets', 'v4', credentials=creds)
                
                # Check if sheet exists
                sheet_record = await conn.fetchrow(
                    "SELECT sheet_id, sheet_url FROM google_sheets_sync WHERE coach_id = $1 ORDER BY created_at DESC LIMIT 1",
                    coach_id
                )
                
                # Prepare data
                headers = [
                    "Client Name", "Phone Number", "Country", "Goals", "Categories",
                    "Last Accountability Sent", "Last Celebration Sent", "Status", "Timezone"
                ]
                
                rows = [headers]
                for client in client_data:
                    rows.append([
                        client['client_name'] or '',
                        client['phone_number'] or '',
                        client['country'] or '',
                        client['goals'] or '',
                        client['categories'] or '',
                        str(client['last_accountability_sent']) if client['last_accountability_sent'] else '',
                        str(client['last_celebration_sent']) if client['last_celebration_sent'] else '',
                        client['status'] or '',
                        client['timezone'] or ''
                    ])
                
                if sheet_record and sheet_record['sheet_id']:
                    # Update existing sheet
                    sheet_id = sheet_record['sheet_id']
                    service.spreadsheets().values().clear(
                        spreadsheetId=sheet_id,
                        range='Sheet1!A:Z'
                    ).execute()
                    
                    service.spreadsheets().values().update(
                        spreadsheetId=sheet_id,
                        range='Sheet1!A1',
                        valueInputOption='USER_ENTERED',
                        body={'values': rows}
                    ).execute()
                    
                else:
                    # Create new sheet
                    spreadsheet = {
                        'properties': {
                            'title': f'Coaching Data - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                        }
                    }
                    sheet = service.spreadsheets().create(body=spreadsheet).execute()
                    sheet_id = sheet['spreadsheetId']
                    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                    
                    # Add data
                    service.spreadsheets().values().update(
                        spreadsheetId=sheet_id,
                        range='Sheet1!A1',
                        valueInputOption='USER_ENTERED',
                        body={'values': rows}
                    ).execute()
                    
                    # Save sheet info
                    await conn.execute(
                        """INSERT INTO google_sheets_sync (coach_id, sheet_id, sheet_url, last_sync_at, sync_status, row_count)
                           VALUES ($1, $2, $3, $4, 'success', $5)""",
                        coach_id, sheet_id, sheet_url, datetime.now(), len(rows)
                    )
                
                # Update sync status
                await conn.execute(
                    """UPDATE google_sheets_sync 
                       SET last_sync_at = $1, sync_status = 'success', row_count = $2 
                       WHERE coach_id = $3""",
                    datetime.now(), len(rows), coach_id
                )
                
                logger.info(f"Google Sheets synced successfully for coach {coach_id}: {len(rows)} rows")
                
            finally:
                await conn.close()
        
        asyncio.run(_sync_sheets())
        
    except Exception as e:
        logger.error(f"Google Sheets sync failed for coach {coach_id}: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 5, "countdown": 60})
def send_bulk_messages(self, coach_id: str, client_ids: list, message_content: str, message_type: str):
    """Send bulk messages to multiple clients"""
    try:
        async def _send_bulk():
            conn = await get_db_connection()
            try:
                # Get coach and client data
                coach = await conn.fetchrow("SELECT * FROM coaches WHERE id = $1", coach_id)
                clients = await conn.fetch(
                    "SELECT * FROM clients WHERE id = ANY($1) AND coach_id = $2 AND is_active = true",
                    client_ids, coach_id
                )
                
                if not coach or not clients:
                    logger.warning(f"Coach {coach_id} or clients {client_ids} not found")
                    return
                
                whatsapp_client = WhatsAppClient(
                    os.getenv("WHATSAPP_ACCESS_TOKEN"),
                    os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                )
                
                success_count = 0
                failed_count = 0
                
                for client in clients:
                    try:
                        # Send message
                        result = await whatsapp_client.send_text_message(
                            client['phone_number'],
                            message_content
                        )
                        
                        # Record result
                        if 'error' not in result:
                            whatsapp_msg_id = result.get('messages', [{}])[0].get('id')
                            await conn.execute(
                                """INSERT INTO message_history 
                                   (coach_id, client_id, message_type, content, whatsapp_message_id, delivery_status, sent_at)
                                   VALUES ($1, $2, $3, $4, $5, 'sent', $6)""",
                                coach_id, client['id'], message_type, message_content,
                                whatsapp_msg_id, datetime.now()
                            )
                            success_count += 1
                        else:
                            failed_count += 1
                            logger.error(f"Failed to send to {client['name']}: {result}")
                        
                        # Rate limiting - wait between messages
                        await asyncio.sleep(1)
                    
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error sending to {client['name']}: {e}")
                
                logger.info(f"Bulk message completed: {success_count} sent, {failed_count} failed")
                
                # Send summary to coach
                summary_msg = f"""📊 **Bulk Message Summary**

✅ Successfully sent: {success_count}
❌ Failed: {failed_count}
📝 Message type: {message_type}

Total clients processed: {len(clients)}"""
                
                try:
                    await whatsapp_client.send_text_message(
                        coach['whatsapp_phone_number'],
                        summary_msg
                    )
                except Exception as e:
                    logger.error(f"Failed to send summary to coach: {e}")
            
            finally:
                await conn.close()
        
        asyncio.run(_send_bulk())
        
    except Exception as e:
        logger.error(f"Bulk message task failed: {e}")
        raise self.retry(exc=e)

@celery_app.task
def check_scheduled_messages():
    """Check and process scheduled messages"""
    try:
        async def _check_scheduled():
            conn = await get_db_connection()
            try:
                # Get messages due to be sent (with 2-minute buffer)
                current_time = datetime.now()
                due_messages = await conn.fetch(
                    """SELECT id FROM scheduled_messages 
                       WHERE status = 'scheduled' 
                       AND scheduled_time <= $1 
                       AND scheduled_time > $2""",
                    current_time + timedelta(minutes=2),
                    current_time - timedelta(minutes=10)  # Prevent reprocessing
                )
                
                logger.info(f"Found {len(due_messages)} messages due for sending")
                
                # Queue each message for sending
                for message in due_messages:
                    send_whatsapp_message.delay(str(message['id']))
                
                # Handle recurring messages
                recurring_messages = await conn.fetch(
                    """SELECT * FROM scheduled_messages 
                       WHERE schedule_type = 'recurring' 
                       AND status = 'sent'
                       AND recurring_pattern IS NOT NULL""",
                )
                
                for recurring_msg in recurring_messages:
                    # Calculate next occurrence based on recurring pattern
                    pattern = recurring_msg['recurring_pattern']
                    if pattern and 'frequency' in pattern:
                        next_time = calculate_next_occurrence(
                            recurring_msg['scheduled_time'], 
                            pattern
                        )
                        
                        if next_time and next_time <= current_time + timedelta(minutes=5):
                            # Create new scheduled message
                            await conn.execute(
                                """INSERT INTO scheduled_messages 
                                   (coach_id, client_id, message_type, content, schedule_type, 
                                    scheduled_time, recurring_pattern, status)
                                   VALUES ($1, $2, $3, $4, 'recurring', $5, $6, 'scheduled')""",
                                recurring_msg['coach_id'], recurring_msg['client_id'],
                                recurring_msg['message_type'], recurring_msg['content'],
                                next_time, pattern
                            )
            
            finally:
                await conn.close()
        
        asyncio.run(_check_scheduled())
        
    except Exception as e:
        logger.error(f"Scheduled message check failed: {e}")

def calculate_next_occurrence(last_time: datetime, pattern: dict) -> datetime:
    """Calculate next occurrence for recurring messages"""
    try:
        frequency = pattern.get('frequency', 'daily')
        interval = pattern.get('interval', 1)
        
        if frequency == 'daily':
            return last_time + timedelta(days=interval)
        elif frequency == 'weekly':
            return last_time + timedelta(weeks=interval)
        elif frequency == 'monthly':
            # Simple monthly calculation (could be improved)
            return last_time + timedelta(days=30 * interval)
        else:
            return None
    
    except Exception as e:
        logger.error(f"Calculate next occurrence error: {e}")
        return None

@celery_app.task
def cleanup_old_data():
    """Clean up old data to maintain database performance"""
    try:
        async def _cleanup():
            conn = await get_db_connection()
            try:
                current_time = datetime.now()
                
                # Clean old webhooks (older than 7 days)
                deleted_webhooks = await conn.fetchval(
                    "DELETE FROM whatsapp_webhooks WHERE created_at < $1 AND processing_status = 'processed' RETURNING COUNT(*)",
                    current_time - timedelta(days=7)
                )
                
                # Clean old voice processing records (older than 30 days and completed)
                deleted_voice = await conn.fetchval(
                    """DELETE FROM voice_message_processing 
                       WHERE created_at < $1 AND processing_status IN ('confirmed', 'failed') 
                       RETURNING COUNT(*)""",
                    current_time - timedelta(days=30)
                )
                
                # Archive old message history (older than 1 year)
                archived_messages = await conn.fetchval(
                    """UPDATE message_history 
                       SET delivery_status = 'archived' 
                       WHERE sent_at < $1 AND delivery_status != 'archived'
                       RETURNING COUNT(*)""",
                    current_time - timedelta(days=365)
                )
                
                logger.info(f"Cleanup completed: {deleted_webhooks} webhooks, {deleted_voice} voice records, {archived_messages} messages archived")
                
            finally:
                await conn.close()
        
        asyncio.run(_cleanup())
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")

@celery_app.task
def send_daily_analytics():
    """Send daily analytics to coaches"""
    try:
        async def _send_analytics():
            conn = await get_db_connection()
            try:
                # Get all active coaches
                coaches = await conn.fetch("SELECT * FROM coaches WHERE is_active = true")
                
                for coach in coaches:
                    try:
                        # Get yesterday's stats
                        yesterday = datetime.now() - timedelta(days=1)
                        
                        stats = await conn.fetchrow(
                            """SELECT 
                                COUNT(CASE WHEN message_type = 'celebration' THEN 1 END) as celebrations_sent,
                                COUNT(CASE WHEN message_type = 'accountability' THEN 1 END) as accountability_sent,
                                COUNT(CASE WHEN delivery_status = 'read' THEN 1 END) as messages_read,
                                COUNT(*) as total_messages
                            FROM message_history 
                            WHERE coach_id = $1 AND DATE(sent_at) = $2""",
                            coach['id'], yesterday.date()
                        )
                        
                        if stats['total_messages'] > 0:
                            analytics_message = f"""📊 **Daily Analytics Report**
🗓️ Date: {yesterday.strftime('%B %d, %Y')}

📈 **Messages Sent:**
🎉 Celebrations: {stats['celebrations_sent']}
🎯 Accountability: {stats['accountability_sent']}
📖 Read by clients: {stats['messages_read']}
📤 Total sent: {stats['total_messages']}

📋 **Engagement Rate:** {(stats['messages_read'] / stats['total_messages'] * 100):.1f}%

Keep up the great coaching! 💪"""
                            
                            whatsapp_client = WhatsAppClient(
                                os.getenv("WHATSAPP_ACCESS_TOKEN"),
                                os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                            )
                            
                            await whatsapp_client.send_text_message(
                                coach['whatsapp_phone_number'],
                                analytics_message
                            )
                    
                    except Exception as e:
                        logger.error(f"Failed to send analytics to coach {coach['id']}: {e}")
            
            finally:
                await conn.close()
        
        asyncio.run(_send_analytics())
        
    except Exception as e:
        logger.error(f"Daily analytics task failed: {e}")

@celery_app.task
def backup_database():
    """Create automated database backup"""
    try:
        # This would integrate with the backup service
        from production_monitoring import DatabaseBackup
        backup_service = DatabaseBackup()
        backup_key = backup_service.create_backup()
        logger.info(f"Automated backup created: {backup_key}")
        return backup_key
    except Exception as e:
        logger.error(f"Automated backup failed: {e}")

# Celery Beat Schedule - Automated tasks
celery_app.conf.beat_schedule = {
    # Check for scheduled messages every minute
    'check-scheduled-messages': {
        'task': 'worker.check_scheduled_messages',
        'schedule': 60.0,
    },
    
    # Daily cleanup at 2 AM
    'daily-cleanup': {
        'task': 'worker.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Daily analytics at 9 AM
    'daily-analytics': {
        'task': 'worker.send_daily_analytics',
        'schedule': crontab(hour=9, minute=0),
    },
    
    # Google Sheets sync every 6 hours
    'sync-sheets-regular': {
        'task': 'worker.sync_all_coach_sheets',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    
    # Daily backup at 3 AM
    'daily-backup': {
        'task': 'worker.backup_database',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Weekly analytics report on Mondays at 10 AM
    'weekly-report': {
        'task': 'worker.send_weekly_report',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),
    }
}

@celery_app.task
def sync_all_coach_sheets():
    """Sync Google Sheets for all coaches"""
    try:
        async def _sync_all():
            conn = await get_db_connection()
            try:
                coaches = await conn.fetch("SELECT id FROM coaches WHERE is_active = true")
                
                for coach in coaches:
                    # Queue individual sync tasks
                    sync_google_sheets.delay(str(coach['id']))
                
                logger.info(f"Queued Google Sheets sync for {len(coaches)} coaches")
            
            finally:
                await conn.close()
        
        asyncio.run(_sync_all())
        
    except Exception as e:
        logger.error(f"Sync all coaches sheets failed: {e}")

@celery_app.task
def send_weekly_report():
    """Send weekly analytics report to coaches"""
    try:
        async def _weekly_report():
            conn = await get_db_connection()
            try:
                coaches = await conn.fetch("SELECT * FROM coaches WHERE is_active = true")
                
                for coach in coaches:
                    try:
                        # Get week's stats
                        week_start = datetime.now() - timedelta(days=7)
                        
                        weekly_stats = await conn.fetchrow(
                            """SELECT 
                                COUNT(*) as total_messages,
                                COUNT(CASE WHEN message_type = 'celebration' THEN 1 END) as celebrations,
                                COUNT(CASE WHEN message_type = 'accountability' THEN 1 END) as accountability,
                                COUNT(CASE WHEN delivery_status = 'read' THEN 1 END) as read_messages,
                                COUNT(DISTINCT client_id) as active_clients
                            FROM message_history 
                            WHERE coach_id = $1 AND sent_at >= $2""",
                            coach['id'], week_start
                        )
                        
                        # Get top performing clients
                        top_clients = await conn.fetch(
                            """SELECT 
                                c.name,
                                COUNT(mh.id) as messages_received,
                                COUNT(CASE WHEN mh.delivery_status = 'read' THEN 1 END) as messages_read
                            FROM clients c
                            JOIN message_history mh ON c.id = mh.client_id
                            WHERE c.coach_id = $1 AND mh.sent_at >= $2
                            GROUP BY c.id, c.name
                            ORDER BY messages_read DESC
                            LIMIT 5""",
                            coach['id'], week_start
                        )
                        
                        if weekly_stats['total_messages'] > 0:
                            engagement_rate = (weekly_stats['read_messages'] / weekly_stats['total_messages']) * 100
                            
                            report_message = f"""📊 **Weekly Coaching Report**
🗓️ {week_start.strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}

📈 **This Week's Impact:**
📤 Total messages sent: {weekly_stats['total_messages']}
🎉 Celebrations: {weekly_stats['celebrations']}
🎯 Accountability check-ins: {weekly_stats['accountability']}
👥 Active clients: {weekly_stats['active_clients']}
📖 Engagement rate: {engagement_rate:.1f}%

🌟 **Most Engaged Clients:**"""
                            
                            for i, client in enumerate(top_clients[:3], 1):
                                client_engagement = (client['messages_read'] / client['messages_received'] * 100) if client['messages_received'] > 0 else 0
                                report_message += f"\n{i}. {client['name']} ({client_engagement:.0f}% engagement)"
                            
                            report_message += "\n\nKeep inspiring your clients! 🚀"
                            
                            whatsapp_client = WhatsAppClient(
                                os.getenv("WHATSAPP_ACCESS_TOKEN"),
                                os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                            )
                            
                            await whatsapp_client.send_text_message(
                                coach['whatsapp_phone_number'],
                                report_message
                            )
                    
                    except Exception as e:
                        logger.error(f"Failed to send weekly report to coach {coach['id']}: {e}")
                
            finally:
                await conn.close()
        
        asyncio.run(_weekly_report())
        
    except Exception as e:
        logger.error(f"Weekly report task failed: {e}")

# Error handling and retry logic
@celery_app.task(bind=True)
def handle_failed_message(self, scheduled_message_id: str, error_details: str):
    """Handle failed message delivery with intelligent retry"""
    try:
        async def _handle_failed():
            conn = await get_db_connection()
            try:
                # Get message details
                message = await conn.fetchrow(
                    """SELECT sm.*, c.name as client_name, co.name as coach_name, co.whatsapp_phone_number
                       FROM scheduled_messages sm
                       JOIN clients c ON sm.client_id = c.id
                       JOIN coaches co ON sm.coach_id = co.id
                       WHERE sm.id = $1""",
                    scheduled_message_id
                )
                
                if not message:
                    return
                
                # Record the failure
                await conn.execute(
                    """INSERT INTO message_history 
                       (scheduled_message_id, coach_id, client_id, message_type, content, delivery_status, error_message, sent_at)
                       VALUES ($1, $2, $3, $4, $5, 'failed', $6, $7)""",
                    scheduled_message_id, message['coach_id'], message['client_id'],
                    message['message_type'], message['content'], error_details, datetime.now()
                )
                
                # Update scheduled message status
                await conn.execute(
                    "UPDATE scheduled_messages SET status = 'failed' WHERE id = $1",
                    scheduled_message_id
                )
                
                # Notify coach of failure
                whatsapp_client = WhatsAppClient(
                    os.getenv("WHATSAPP_ACCESS_TOKEN"),
                    os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                )
                
                failure_notification = f"""❌ **Message Delivery Failed**

👤 Client: {message['client_name']}
📝 Message type: {message['message_type']}
🕐 Scheduled time: {message['scheduled_time']}

Error: {error_details}

The message has been marked as failed. You can retry manually if needed."""
                
                await whatsapp_client.send_text_message(
                    message['whatsapp_phone_number'],
                    failure_notification
                )
                
            finally:
                await conn.close()
        
        asyncio.run(_handle_failed())
        
    except Exception as e:
        logger.error(f"Handle failed message task error: {e}")

# Worker startup and configuration
if __name__ == '__main__':
    # Set up logging
    from production_monitoring import setup_logging
    setup_logging()
    
    logger.info("Starting Celery worker for coaching system...")
    
    # Configure worker
    celery_app.conf.update(
        worker_log_color=False,
        worker_redirect_stdouts=True,
        worker_redirect_stdouts_level='INFO'
    )
    
    # Start worker
    celery_app.start(['worker', '--loglevel=info', '--concurrency=4'])