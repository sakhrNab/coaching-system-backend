"""
Enhanced WhatsApp Webhook Handler
Handles conversation tracking and 24-hour window management
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from .database import db

logger = logging.getLogger(__name__)

router = APIRouter()

def verify_webhook_token(token: str) -> bool:
    """Verify webhook token"""
    expected_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "test-verify-token")
    return token == expected_token

@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
):
    """Verify webhook endpoint"""
    expected_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "test-verify-token")
    
    logger.info(f"🔍 Webhook verification attempt:")
    logger.info(f"   hub_mode: {hub_mode}")
    logger.info(f"   hub_verify_token: {hub_verify_token}")
    logger.info(f"   expected_token: {expected_token}")
    logger.info(f"   tokens_match: {hub_verify_token == expected_token}")
    
    if hub_mode == "subscribe" and verify_webhook_token(hub_verify_token):
        logger.info("✅ Webhook verified successfully")
        return int(hub_challenge)
    else:
        logger.warning(f"❌ Webhook verification failed: mode={hub_mode}, token={hub_verify_token}")
        raise HTTPException(status_code=403, detail="Forbidden")

@router.post("/whatsapp")
async def handle_webhook(request: Request):
    """Handle incoming WhatsApp webhooks"""
    try:
        body = await request.json()
        logger.info(f"📥 Received webhook: {json.dumps(body, indent=2)}")
        
        # Store webhook for processing
        async with db.pool.acquire() as conn:
            webhook_id = await conn.fetchval(
                "INSERT INTO whatsapp_webhooks (webhook_data, processing_status) VALUES ($1, 'received') RETURNING id",
                json.dumps(body)
            )
            logger.info(f"💾 Stored webhook with ID: {webhook_id}")
        
        # Process webhook data
        await process_webhook_data(body)
        
        # Mark as processed
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE whatsapp_webhooks SET processing_status = 'processed' WHERE id = $1",
                webhook_id
            )
            logger.info(f"✅ Marked webhook {webhook_id} as processed")
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_webhook_data(data: Dict[str, Any]):
    """Process webhook data and track conversations"""
    try:
        if data.get("object") != "whatsapp_business_account":
            return
        
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    await process_message_webhook(change.get("value", {}))
                elif change.get("field") == "messages.status":
                    await process_status_webhook(change.get("value", {}))
                elif change.get("field") == "conversations":
                    await process_conversation_webhook(change.get("value", {}))
    
    except Exception as e:
        logger.error(f"Error processing webhook data: {e}")

async def process_message_webhook(value: Dict[str, Any]):
    """Process incoming message webhook"""
    try:
        # Extract message data
        messages = value.get("messages", [])
        contacts = value.get("contacts", [])
        
        for message in messages:
            wa_id = message.get("from")
            message_id = message.get("id")
            timestamp = message.get("timestamp")
            
            # Find contact info
            contact_info = next((c for c in contacts if c.get("wa_id") == wa_id), {})
            user_name = contact_info.get("profile", {}).get("name", "Unknown")
            
            logger.info(f"📨 Received message from {wa_id} ({user_name}): {message_id}")
            
            # Create user-initiated conversation window (24 hours from now)
            try:
                async with db.pool.acquire() as conn:
                    # Deactivate existing conversations for this user
                    await conn.execute(
                        "UPDATE whatsapp_conversations SET is_active = false WHERE wa_id = $1",
                        wa_id
                    )
                    
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
                logger.error(f"Database error creating conversation: {db_error}")
            
    except Exception as e:
        logger.error(f"Error processing message webhook: {e}")

async def process_status_webhook(value: Dict[str, Any]):
    """Process message status webhook"""
    try:
        statuses = value.get("statuses", [])
        
        for status in statuses:
            message_id = status.get("id")
            recipient_id = status.get("recipient_id")
            status_type = status.get("status")
            conversation = status.get("conversation", {})
            
            logger.info(f"📊 Message status: {message_id} -> {status_type} for {recipient_id}")
            
            # Track conversation if present
            if conversation:
                conversation_id = conversation.get("id")
                origin_type = conversation.get("origin", {}).get("type")
                expiration_timestamp = conversation.get("expiration_timestamp")
                
                if conversation_id and origin_type and expiration_timestamp:
                    # Convert timestamp to datetime
                    expires_at = datetime.fromtimestamp(
                        int(expiration_timestamp), 
                        tz=timezone.utc
                    )
                    
                    # Record conversation directly
                    try:
                        async with db.pool.acquire() as conn:
                            # Deactivate existing conversations for this user
                            await conn.execute(
                                "UPDATE whatsapp_conversations SET is_active = false WHERE wa_id = $1",
                                recipient_id
                            )
                            
                            # Insert new conversation
                            await conn.execute(
                                """INSERT INTO whatsapp_conversations 
                                   (wa_id, conversation_id, origin_type, initiated_at, expires_at)
                                   VALUES ($1, $2, $3, NOW(), $4)""",
                                recipient_id, conversation_id, origin_type, expires_at
                            )
                            
                            logger.info(f"💬 Recorded conversation: {conversation_id} for {recipient_id} until {expires_at}")
                    except Exception as e:
                        logger.error(f"Error recording conversation: {e}")
    
    except Exception as e:
        logger.error(f"Error processing status webhook: {e}")

async def process_conversation_webhook(value: Dict[str, Any]):
    """Process conversation webhook"""
    try:
        conversations = value.get("conversations", [])
        
        for conversation in conversations:
            conversation_id = conversation.get("id")
            origin_type = conversation.get("origin", {}).get("type")
            expiration_timestamp = conversation.get("expiration_timestamp")
            
            logger.info(f"💬 Conversation webhook: {conversation_id} - {origin_type}")
            
            # This webhook provides conversation updates
            # We can use this to track conversation state changes
    
    except Exception as e:
        logger.error(f"Error processing conversation webhook: {e}")

# Utility functions for conversation management
async def get_conversation_status(wa_id: str) -> Dict[str, Any]:
    """Get current conversation status for a user"""
    try:
        async with db.pool.acquire() as conn:
            # Check if user has active conversation
            conversation = await conn.fetchrow(
                "SELECT * FROM get_active_conversation($1)", wa_id
            )
            
            # Check if can send free message
            can_send_free = await conn.fetchval(
                "SELECT can_send_free_message($1)", wa_id
            )
            
            return {
                "wa_id": wa_id,
                "has_active_conversation": conversation is not None,
                "can_send_free_message": can_send_free or False,
                "conversation": dict(conversation) if conversation else None
            }
    
    except Exception as e:
        logger.error(f"Error getting conversation status: {e}")
        return {
            "wa_id": wa_id,
            "has_active_conversation": False,
            "can_send_free_message": False,
            "conversation": None
        }

@router.get("/conversation-status/{wa_id}")
async def get_conversation_status_endpoint(wa_id: str):
    """Get conversation status for a WhatsApp ID"""
    status = await get_conversation_status(wa_id)
    return status

