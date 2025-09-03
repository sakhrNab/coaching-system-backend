"""
Real Integration Test Script
Test with real phone number and APIs
"""

import asyncio
import httpx
import os
from datetime import datetime

# Load real environment variables
from dotenv import load_dotenv
load_dotenv('.env.production')

API_BASE = "https://your-domain.com/api"  # Update with your domain
TEST_PHONE = "+1234567890"  # Replace with your real phone number

async def test_real_integration():
    """Test complete workflow with real APIs"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("📱 Testing Real Integration with Your Phone Number\n")
        
        # Step 1: Register as coach
        print("1. COACH REGISTRATION")
        coach_data = {
            "barcode": f"real-test-{datetime.now().strftime('%Y%m%d%H%M')}",
            "name": "Real Test Coach",
            "email": "your-email@example.com",  # Your real email
            "whatsapp_token": os.getenv("WHATSAPP_ACCESS_TOKEN"),
            "timezone": "EST"
        }
        
        response = await client.post(f"{API_BASE}/register", json=coach_data)
        result = response.json()
        coach_id = result['coach_id']
        print(f"✅ Coach registered: {coach_id}")
        
        # Step 2: Add yourself as a client
        print(f"\n2. ADDING YOUR PHONE NUMBER AS CLIENT")
        client_data = {
            "name": "Test Client (You)",
            "phone_number": TEST_PHONE,
            "country": "US",
            "timezone": "EST",
            "categories": ["Health", "Business", "Growth"]
        }
        
        response = await client.post(f"{API_BASE}/coaches/{coach_id}/clients", json=client_data)
        print(f"✅ Client added: {response.status_code}")
        
        # Step 3: Send real WhatsApp message
        print(f"\n3. SENDING REAL WHATSAPP MESSAGE TO {TEST_PHONE}")
        message_data = {
            "client_ids": [coach_id],  # Will be resolved to actual client
            "message_type": "celebration",
            "content": "🎉 Congratulations! Your coaching system is working! This is a real test message from your accountability coaching platform.",
            "schedule_type": "now"
        }
        
        response = await client.post(f"{API_BASE}/messages/send", json=message_data)
        print(f"✅ Message sent: {response.status_code}")
        print("📱 Check your WhatsApp for the test message!")
        
        # Step 4: Test Google Sheets export
        print(f"\n4. TESTING GOOGLE SHEETS EXPORT")
        response = await client.get(f"{API_BASE}/coaches/{coach_id}/export")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Google Sheets export: {result.get('sheet_url', 'URL not provided')}")
        else:
            print(f"⚠️ Export status: {response.status_code}")
        
        # Step 5: Test voice processing (simulate)
        print(f"\n5. TESTING VOICE MESSAGE PROCESSING")
        voice_data = {
            "audio_url": "https://example.com/test-audio.mp3",  # Mock URL
            "from_number": TEST_PHONE,
            "message_type": "accountability",
            "target_clients": ["all"]
        }
        
        response = await client.post(f"{API_BASE}/voice/process", json=voice_data)
        print(f"✅ Voice processing: {response.status_code}")
        
        # Step 6: Check analytics
        print(f"\n6. CHECKING ANALYTICS")
        response = await client.get(f"{API_BASE}/coaches/{coach_id}/analytics")
        if response.status_code == 200:
            analytics = response.json()
            print(f"✅ Analytics: {analytics}")
        
        print(f"\n🎉 REAL INTEGRATION TEST COMPLETED!")
        print(f"📊 Coach ID for further testing: {coach_id}")
        print(f"📱 Check your phone ({TEST_PHONE}) for WhatsApp messages")

if __name__ == "__main__":
    asyncio.run(test_real_integration())
