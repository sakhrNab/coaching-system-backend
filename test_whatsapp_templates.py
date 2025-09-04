"""
Test script for WhatsApp template messaging and conversation tracking
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
API_BASE = "http://localhost:8001"
TEST_COACH_ID = "f1af824a-1697-445d-84e6-11d8e79ece57"
TEST_CLIENT_PHONE = "201280682640"

async def test_template_mapping():
    """Test template mapping functionality"""
    print("🧪 Testing Template Mapping")
    print("=" * 50)
    
    # Test celebration messages
    celebration_messages = [
        "🎉 What are we celebrating today?",
        "✨ What are you grateful for?",
        "🌟 What victory are you proud of today?",
        "🎊 What positive moment made your day?",
        "💫 What breakthrough did you experience?"
    ]
    
    # Test accountability messages
    accountability_messages = [
        "📝 How did you progress on your goals today?",
        "🎯 What action did you take towards your target?",
        "💪 What challenge did you overcome today?",
        "📈 How are you measuring your progress?",
        "🔥 What will you commit to tomorrow?"
    ]
    
    from backend.whatsapp_templates import template_manager
    
    print("📋 Celebration Messages:")
    for msg in celebration_messages:
        template_name = template_manager.get_template_name(msg)
        print(f"  {msg} -> {template_name}")
    
    print("\n📋 Accountability Messages:")
    for msg in accountability_messages:
        template_name = template_manager.get_template_name(msg)
        print(f"  {msg} -> {template_name}")
    
    print("\n✅ Template mapping test completed")

async def test_conversation_tracking():
    """Test conversation tracking functionality"""
    print("\n🧪 Testing Conversation Tracking")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test conversation status endpoint
        try:
            response = await client.get(f"{API_BASE}/webhook/conversation-status/{TEST_CLIENT_PHONE}")
            if response.status_code == 200:
                status = response.json()
                print(f"📊 Conversation Status for {TEST_CLIENT_PHONE}:")
                print(f"  Has Active Conversation: {status.get('has_active_conversation')}")
                print(f"  Can Send Free Message: {status.get('can_send_free_message')}")
                print(f"  Conversation Details: {status.get('conversation')}")
            else:
                print(f"❌ Failed to get conversation status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing conversation status: {e}")

async def test_template_message_sending():
    """Test sending template messages"""
    print("\n🧪 Testing Template Message Sending")
    print("=" * 50)
    
    # Test data
    test_messages = [
        {
            "client_ids": ["35c0503e-60c6-4ee0-917a-4cde128e99fa"],
            "message_type": "celebration",
            "content": "🎉 What are we celebrating today?",
            "schedule_type": "now"
        },
        {
            "client_ids": ["35c0503e-60c6-4ee0-917a-4cde128e99fa"],
            "message_type": "accountability", 
            "content": "🔥 What will you commit to tomorrow?",
            "schedule_type": "now"
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for i, message_data in enumerate(test_messages, 1):
            print(f"\n📤 Test {i}: Sending {message_data['message_type']} message")
            print(f"   Content: {message_data['content']}")
            
            try:
                response = await client.post(
                    f"{API_BASE}/messages/send",
                    json=message_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Success: {result}")
                else:
                    print(f"   ❌ Failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Wait between tests
            await asyncio.sleep(2)

async def test_webhook_verification():
    """Test webhook verification"""
    print("\n🧪 Testing Webhook Verification")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test webhook verification
        try:
            response = await client.get(
                f"{API_BASE}/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "test-verify-token",
                    "hub.challenge": "test-challenge-123"
                }
            )
            
            if response.status_code == 200:
                challenge = response.text
                print(f"✅ Webhook verification successful: {challenge}")
            else:
                print(f"❌ Webhook verification failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing webhook verification: {e}")

async def test_database_functions():
    """Test database conversation functions"""
    print("\n🧪 Testing Database Functions")
    print("=" * 50)
    
    from backend.database import db
    
    try:
        await db.connect()
        
        # Test can_send_free_message function
        can_send = await db.fetchval("SELECT can_send_free_message($1)", TEST_CLIENT_PHONE)
        print(f"📊 Can send free message to {TEST_CLIENT_PHONE}: {can_send}")
        
        # Test get_active_conversation function
        conversation = await db.fetchrow("SELECT * FROM get_active_conversation($1)", TEST_CLIENT_PHONE)
        if conversation:
            print(f"💬 Active conversation: {dict(conversation)}")
        else:
            print("💬 No active conversation found")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ Error testing database functions: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting WhatsApp Template and Conversation Tracking Tests")
    print("=" * 70)
    
    # Run tests
    await test_template_mapping()
    await test_database_functions()
    await test_conversation_tracking()
    await test_webhook_verification()
    await test_template_message_sending()
    
    print("\n🎉 All tests completed!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

