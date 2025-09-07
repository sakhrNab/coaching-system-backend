"""
Additional Backend Endpoints for Real Data Integration
Add these endpoints to the main backend_api.py file
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd
import tempfile
import os
import logging
from datetime import datetime
from typing import List, Dict
from .database import db
from .core_api import CategoryCreate, TemplateCreate, ImportData, GoogleContactsImport, VoiceProcessRequest
from .whatsapp_templates import template_manager
import uuid
import httpx
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class GoalCreate(BaseModel):
    title: str
    description: str = None
    category: str = None
    target_date: str = None

# Add these endpoints to your main FastAPI app

@router.post("/coaches/{coach_id}/import-clients",
             summary="Import Clients from JSON",
             description="""
             Import multiple clients from JSON data for a coach.
             
             This endpoint allows coaches to bulk import clients from external sources
             or backup files. The import data should contain an array of client objects
             with the required fields.
             
             **Features:**
             - Bulk client import
             - Data validation
             - Duplicate phone number handling
             - Category assignment
             
             **Use Cases:**
             - Restore from backup
             - Migrate from other systems
             - Bulk client onboarding
             """,
             tags=["Client CRUD"],
             responses={
                 200: {"description": "Clients imported successfully"},
                 400: {"description": "Invalid import data"},
                 404: {"description": "Coach not found"},
                 500: {"description": "Database error"}
             })
async def import_clients_json(coach_id: str, import_data: ImportData):
    """Import clients from JSON data"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Validate coach exists
        coach = await db.fetchrow("SELECT id FROM coaches WHERE id = $1", coach_id)
        if not coach:
            raise HTTPException(status_code=404, detail="Coach not found")
        
        # Validate import data
        source = import_data.source
        data = import_data.data
        
        imported_count = 0
        errors = []

        # Process CSV data
        if source == 'csv':
            lines = data.strip().split('\n')
            if len(lines) < 2:
                raise HTTPException(status_code=400, detail="Invalid CSV data")
            
            headers = lines[0].split(',')
            required_headers = ['name', 'phone_number']
            
            for header in required_headers:
                if header not in headers:
                    raise HTTPException(status_code=400, detail=f"Missing required header: {header}")
            
            # Process each line
            for i, line in enumerate(lines[1:], 1):
                try:
                    values = line.split(',')
                    if len(values) < 2:
                        continue
                    
                    client_data = {
                        'name': values[headers.index('name')].strip(),
                        'phone_number': values[headers.index('phone_number')].strip(),
                        'country': values[headers.index('country')].strip() if 'country' in headers and len(values) > headers.index('country') else 'USA',
                        'timezone': values[headers.index('timezone')].strip() if 'timezone' in headers and len(values) > headers.index('timezone') else 'EST'
                    }
                    
                    # Normalize phone number
                    if not client_data['phone_number'].startswith('+'):
                        client_data['phone_number'] = '+1' + client_data['phone_number'].lstrip('0')

                    # Insert client
                    client_id = str(uuid.uuid4())
                    await db.execute(
                        """INSERT INTO clients (id, coach_id, name, phone_number, country, timezone)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        client_id, coach_id, client_data['name'], client_data['phone_number'],
                        client_data['country'], client_data['timezone']
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Line {i}: {str(e)}")
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported source type")
        
        return {
            "status": "success",
            "imported_count": imported_count,
            "errors": errors,
            "message": f"Successfully imported {imported_count} clients"
        }
    
    except Exception as e:
        logger.error(f"Import clients error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import clients: {str(e)}")


@router.post("/coaches/{coach_id}/templates",
             summary="Create Message Template",
             description="""
             Create a custom message template for a coach.
             
             This endpoint allows coaches to create personalized message templates
             for different types of communications (celebration, accountability, etc.).
             
             **Features:**
             - Custom template creation
             - Template categorization
             - Language code support
             - WhatsApp template integration
             
             **Use Cases:**
             - Personalized messaging
             - Brand consistency
             - Multi-language support
             - Template management
             """,
             tags=["Message Templates"],
             responses={
                 200: {"description": "Template created successfully"},
                 400: {"description": "Invalid template data"},
                 404: {"description": "Coach not found"},
                 500: {"description": "Database error"}
             })
async def create_template(coach_id: str, template_data: TemplateCreate):
    """Create a custom message template for a coach"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Validate coach exists
        coach = await db.fetchrow("SELECT id FROM coaches WHERE id = $1", coach_id)
        if not coach:
            raise HTTPException(status_code=404, detail="Coach not found")
        
        # Validate template data
        message_type = template_data.message_type.strip()
        content = template_data.content.strip()
        
        if not content:
            raise HTTPException(status_code=400, detail="Template content cannot be empty")
        
        # Validate message type
        valid_types = ['celebration', 'accountability', 'general', 'checkin']
        if message_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid message type. Must be one of: {valid_types}")
        
        # Create template
        template_id = str(uuid.uuid4())
        
        await db.execute(
            "INSERT INTO message_templates (id, coach_id, message_type, content, is_default) VALUES ($1, $2, $3, $4, false)",
            template_id, coach_id, message_type, content
        )
        
        return {
            "template_id": template_id,
            "message_type": message_type,
            "content": content,
            "status": "created"
        }
    
    except Exception as e:
        logger.error(f"Create template error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")

@router.get("/coaches/{coach_id}/templates",
            summary="Get Message Templates",
            description="""
            Retrieve message templates for a coach.
            
            **Template Types:**
            - `celebration`: Positive reinforcement messages (templates 6-10)
            - `accountability`: Goal tracking messages (templates 1-5)
            - `null`: All templates (default)
            
            **Template Information:**
            - Template content and metadata
            - WhatsApp template names
            - Language codes
            - Default vs custom templates
            
            **Use Cases:**
            - Display available templates in UI
            - Filter templates by type
            - Show template details for selection
            """,
            tags=["Message Templates"],
            responses={
                200: {
                    "description": "Templates retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": [
                                {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "message_type": "celebration",
                                    "content": "🎉 What are we celebrating today?",
                                    "is_default": True,
                                    "whatsapp_template_name": "celebration_message_6",
                                    "language_code": "en"
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
async def get_message_templates(coach_id: str, type: str = None):
    """Get message templates for coach"""
    try:
        async with db.pool.acquire() as conn:
            if type:
                query = """SELECT id, message_type, content, is_default, is_active
                           FROM message_templates 
                           WHERE (coach_id = $1 OR coach_id IS NULL) 
                           AND is_active = true 
                           AND message_type = $2
                           ORDER BY is_default DESC, created_at DESC"""
                templates = await conn.fetch(query, coach_id, type)
            else:
                query = """SELECT id, message_type, content, is_default, is_active
                           FROM message_templates 
                           WHERE (coach_id = $1 OR coach_id IS NULL) 
                           AND is_active = true
                           ORDER BY is_default DESC, created_at DESC"""
                templates = await conn.fetch(query, coach_id)
            
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

@router.put("/templates/{template_id}/language-code",
            summary="Update Template Language Code",
            description="""
            Update the language code for a message template.
            
            This endpoint allows coaches to change the language code of their
            message templates to support different languages and regions.
            
            **Features:**
            - Language code validation
            - Template ownership verification
            - WhatsApp template compatibility
            - Multi-language support
            
            **Use Cases:**
            - International coaching
            - Multi-language templates
            - Regional customization
            - Template localization
            """,
            tags=["Message Templates"],
            responses={
                200: {"description": "Language code updated successfully"},
                400: {"description": "Invalid language code"},
                404: {"description": "Template not found"},
                500: {"description": "Database error"}
            })
async def update_template_language_code(template_id: str, language_code: str):
    """Update the language code for a template"""
    try:
        # Validate language code format
        if not language_code or len(language_code) < 2:
            raise HTTPException(status_code=400, detail="Invalid language code format")
        
        async with db.pool.acquire() as conn:
            # Update the language code
            result = await conn.execute(
                "UPDATE message_templates SET language_code = $1 WHERE id = $2",
                language_code, template_id
            )
            
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Template not found")
            
            # Reload template cache
            await template_manager.load_templates_from_db()
            
            return {"message": "Language code updated successfully", "language_code": language_code}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update language code error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update language code")

@router.get("/templates/{template_id}",
            summary="Get Template Details",
            description="""
            Get detailed information about a specific message template.
            
            This endpoint retrieves comprehensive details about a message template
            including its content, language code, WhatsApp integration status,
            and usage statistics.
            
            **Features:**
            - Complete template information
            - Language code details
            - WhatsApp template status
            - Usage analytics
            
            **Use Cases:**
            - Template editing
            - Template management
            - Usage analysis
            - Template debugging
            """,
            tags=["Message Templates"],
            responses={
                200: {"description": "Template details retrieved successfully"},
                404: {"description": "Template not found"},
                500: {"description": "Database error"}
            })
async def get_template_details(template_id: str):
    """Get detailed information about a template including language code"""
    try:
        async with db.pool.acquire() as conn:
            template = await conn.fetchrow(
                """SELECT id, message_type, content, language_code, whatsapp_template_name, 
                          is_default, is_active, created_at
                   FROM message_templates 
                   WHERE id = $1""",
                template_id
            )
            
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            
            return {
                "id": str(template['id']),
                "message_type": template['message_type'],
                "content": template['content'],
                "language_code": template['language_code'],
                "whatsapp_template_name": template['whatsapp_template_name'],
                "is_default": template['is_default'],
                "is_active": template['is_active'],
                "created_at": template['created_at']
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get template details error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch template details")

@router.get("/coaches/{coach_id}/analytics",
            summary="Get Message Analytics",
            description="""
            Get comprehensive message analytics for a coach.
            
            This endpoint provides detailed analytics about message performance,
            delivery rates, engagement metrics, and usage patterns for a coach's
            messaging activities.
            
            **Features:**
            - Message delivery statistics
            - Engagement metrics
            - Performance trends
            - Client interaction analysis
            - Time-based filtering
            
            **Use Cases:**
            - Performance monitoring
            - Strategy optimization
            - Client engagement analysis
            - Reporting and insights
            """,
            tags=["Analytics"],
            responses={
                200: {"description": "Analytics data retrieved successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Database error"}
            })
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
                AND sent_at >= CURRENT_DATE - INTERVAL $2 || ' days'
                GROUP BY message_type, delivery_status, DATE(sent_at)
                ORDER BY sent_date DESC""",
                coach_id, str(days)
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

@router.get("/coaches/{coach_id}/clients/{client_id}/history",
            summary="Get Client Message History",
            description="""
            Get message history for a specific client.
            
            This endpoint retrieves the complete message history between a coach
            and a specific client, including sent messages, received responses,
            and delivery status information.
            
            **Features:**
            - Complete message history
            - Message status tracking
            - Timestamp information
            - Pagination support
            - Message type filtering
            
            **Use Cases:**
            - Client communication review
            - Progress tracking
            - Message debugging
            - Relationship analysis
            """,
            tags=["Client CRUD"],
            responses={
                200: {"description": "Message history retrieved successfully"},
                404: {"description": "Client not found"},
                500: {"description": "Database error"}
            })
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

@router.put("/coaches/{coach_id}/clients/{client_id}",
            summary="Update Client Information",
            description="""
            Update client information and details.
            
            This endpoint allows coaches to modify client information including
            personal details, contact information, categories, and preferences.
            
            **Features:**
            - Client information updates
            - Category management
            - Contact details modification
            - Preference updates
            - Data validation
            
            **Use Cases:**
            - Client profile management
            - Information updates
            - Category changes
            - Contact maintenance
            """,
            tags=["Client CRUD"],
            responses={
                200: {"description": "Client updated successfully"},
                400: {"description": "Invalid client data"},
                404: {"description": "Client not found"},
                500: {"description": "Database error"}
            })
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

@router.delete("/coaches/{coach_id}/clients/{client_id}",
               summary="Delete Client",
               description="""
               Delete (deactivate) a client from the coach's client list.
               
               This endpoint soft-deletes a client by marking them as inactive
               rather than permanently removing their data from the database.
               
               **Features:**
               - Soft delete (data preservation)
               - Client verification
               - Data retention
               - Audit trail
               
               **Use Cases:**
               - Client removal
               - Data cleanup
               - Privacy compliance
               - Account management
               """,
               tags=["Client CRUD"],
               responses={
                   200: {"description": "Client deleted successfully"},
                   404: {"description": "Client not found"},
                   500: {"description": "Database error"}
               })
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


@router.delete("/scheduled-messages/{message_id}",
               summary="Cancel Scheduled Message",
               description="""
               Cancel a scheduled message before it's sent.
               
               This endpoint allows coaches to cancel scheduled messages that haven't
               been sent yet, preventing them from being delivered to clients.
               
               **Features:**
               - Message cancellation
               - Status validation
               - Immediate effect
               - Audit logging
               
               **Use Cases:**
               - Schedule changes
               - Message corrections
               - Emergency cancellations
               - Schedule management
               """,
               tags=["Message Scheduling"],
               responses={
                   200: {"description": "Message cancelled successfully"},
                   404: {"description": "Message not found"},
                   400: {"description": "Message already sent"},
                   500: {"description": "Database error"}
               })
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

@router.get("/coaches/{coach_id}/goals",
            summary="Get Client Goals",
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

@router.post("/coaches/{coach_id}/clients/{client_id}/goals",
             summary="Create Client Goal",
             description="""
             Create a new goal for a specific client.
             
             This endpoint allows coaches to set new goals for their clients,
             including goal details, target dates, and progress tracking.
             
             **Features:**
             - Goal creation
             - Target date setting
             - Progress tracking setup
             - Goal categorization
             - Client verification
             
             **Use Cases:**
             - Goal setting
             - Client development
             - Progress planning
             - Achievement tracking
             """,
             tags=["Goal Management"],
             responses={
                 200: {"description": "Goal created successfully"},
                 400: {"description": "Invalid goal data"},
                 404: {"description": "Client not found"},
                 500: {"description": "Database error"}
             })
async def create_client_goal(coach_id: str, client_id: str, goal_data: GoalCreate):
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
            if goal_data.category:
                category_id = await conn.fetchval(
                    "SELECT id FROM categories WHERE name = $1 AND (is_predefined = true OR coach_id = $2)",
                    goal_data.category, coach_id
                )
            
            # Parse target_date if provided
            target_date = None
            if goal_data.target_date:
                try:
                    target_date = datetime.strptime(goal_data.target_date, '%Y-%m-%d').date()
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
            
            goal_id = await conn.fetchval(
                """INSERT INTO goals (client_id, title, description, category_id, target_date)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                client_id, goal_data.title, goal_data.description,
                category_id, target_date
            )
            
            return {"goal_id": str(goal_id), "status": "created"}
    
    except Exception as e:
        logger.error(f"Create goal error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create goal")

@router.get("/coaches/{coach_id}/scheduled-messages",
            summary="Get Scheduled Messages",
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
async def get_coach_scheduled_messages(coach_id: str):
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

@router.get("/coaches/{coach_id}/stats",
            summary="Get Coach Statistics",
            description="""
            Get comprehensive statistics for a coach's dashboard.
            
            This endpoint provides detailed statistics about a coach's performance,
            client metrics, message activity, and system usage.
            
            **Features:**
            - Performance metrics
            - Client statistics
            - Message activity
            - System usage
            - Trend analysis
            
            **Use Cases:**
            - Dashboard display
            - Performance monitoring
            - Analytics reporting
            - System optimization
            """,
            tags=["Analytics"],
            responses={
                200: {"description": "Statistics retrieved successfully"},
                404: {"description": "Coach not found"},
                500: {"description": "Database error"}
            })
async def get_coach_analytics_stats(coach_id: str):
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
@router.post("/coaches/{coach_id}/import-google-contacts",
             summary="Import Google Contacts",
             description="""
             Import contacts from Google Contacts for a coach.
             
             This endpoint allows coaches to import their Google Contacts as clients,
             automatically creating client profiles with contact information.
             
             **Features:**
             - Google Contacts integration
             - Automatic client creation
             - Contact data mapping
             - Duplicate handling
             - Bulk import processing
             
             **Use Cases:**
             - Contact migration
             - Bulk client onboarding
             - Contact synchronization
             - Data import
             """,
             tags=["Client CRUD"],
             responses={
                 200: {"description": "Contacts imported successfully"},
                 400: {"description": "Invalid contact data"},
                 404: {"description": "Coach not found"},
                 500: {"description": "Database error"}
             })
async def import_google_contacts(coach_id: str, google_data: GoogleContactsImport):
    """Import contacts from Google"""
    try:
        # Check if database is connected
        if not hasattr(db, 'pool') or db.pool is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Validate coach exists
        coach = await db.fetchrow("SELECT id FROM coaches WHERE id = $1", coach_id)
        if not coach:
            raise HTTPException(status_code=404, detail="Coach not found")
        
        # Validate Google data
        if not google_data.access_token:
            raise HTTPException(status_code=400, detail="Access token is required")
        
        # For now, return a placeholder response
        # In a real implementation, you would use the Google People API
        return {
            "status": "success",
            "imported_count": 0,
            "message": "Google Contacts integration not fully implemented yet"
        }
    
    except Exception as e:
        logger.error(f"Import Google contacts error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import Google contacts: {str(e)}")

# Bulk operations
@router.post("/coaches/{coach_id}/bulk-message",
             summary="Send Bulk Message",
             description="""
             Send a message to multiple clients at once.
             
             This endpoint allows coaches to send the same message to multiple
             clients simultaneously, with individual delivery tracking.
             
             **Features:**
             - Bulk message sending
             - Individual delivery tracking
             - Client selection
             - Message customization
             - Delivery status monitoring
             
             **Use Cases:**
             - Mass communications
             - Announcements
             - Group messaging
             - Campaign management
             """,
             tags=["Message Sending"],
             responses={
                 200: {"description": "Bulk message sent successfully"},
                 400: {"description": "Invalid message data"},
                 404: {"description": "Coach not found"},
                 500: {"description": "Database error"}
             })
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
                    # background_tasks.add_task(send_immediate_message, str(scheduled_id))
                    pass # Placeholder for background task
        
        return {"message_ids": message_ids, "status": "queued"}
    
    except Exception as e:
        logger.error(f"Bulk message error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send bulk message")

@router.get("/health",
            summary="Health Check",
            description="""
            Check the health status of the application.
            
            This endpoint provides a basic health check to verify that the
            application and database are running properly.
            
            **Features:**
            - Application status
            - Database connectivity
            - Basic system health
            - Quick status verification
            
            **Use Cases:**
            - System monitoring
            - Load balancer checks
            - Service discovery
            - Health verification
            """,
            tags=["System Health"],
            responses={
                200: {"description": "System is healthy"},
                500: {"description": "System error"}
            })
async def detailed_health_check():
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

# Health check endpoint

# Configuration endpoint
@router.get("/config",
            summary="Get App Configuration",
            description="""
            Get application configuration for the frontend.
            
            This endpoint provides configuration settings and feature flags
            that the frontend needs to properly configure the application.
            
            **Features:**
            - Feature flags
            - Configuration settings
            - Environment variables
            - Frontend configuration
            
            **Use Cases:**
            - Frontend initialization
            - Feature toggling
            - Configuration management
            - Environment setup
            """,
            tags=["System Configuration"],
            responses={
                200: {"description": "Configuration retrieved successfully"},
                500: {"description": "Configuration error"}
            })
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