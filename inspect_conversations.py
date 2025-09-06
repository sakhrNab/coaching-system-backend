#!/usr/bin/env python3
"""
Inspect database conversations to see 24-hour window tracking
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def inspect_database():
    """Inspect the database for conversation tracking"""
    
    # Database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/coaching_system")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to database")
        
        # Check if conversations table exists
        print("\n📋 CHECKING DATABASE TABLES")
        print("="*50)
        
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%conversation%'
        """)
        
        print("📊 Conversation-related tables:")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Check whatsapp_conversations table
        print("\n📋 WHATSAPP_CONVERSATIONS TABLE")
        print("="*50)
        
        try:
            conversations = await conn.fetch("""
                SELECT 
                    wa_id,
                    conversation_id,
                    origin_type,
                    initiated_at,
                    expires_at,
                    is_active,
                    created_at
                FROM whatsapp_conversations 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            
            if conversations:
                print(f"📊 Found {len(conversations)} conversations:")
                for conv in conversations:
                    print(f"\n   📱 WA ID: {conv['wa_id']}")
                    print(f"   🆔 Conversation ID: {conv['conversation_id']}")
                    print(f"   🎯 Origin Type: {conv['origin_type']}")
                    print(f"   ⏰ Initiated At: {conv['initiated_at']}")
                    print(f"   ⏳ Expires At: {conv['expires_at']}")
                    print(f"   ✅ Active: {conv['is_active']}")
                    print(f"   📅 Created: {conv['created_at']}")
                    
                    # Check if expired
                    now = datetime.now(conv['expires_at'].tzinfo)
                    if conv['expires_at'] < now:
                        print(f"   ⚠️  EXPIRED: {now - conv['expires_at']} ago")
                    else:
                        print(f"   ✅ ACTIVE: {conv['expires_at'] - now} remaining")
            else:
                print("📊 No conversations found")
                
        except Exception as e:
            print(f"❌ Error reading conversations: {e}")
        
        # Check can_send_free_message function
        print("\n📋 TESTING can_send_free_message FUNCTION")
        print("="*50)
        
        test_phone = "1234567890"
        
        try:
            result = await conn.fetchval("SELECT can_send_free_message($1)", test_phone)
            print(f"📱 Phone: {test_phone}")
            print(f"✅ Can send free message: {result}")
            
            if result:
                print("💡 This phone number has an active 24h window")
            else:
                print("💡 This phone number does not have an active 24h window")
                
        except Exception as e:
            print(f"❌ Error testing function: {e}")
        
        # Check message templates
        print("\n📋 MESSAGE TEMPLATES")
        print("="*50)
        
        try:
            templates = await conn.fetch("""
                SELECT 
                    content,
                    message_type,
                    language_code,
                    whatsapp_template_name,
                    is_default
                FROM message_templates 
                WHERE is_default = true
                ORDER BY message_type, content
            """)
            
            if templates:
                print(f"📊 Found {len(templates)} default templates:")
                for template in templates:
                    print(f"\n   📝 Content: {template['content']}")
                    print(f"   🏷️  Type: {template['message_type']}")
                    print(f"   🌐 Language: {template['language_code']}")
                    print(f"   📱 Template Name: {template['whatsapp_template_name']}")
            else:
                print("📊 No templates found")
                
        except Exception as e:
            print(f"❌ Error reading templates: {e}")
        
        # Check recent messages
        print("\n📋 RECENT MESSAGES")
        print("="*50)
        
        try:
            messages = await conn.fetch("""
                SELECT 
                    client_id,
                    message_type,
                    content,
                    delivery_status,
                    sent_at,
                    created_at
                FROM scheduled_messages 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            if messages:
                print(f"📊 Found {len(messages)} recent messages:")
                for msg in messages:
                    print(f"\n   👤 Client ID: {msg['client_id']}")
                    print(f"   📝 Type: {msg['message_type']}")
                    print(f"   💬 Content: {msg['content'][:50]}...")
                    print(f"   📊 Status: {msg['delivery_status']}")
                    print(f"   ⏰ Sent: {msg['sent_at']}")
                    print(f"   📅 Created: {msg['created_at']}")
            else:
                print("📊 No messages found")
                
        except Exception as e:
            print(f"❌ Error reading messages: {e}")
        
        await conn.close()
        print("\n✅ Database inspection completed")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Make sure your database is running and accessible")

if __name__ == "__main__":
    print("🔍 DATABASE CONVERSATION INSPECTOR")
    print("="*50)
    print("This script inspects the database to show 24-hour window tracking")
    print("="*50)
    
    asyncio.run(inspect_database())
