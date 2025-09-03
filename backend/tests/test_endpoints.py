import asyncio
import httpx
import json
from datetime import datetime

# API Base URL
API_BASE = "http://localhost:8000"

async def test_endpoints():
    """Comprehensive test of all API endpoints"""
    async with httpx.AsyncClient() as client:
        print("🚀 Starting comprehensive API testing...\n")
        
        # Test 1: Root endpoint
        print("1. Testing root endpoint...")
        try:
            response = await client.get(f"{API_BASE}/")
            print(f"✅ Root: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Root failed: {e}")
        
        # Test 2: API docs
        print("\n2. Testing API documentation...")
        try:
            response = await client.get(f"{API_BASE}/docs")
            print(f"✅ Docs: {response.status_code} - Documentation available")
        except Exception as e:
            print(f"❌ Docs failed: {e}")
            
        # Test 3: Health endpoint (from additional_backend_endpoints)
        print("\n3. Testing health endpoint...")
        try:
            response = await client.get(f"{API_BASE}/health")
            print(f"✅ Health: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Health failed: {e}")
            
        # Test 4: Coach registration
        print("\n4. Testing coach registration...")
        registration_data = {
            "barcode": "test-barcode-123",
            "name": "Test Coach",
            "email": "test@coach.com",
            "whatsapp_token": "test-token",
            "timezone": "EST"
        }
        try:
            response = await client.post(f"{API_BASE}/register", json=registration_data)
            result = response.json()
            print(f"✅ Registration: {response.status_code} - {result}")
            
            # Store coach_id for further tests
            if result.get('coach_id'):
                coach_id = result['coach_id']
                print(f"   Coach ID: {coach_id}")
        except Exception as e:
            print(f"❌ Registration failed: {e}")
            return
            
        # Test 5: Get clients for coach
        print("\n5. Testing get clients...")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/clients")
            clients = response.json()
            print(f"✅ Get clients: {response.status_code} - Found {len(clients)} clients")
        except Exception as e:
            print(f"❌ Get clients failed: {e}")
            
        # Test 6: Add a client
        print("\n6. Testing add client...")
        client_data = {
            "name": "John Doe",
            "phone_number": "+1234567890",
            "country": "US",
            "timezone": "EST",
            "categories": ["Health", "Finance"]
        }
        try:
            response = await client.post(f"{API_BASE}/coaches/{coach_id}/clients", json=client_data)
            print(f"✅ Add client: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Add client failed: {e}")
            
        # Test 7: Get clients again (should show the new client)
        print("\n7. Testing get clients after adding...")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/clients")
            clients = response.json()
            print(f"✅ Get clients updated: {response.status_code} - Found {len(clients)} clients")
            if clients:
                client_id = clients[0]['id']
                print(f"   First client ID: {client_id}")
        except Exception as e:
            print(f"❌ Get clients failed: {e}")
            
        # Test 8: Categories endpoint
        print("\n8. Testing get categories...")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/categories")
            categories = response.json()
            print(f"✅ Get categories: {response.status_code} - Found {len(categories)} categories")
        except Exception as e:
            print(f"❌ Get categories failed: {e}")
            
        # Test 9: Message templates
        print("\n9. Testing message templates...")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/templates?type=celebration")
            templates = response.json()
            print(f"✅ Get templates: {response.status_code} - Found {len(templates)} templates")
        except Exception as e:
            print(f"❌ Get templates failed: {e}")
            
        # Test 10: Send message
        print("\n10. Testing send message...")
        message_data = {
            "client_ids": [client_id] if 'client_id' in locals() else [],
            "message_type": "celebration",
            "content": "🎉 Great job today!",
            "schedule_type": "now"
        }
        try:
            response = await client.post(f"{API_BASE}/messages/send", json=message_data)
            print(f"✅ Send message: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Send message failed: {e}")
            
        # Test 11: WhatsApp webhook (simulate)
        print("\n11. Testing WhatsApp webhook...")
        webhook_data = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "test-id",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "from": "+1234567890",
                                        "text": {"body": "Hello coach!"},
                                        "timestamp": str(int(datetime.now().timestamp())),
                                        "type": "text"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        try:
            response = await client.post(f"{API_BASE}/webhook/whatsapp", json=webhook_data)
            print(f"✅ WhatsApp webhook: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ WhatsApp webhook failed: {e}")
            
        # Test 12: Stats endpoint
        print("\n12. Testing stats endpoint...")
        try:
            response = await client.get(f"{API_BASE}/stats")
            print(f"✅ Stats: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Stats failed: {e}")
            
        # Test 13: Coach profile
        print("\n13. Testing get coach profile...")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}")
            print(f"✅ Coach profile: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Coach profile failed: {e}")
            
        print("\n🎉 API testing completed!")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
