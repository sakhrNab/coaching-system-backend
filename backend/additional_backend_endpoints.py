"""
Additional Backend Endpoints for Real Data Integration
Add these endpoints to the main backend_api.py file
"""

from fastapi import APIRouter, UploadFile, File
import pandas as pd
import tempfile
import os
import logging
from datetime import datetime
from typing import List, Dict
from .database import db

logger = logging.getLogger(__name__)
router = APIRouter()

# Add these endpoints to your main FastAPI app

@router.post("/coaches/{coach_id}/import-clients")
async def import_clients_from_file(coach_id: str, file: UploadFile = File(...)):
    """Import clients from CSV/Excel file"""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Read file based on extension
            if file.filename.endswith('.csv'):
                df = pd.read_csv(temp_file_path)
            elif file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(temp_file_path)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")

            # Validate required columns
            required_columns = ['name', 'phone_number']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Missing required columns: {missing_columns}"
                )

            # Process and import clients
            imported_count = 0
            errors = []

            async with db.pool.acquire() as conn:
                for index, row in df.iterrows():
                    try:
                        # Prepare client data
                        client_data = {
                            'name': str(row['name']).strip(),
                            'phone_number': str(row['phone_number']).strip(),
                            'country': str(row.get('country', 'USA')).strip(),
                            'timezone': str(row.get('timezone', 'EST')).strip(),
                        }

                        # Validate phone number format (basic)
                        if not client_data['phone_number'].startswith('+'):
                            client_data['phone_number'] = '+1' + client_data['phone_number'].lstrip('0')

                        # Insert client
                        client_id = await conn.fetchval(
                            """INSERT INTO clients (coach_id, name, phone_number, country, timezone)
                               VALUES ($1, $2, $3, $4, $5) 
                               ON CONFLICT (coach_id, phone_number) DO NOTHING
                               RETURNING id""",
                            coach_id, client_data['name'], client_data['phone_number'],
                            client_data['country'], client_data['timezone']
                        )

                        if client_id:
                            # Handle categories if present
                            if 'categories' in row and pd.notna(row['categories']):
                                categories = [cat.strip() for cat in str(row['categories']).split(',')]
                                
                                for category_name in categories:
                                    if category_name:
                                        # Find or create category
                                        category_id = await conn.fetchval(
                                            """SELECT id FROM categories 
                                               WHERE name = $1 AND (is_predefined = true OR coach_id = $2)""",
                                            category_name, coach_id
                                        )
                                        
                                        if not category_id:
                                            # Create custom category
                                            category_id = await conn.fetchval(
                                                "INSERT INTO categories (name, coach_id, is_predefined) VALUES ($1, $2, false) RETURNING id",
                                                category_name, coach_id
                                            )
                                        
                                        # Link client to category
                                        await conn.execute(
                                            "INSERT INTO client_categories (client_id, category_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                                            client_id, category_id
                                        )

                            imported_count += 1

                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")

            return {
                "status": "success",
                "count": imported_count,
                "errors": errors[:10]  # Limit error messages
            }

        finally:
            # Clean up temp file
            os.unlink(temp_file_path)

    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@router.get("/coaches/{coach_id}/templates")
async def get_message_templates(coach_id: str, message_type: str = None):
    """Get message templates for coach"""
    try:
        async with db.pool.acquire() as conn:
            query = """SELECT id, message_type, content, is_default, is_active
                       FROM message_templates 
                       WHERE (coach_id = $1 OR coach_id IS NULL) AND is_active = true"""
            
            params = [coach_id]
            
            if message_type:
                query += " AND message_type = $2"
                params.append(message_type)
            
            query += " ORDER BY is_default DESC, created_at DESC"
            
            templates = await conn.fetch(query, *params)
            
            return [
                {
                    "id": str(template['id']),
                    "message_type": template['message_type'],
                    "content": template['content'],
                    "is_default": template['is_default']
                } for template in templates
            ]
    
    except Exception as e:
        logger.error(f"Get templates error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch templates")

@router.post("/coaches/{coach_id}/templates")
async def create_message_template(coach_id: str, template_data: dict):
    """Create custom message template"""
    try:
        async with db.pool.acquire() as conn:
            template_id = await conn.fetchval(
                """INSERT INTO message_templates (coach_id, message_type, content, is_default, is_active)
                   VALUES ($1, $2, $3, false, true) RETURNING id""",
                coach_id, template_data['message_type'], template_data['content']
            )
            
            return {"template_id": str(template_id), "status": "created"}
    
    except Exception as e:
        logger.error(f"Create template error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")

@router.get("/coaches/{coach_id}/analytics")
async def get_message_analytics(coach_id: str, days: int = 30):
    """Get message analytics for coach"""
    try:
        async with db.pool.acquire() as conn:
            # Get message counts by type and status
            analytics = await conn.fetch(
                """SELECT 
                    message_type,
                    delivery_status,
                    DATE(sent_at) as sent_date,
                    COUNT(*) as count
                FROM message_history 
                WHERE coach_id = $1 
                AND sent_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY message_type, delivery_status, DATE(sent_at)
                ORDER BY sent_date DESC""",
                coach_id, days
            )
            
            # Get client engagement stats
            engagement = await conn.fetch(
                """SELECT 
                    c.name,
                    COUNT(mh.id) as total_messages,
                    COUNT(CASE WHEN mh.delivery_status = 'delivered' THEN 1 END) as delivered,
                    COUNT(CASE WHEN mh.delivery_status = 'read' THEN 1 END) as read,
                    MAX(mh.sent_at) as last_message
                FROM clients c
                LEFT JOIN message_history mh ON c.id = mh.client_id
                WHERE c.coach_id = $1 AND c.is_active = true
                GROUP BY c.id, c.name
                ORDER BY total_messages DESC""",
                coach_id
            )
            
            return {
                "message_analytics": [dict(row) for row in analytics],
                "client_engagement": [dict(row) for row in engagement]
            }
    
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")

@router.get("/coaches/{coach_id}/clients/{client_id}/history")
async def get_client_message_history(coach_id: str, client_id: str, limit: int = 50):
    """Get message history for specific client"""
    try:
        async with db.pool.acquire() as conn:
            history = await conn.fetch(
                """SELECT 
                    message_type,
                    content,
                    delivery_status,
                    sent_at,
                    delivered_at,
                    read_at
                FROM message_history 
                WHERE coach_id = $1 AND client_id = $2 
                ORDER BY sent_at DESC 
                LIMIT $3""",
                coach_id, client_id, limit
            )
            
            return [
                {
                    "message_type": msg['message_type'],
                    "content": msg['content'],
                    "status": msg['delivery_status'],
                    "sent_at": msg['sent_at'].isoformat() if msg['sent_at'] else None,
                    "delivered_at": msg['delivered_at'].isoformat() if msg['delivered_at'] else None,
                    "read_at": msg['read_at'].isoformat() if msg['read_at'] else None
                } for msg in history
            ]
    
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")

@router.put("/coaches/{coach_id}/clients/{client_id}")
async def update_client(coach_id: str, client_id: str, client_data: dict):
    """Update client information"""
    try:
        async with db.pool.acquire() as conn:
            # Update basic client info
            await conn.execute(
                """UPDATE clients 
                   SET name = $1, phone_number = $2, country = $3, timezone = $4, updated_at = CURRENT_TIMESTAMP
                   WHERE id = $5 AND coach_id = $6""",
                client_data['name'], client_data['phone_number'], 
                client_data['country'], client_data['timezone'],
                client_id, coach_id
            )
            
            # Update categories if provided
            if 'categories' in client_data:
                # Remove existing categories
                await conn.execute(
                    "DELETE FROM client_categories WHERE client_id = $1",
                    client_id
                )
                
                # Add new categories
                for category_name in client_data['categories']:
                    category_id = await conn.fetchval(
                        """SELECT id FROM categories 
                           WHERE name = $1 AND (is_predefined = true OR coach_id = $2)""",
                        category_name, coach_id
                    )
                    
                    if category_id:
                        await conn.execute(
                            "INSERT INTO client_categories (client_id, category_id) VALUES ($1, $2)",
                            client_id, category_id
                        )
            
            return {"status": "updated"}
    
    except Exception as e:
        logger.error(f"Update client error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update client")

@router.delete("/coaches/{coach_id}/clients/{client_id}")
async def delete_client(coach_id: str, client_id: str):
    """Delete (deactivate) client"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE clients SET is_active = false WHERE id = $1 AND coach_id = $2",
                client_id, coach_id
            )
            
            return {"status": "deleted"}
    
    except Exception as e:
        logger.error(f"Delete client error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete client")

@router.get("/coaches/{coach_id}/scheduled-messages")
async def get_scheduled_messages(coach_id: str):
    """Get all scheduled messages for coach"""
    try:
        async with db.pool.acquire() as conn:
            messages = await conn.fetch(
                """SELECT 
                    sm.id,
                    sm.message_type,
                    sm.content,
                    sm.schedule_type,
                    sm.scheduled_time,
                    sm.status,
                    c.name as client_name,
                    c.phone_number
                FROM scheduled_messages sm
                JOIN clients c ON sm.client_id = c.id
                WHERE sm.coach_id = $1 AND sm.status IN ('scheduled', 'pending')
                ORDER BY sm.scheduled_time ASC""",
                coach_id
            )
            
            return [
                {
                    "id": str(msg['id']),
                    "message_type": msg['message_type'],
                    "content": msg['content'],
                    "schedule_type": msg['schedule_type'],
                    "scheduled_time": msg['scheduled_time'].isoformat() if msg['scheduled_time'] else None,
                    "status": msg['status'],
                    "client_name": msg['client_name'],
                    "client_phone": msg['phone_number']
                } for msg in messages
            ]
    
    except Exception as e:
        logger.error(f"Get scheduled messages error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scheduled messages")

@router.delete("/scheduled-messages/{message_id}")
async def cancel_scheduled_message(message_id: str):
    """Cancel a scheduled message"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE scheduled_messages SET status = 'cancelled' WHERE id = $1",
                message_id
            )
            
            return {"status": "cancelled"}
    
    except Exception as e:
        logger.error(f"Cancel message error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel message")

@router.get("/coaches/{coach_id}/goals")
async def get_client_goals(coach_id: str):
    """Get goals for all coach's clients"""
    try:
        async with db.pool.acquire() as conn:
            goals = await conn.fetch(
                """SELECT 
                    g.id,
                    g.title,
                    g.description,
                    g.target_date,
                    g.is_achieved,
                    c.name as client_name,
                    cat.name as category_name
                FROM goals g
                JOIN clients c ON g.client_id = c.id
                LEFT JOIN categories cat ON g.category_id = cat.id
                WHERE c.coach_id = $1 AND c.is_active = true
                ORDER BY g.target_date ASC""",
                coach_id
            )
            
            return [
                {
                    "id": str(goal['id']),
                    "title": goal['title'],
                    "description": goal['description'],
                    "target_date": goal['target_date'].isoformat() if goal['target_date'] else None,
                    "is_achieved": goal['is_achieved'],
                    "client_name": goal['client_name'],
                    "category": goal['category_name']
                } for goal in goals
            ]
    
    except Exception as e:
        logger.error(f"Get goals error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch goals")

@router.post("/coaches/{coach_id}/clients/{client_id}/goals")
async def create_client_goal(coach_id: str, client_id: str, goal_data: dict):
    """Create a new goal for client"""
    try:
        async with db.pool.acquire() as conn:
            # Verify client belongs to coach
            client = await conn.fetchrow(
                "SELECT id FROM clients WHERE id = $1 AND coach_id = $2",
                client_id, coach_id
            )
            
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            
            # Get category ID if provided
            category_id = None
            if 'category' in goal_data:
                category_id = await conn.fetchval(
                    "SELECT id FROM categories WHERE name = $1 AND (is_predefined = true OR coach_id = $2)",
                    goal_data['category'], coach_id
                )
            
            goal_id = await conn.fetchval(
                """INSERT INTO goals (client_id, title, description, category_id, target_date)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                client_id, goal_data['title'], goal_data.get('description'),
                category_id, goal_data.get('target_date')
            )
            
            return {"goal_id": str(goal_id), "status": "created"}
    
    except Exception as e:
        logger.error(f"Create goal error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create goal")

@router.get("/coaches/{coach_id}/stats")
async def get_coach_stats(coach_id: str):
    """Get comprehensive stats for coach dashboard"""
    try:
        async with db.pool.acquire() as conn:
            # Basic counts
            stats = await conn.fetchrow(
                """SELECT 
                    (SELECT COUNT(*) FROM clients WHERE coach_id = $1 AND is_active = true) as total_clients,
                    (SELECT COUNT(*) FROM message_history WHERE coach_id = $1 AND sent_at >= CURRENT_DATE - INTERVAL '30 days') as messages_sent_month,
                    (SELECT COUNT(*) FROM scheduled_messages WHERE coach_id = $1 AND status = 'scheduled') as pending_messages,
                    (SELECT COUNT(*) FROM goals g JOIN clients c ON g.client_id = c.id WHERE c.coach_id = $1 AND g.is_achieved = false) as active_goals""",
                coach_id
            )
            
            # Recent activity
            recent_activity = await conn.fetch(
                """SELECT 
                    'message_sent' as activity_type,
                    c.name as client_name,
                    mh.message_type,
                    mh.sent_at as timestamp
                FROM message_history mh
                JOIN clients c ON mh.client_id = c.id
                WHERE mh.coach_id = $1
                ORDER BY mh.sent_at DESC
                LIMIT 10""",
                coach_id
            )
            
            return {
                "total_clients": stats['total_clients'],
                "messages_sent_month": stats['messages_sent_month'],
                "pending_messages": stats['pending_messages'],
                "active_goals": stats['active_goals'],
                "recent_activity": [
                    {
                        "type": activity['activity_type'],
                        "client_name": activity['client_name'],
                        "message_type": activity['message_type'],
                        "timestamp": activity['timestamp'].isoformat() if activity['timestamp'] else None
                    } for activity in recent_activity
                ]
            }
    
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")

# Enhanced Google Contacts integration
@router.post("/coaches/{coach_id}/import-google-contacts")
async def import_google_contacts(coach_id: str, access_token: str):
    """Import contacts from Google Contacts API"""
    try:
        # Fetch contacts from Google People API
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://people.googleapis.com/v1/people/me/connections",
                params={
                    "personFields": "names,phoneNumbers,emailAddresses"
                },
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch Google contacts")
            
            contacts_data = response.json()
            connections = contacts_data.get('connections', [])
            
            imported_count = 0
            
            async with db.pool.acquire() as conn:
                for contact in connections:
                    if not contact.get('names') or not contact.get('phoneNumbers'):
                        continue
                    
                    name = contact['names'][0].get('displayName', '')
                    phone = contact['phoneNumbers'][0].get('value', '')
                    
                    if name and phone:
                        try:
                            # Clean phone number
                            clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                            if not clean_phone.startswith('+'):
                                clean_phone = '+1' + clean_phone
                            
                            await conn.execute(
                                """INSERT INTO clients (coach_id, name, phone_number, country, timezone)
                                   VALUES ($1, $2, $3, 'USA', 'EST')
                                   ON CONFLICT (coach_id, phone_number) DO NOTHING""",
                                coach_id, name, clean_phone
                            )
                            imported_count += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to import contact {name}: {e}")
                            continue
            
            return {"status": "success", "imported_count": imported_count}
    
    except Exception as e:
        logger.error(f"Google contacts import error: {e}")
        raise HTTPException(status_code=500, detail="Failed to import Google contacts")

# Bulk operations
@router.post("/coaches/{coach_id}/bulk-message")
async def send_bulk_message(coach_id: str, bulk_data: dict):
    """Send message to multiple clients at once"""
    try:
        client_ids = bulk_data['client_ids']
        message_content = bulk_data['content']
        message_type = bulk_data.get('message_type', 'general')
        schedule_type = bulk_data.get('schedule_type', 'now')
        
        message_ids = []
        
        async with db.pool.acquire() as conn:
            for client_id in client_ids:
                scheduled_id = await conn.fetchval(
                    """INSERT INTO scheduled_messages 
                       (coach_id, client_id, message_type, content, schedule_type, status)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       RETURNING id""",
                    coach_id, client_id, message_type, message_content, 
                    schedule_type, 'pending' if schedule_type == 'now' else 'scheduled'
                )
                message_ids.append(str(scheduled_id))
                
                # Send immediately if requested
                if schedule_type == 'now':
                    # Add to background task queue
                    background_tasks.add_task(send_immediate_message, str(scheduled_id))
        
        return {"message_ids": message_ids, "status": "queued"}
    
    except Exception as e:
        logger.error(f"Bulk message error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send bulk message")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected",
            "error": str(e)
        }

# Configuration endpoint
@router.get("/config")
async def get_app_config():
    """Get app configuration for frontend"""
    return {
        "features": {
            "google_contacts": bool(os.getenv("GOOGLE_CLIENT_ID")),
            "voice_processing": bool(os.getenv("OPENAI_API_KEY")),
            "whatsapp_integration": True,
            "google_sheets": bool(os.getenv("GOOGLE_CLIENT_ID"))
        },
        "timezones": ["EST", "PST", "CST", "MST", "GMT", "CET", "JST", "AEST"],
        "supported_file_types": [".csv", ".xlsx", ".xls"],
        "max_file_size": "10MB"
    }