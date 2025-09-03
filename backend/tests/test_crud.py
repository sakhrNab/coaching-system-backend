import asyncio
import httpx
import json
import random

API_BASE = "http://localhost:8000"

async def test_crud_operations():
    """Test Create, Read, Update, Delete operations"""
    async with httpx.AsyncClient() as client:
        print("🧪 Testing CRUD Operations\n")
        
        # Step 1: Create a new coach
        print("1. CREATE - Register new coach")
        random_id = random.randint(1000, 9999)
        registration_data = {
            "barcode": f"test-barcode-{random_id}",
            "name": f"Test Coach {random_id}",
            "email": f"coach{random_id}@test.com",
            "whatsapp_token": f"token-{random_id}",
            "timezone": "EST"
        }
        
        response = await client.post(f"{API_BASE}/register", json=registration_data)
        result = response.json()
        print(f"✅ Coach registered: {result}")
        coach_id = result['coach_id']
        
        # Step 2: Create clients 
        print(f"\n2. CREATE - Add clients to coach {coach_id}")
        clients_to_create = [
            {
                "name": f"Client A-{random_id}",
                "phone_number": f"+1555000{random_id:04d}",
                "country": "US",
                "timezone": "EST",
                "categories": ["Health", "Finance"]
            },
            {
                "name": f"Client B-{random_id}",
                "phone_number": f"+1555001{random_id:04d}",
                "country": "CA", 
                "timezone": "PST",
                "categories": ["Business", "Growth"]
            }
        ]
        
        client_ids = []
        for client_data in clients_to_create:
            try:
                response = await client.post(f"{API_BASE}/coaches/{coach_id}/clients", json=client_data)
                if response.status_code == 200:
                    result = response.json()
                    client_ids.append(result['client_id'])
                    print(f"✅ Client created: {client_data['name']} - ID: {result['client_id']}")
                else:
                    print(f"❌ Failed to create client {client_data['name']}: {response.text}")
            except Exception as e:
                print(f"❌ Error creating client {client_data['name']}: {e}")
        
        # Step 3: Read - Get all clients
        print(f"\n3. READ - Get all clients for coach {coach_id}")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/clients")
            clients = response.json()
            print(f"✅ Retrieved {len(clients)} clients:")
            for client in clients:
                print(f"   - {client['name']} ({client['phone_number']})")
        except Exception as e:
            print(f"❌ Error getting clients: {e}")
            
        # Step 4: Read - Get categories
        print(f"\n4. READ - Get categories for coach {coach_id}")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/categories")
            categories = response.json()
            print(f"✅ Retrieved {len(categories)} categories:")
            for cat in categories[:5]:  # Show first 5
                print(f"   - {cat['name']} (Predefined: {cat['is_predefined']})")
        except Exception as e:
            print(f"❌ Error getting categories: {e}")
            
        # Step 5: Update - Test updating a client (if endpoint exists)
        if client_ids:
            print(f"\n5. UPDATE - Test client update for {client_ids[0]}")
            try:
                update_data = {
                    "name": f"Updated Client {random_id}",
                    "country": "UK",
                    "timezone": "GMT"
                }
                response = await client.put(f"{API_BASE}/coaches/{coach_id}/clients/{client_ids[0]}", json=update_data)
                if response.status_code == 200:
                    print(f"✅ Client updated successfully")
                else:
                    print(f"ℹ️ Update endpoint returned: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"ℹ️ Update test: {e}")
        
        # Step 6: Test message operations
        print(f"\n6. CREATE - Test message operations")
        if client_ids:
            message_data = {
                "client_ids": [client_ids[0]],
                "message_type": "celebration",
                "content": f"🎉 Test celebration message {random_id}!",
                "schedule_type": "now"
            }
            try:
                response = await client.post(f"{API_BASE}/messages/send", json=message_data)
                print(f"✅ Message scheduled: {response.status_code} - {response.json()}")
            except Exception as e:
                print(f"ℹ️ Message test: {e}")
        
        # Step 7: Delete - Test deleting a client (if endpoint exists)
        if client_ids:
            print(f"\n7. DELETE - Test client deletion for {client_ids[-1]}")
            try:
                response = await client.delete(f"{API_BASE}/coaches/{coach_id}/clients/{client_ids[-1]}")
                if response.status_code == 200:
                    print(f"✅ Client deleted successfully")
                else:
                    print(f"ℹ️ Delete endpoint returned: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"ℹ️ Delete test: {e}")
        
        # Step 8: Read again to verify changes
        print(f"\n8. READ - Verify final state")
        try:
            response = await client.get(f"{API_BASE}/coaches/{coach_id}/clients")
            clients = response.json()
            print(f"✅ Final count: {len(clients)} clients")
            for client in clients:
                print(f"   - {client['name']} ({client['phone_number']})")
        except Exception as e:
            print(f"❌ Error in final verification: {e}")
        
        print("\n🎉 CRUD testing completed!")

if __name__ == "__main__":
    asyncio.run(test_crud_operations())
