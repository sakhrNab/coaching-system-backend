import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

async def test_all_endpoints():
    """Test all available endpoints comprehensively"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🚀 Comprehensive Backend Testing\n")
        
        # Step 1: Basic connectivity
        print("1. BASIC CONNECTIVITY")
        try:
            response = await client.get(f"{API_BASE}/")
            print(f"✅ Root endpoint: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Root failed: {e}")
            return
        
        try:
            response = await client.get(f"{API_BASE}/docs")
            print(f"✅ API Docs: {response.status_code}")
        except Exception as e:
            print(f"❌ Docs failed: {e}")
        
        # Step 2: Health check
        print("\n2. HEALTH CHECK")
        try:
            response = await client.get(f"{API_BASE}/health")
            print(f"✅ Health: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Health failed: {e}")
        
        # Step 3: Create test coach
        print("\n3. COACH REGISTRATION")
        coach_data = {
            "barcode": "comprehensive-test-123",
            "name": "Comprehensive Test Coach",
            "email": "comprehensive@test.com",
            "whatsapp_token": "test-token-comp",
            "timezone": "EST"
        }
        
        try:
            response = await client.post(f"{API_BASE}/register", json=coach_data)
            result = response.json()
            print(f"✅ Coach registration: {response.status_code} - Status: {result.get('status')}")
            coach_id = result.get('coach_id')
        except Exception as e:
            print(f"❌ Coach registration failed: {e}")
            return
        
        # Step 4: Categories
        print(f"\n4. CATEGORIES (Coach ID: {coach_id})")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/categories")
            categories = response.json()
            print(f"✅ Get categories: {response.status_code} - Found {len(categories)} categories")
            # Show first few categories
            for i, cat in enumerate(categories[:3]):
                print(f"   - {cat['name']} (Predefined: {cat['is_predefined']})")
        except Exception as e:
            print(f"❌ Categories failed: {e}")
        
        # Step 5: Clients CRUD
        print(f"\n5. CLIENT MANAGEMENT")
        
        # 5a. Get existing clients
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/clients")
            existing_clients = response.json()
            print(f"✅ Get existing clients: {response.status_code} - Found {len(existing_clients)} clients")
        except Exception as e:
            print(f"❌ Get clients failed: {e}")
            existing_clients = []
        
        # 5b. Add new client  
        new_client = {
            "name": "Comprehensive Test Client",
            "phone_number": "+1555000COMP",
            "country": "US",
            "timezone": "EST",
            "categories": ["Health", "Business"]
        }
        
        try:
            response = await client.post(f"{API_BASE}/coaches/{coach_id}/clients", json=new_client)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Add client: {response.status_code} - Client ID: {result.get('client_id')}")
                new_client_id = result.get('client_id')
            else:
                print(f"⚠️ Add client: {response.status_code} - {response.text}")
                new_client_id = None
        except Exception as e:
            print(f"❌ Add client failed: {e}")
            new_client_id = None
        
        # 5c. Get clients again
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/clients")
            updated_clients = response.json()
            print(f"✅ Get updated clients: {response.status_code} - Found {len(updated_clients)} clients")
            if len(updated_clients) > len(existing_clients):
                print(f"   📈 Successfully added {len(updated_clients) - len(existing_clients)} new client(s)")
        except Exception as e:
            print(f"❌ Get updated clients failed: {e}")
        
        # Step 6: Templates
        print(f"\n6. MESSAGE TEMPLATES")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/templates?type=celebration")
            templates = response.json()
            print(f"✅ Get templates: {response.status_code} - Found {len(templates)} templates")
        except Exception as e:
            print(f"❌ Templates failed: {e}")
            
        # Step 7: Message sending
        print(f"\n7. MESSAGE OPERATIONS")
        if new_client_id:
            message_request = {
                "client_ids": [new_client_id],
                "message_type": "celebration",
                "content": "🎉 Comprehensive test message!",
                "schedule_type": "now"
            }
            
            try:
                response = await client.post(f"{API_BASE}/messages/send", json=message_request)
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Send message: {response.status_code} - {result}")
                else:
                    print(f"⚠️ Send message: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Send message failed: {e}")
        else:
            print("⏭️ Skipping message test (no client ID)")
        
        # Step 8: WhatsApp webhook simulation
        print(f"\n8. WEBHOOK TESTING")
        webhook_data = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test-entry",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": "+1555000COMP",
                            "text": {"body": "Test webhook message"},
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
        
        try:
            response = await client.post(f"{API_BASE}/webhook/whatsapp", json=webhook_data)
            result = response.json()
            print(f"✅ WhatsApp webhook: {response.status_code} - Status: {result.get('status')}")
        except Exception as e:
            print(f"❌ WhatsApp webhook failed: {e}")
        
        # Step 9: Additional endpoints
        print(f"\n9. ADDITIONAL ENDPOINTS")
        
        # 9a. Coach stats
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/stats")
            print(f"✅ Coach stats: {response.status_code}")
        except Exception as e:
            print(f"❌ Coach stats: {e}")
        
        # 9b. Export endpoint
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/export")
            print(f"✅ Export: {response.status_code}")
        except Exception as e:
            print(f"❌ Export: {e}")
        
        # 9c. Analytics
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/analytics")
            print(f"✅ Analytics: {response.status_code}")
        except Exception as e:
            print(f"❌ Analytics: {e}")
        
        print("\n🎉 Comprehensive testing completed!")
        print(f"📊 Coach ID for further testing: {coach_id}")

if __name__ == "__main__":
    asyncio.run(test_all_endpoints())
