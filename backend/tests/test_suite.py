"""
test_suite.py - Comprehensive Testing Framework
Complete test suite for the entire coaching system
"""

import pytest
import asyncio
import asyncpg
import httpx
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import tempfile
import pandas as pd

# Test configuration
TEST_CONFIG = {
    "API_BASE": "http://localhost:8000",
    "DB_CONFIG": {
        "host": os.getenv("TEST_DB_HOST", "localhost"),
        "port": int(os.getenv("TEST_DB_PORT", 5433)),
        "user": os.getenv("TEST_DB_USER", "postgres"),
        "password": os.getenv("TEST_DB_PASSWORD", "testpass"),
        "database": os.getenv("TEST_DB_NAME", "coaching_test")
    }
}

# Test fixtures
@pytest.fixture
async def db_conn():
    """Create test database connection"""
    conn = await asyncpg.connect(**TEST_CONFIG["DB_CONFIG"])
    yield conn
    await conn.close()

@pytest.fixture
async def api_client():
    """Create test API client"""
    async with httpx.AsyncClient(base_url=TEST_CONFIG["API_BASE"]) as client:
        yield client

@pytest.fixture
async def test_coach(db_conn):
    """Create test coach"""
    coach_id = await db_conn.fetchval(
        """INSERT INTO coaches (name, email, whatsapp_token, whatsapp_phone_number, timezone, registration_barcode)
           VALUES ('Test Coach', 'test@example.com', 'test_token_123', '+1234567890', 'EST', 'test_barcode_123')
           RETURNING id"""
    )
    yield str(coach_id)
    
    # Cleanup
    await db_conn.execute("DELETE FROM coaches WHERE id = $1", coach_id)

@pytest.fixture
async def test_client(db_conn, test_coach):
    """Create test client"""
    client_id = await db_conn.fetchval(
        """INSERT INTO clients (coach_id, name, phone_number, country, timezone)
           VALUES ($1, 'Test Client', '+1987654321', 'USA', 'EST')
           RETURNING id""",
        test_coach
    )
    yield str(client_id)

class TestCoachRegistration:
    """Test coach registration and authentication"""
    
    @pytest.mark.asyncio
    async def test_coach_registration_new(self, api_client):
        """Test new coach registration"""
        registration_data = {
            "barcode": f"test_barcode_{datetime.now().timestamp()}",
            "whatsapp_token": "new_test_token",
            "name": "New Test Coach",
            "email": "newtest@example.com",
            "timezone": "PST"
        }
        
        response = await api_client.post("/register", json=registration_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "registered"
        assert "coach_id" in data
    
    @pytest.mark.asyncio
    async def test_coach_registration_existing(self, api_client, test_coach):
        """Test existing coach registration"""
        registration_data = {
            "barcode": "test_barcode_123",
            "whatsapp_token": "test_token_123",
            "name": "Test Coach",
            "timezone": "EST"
        }
        
        response = await api_client.post("/register", json=registration_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "existing"
        assert data["coach_id"] == test_coach
    
    @pytest.mark.asyncio
    async def test_authentication_with_barcode(self, api_client, test_coach):
        """Test JWT authentication with barcode"""
        auth_data = {"barcode": "test_barcode_123"}
        
        response = await api_client.post("/auth/token", json=auth_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "coach_data" in data

class TestClientManagement:
    """Test client management operations"""
    
    @pytest.mark.asyncio
    async def test_add_client(self, api_client, test_coach):
        """Test adding new client"""
        client_data = {
            "name": "New Test Client",
            "phone_number": "+1555666777",
            "country": "Canada",
            "timezone": "PST",
            "categories": ["Health", "Finance"]
        }
        
        response = await api_client.post(f"/coaches/{test_coach}/clients", json=client_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "created"
        assert "client_id" in data
    
    @pytest.mark.asyncio
    async def test_get_clients(self, api_client, test_coach, test_client):
        """Test retrieving clients"""
        response = await api_client.get(f"/coaches/{test_coach}/clients")
        assert response.status_code == 200
        
        clients = response.json()
        assert isinstance(clients, list)
        assert len(clients) >= 1
        
        # Find our test client
        test_client_data = next((c for c in clients if c["id"] == test_client), None)
        assert test_client_data is not None
        assert test_client_data["name"] == "Test Client"
    
    @pytest.mark.asyncio
    async def test_update_client(self, api_client, test_coach, test_client):
        """Test updating client information"""
        update_data = {
            "name": "Updated Test Client",
            "phone_number": "+1987654321",
            "country": "USA",
            "timezone": "CST",
            "categories": ["Business", "Growth"]
        }
        
        response = await api_client.put(f"/coaches/{test_coach}/clients/{test_client}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "updated"
    
    @pytest.mark.asyncio
    async def test_delete_client(self, api_client, test_coach, test_client):
        """Test deleting (deactivating) client"""
        response = await api_client.delete(f"/coaches/{test_coach}/clients/{test_client}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "deleted"

class TestMessageOperations:
    """Test message sending and processing"""
    
    @pytest.mark.asyncio
    async def test_send_immediate_message(self, api_client, test_coach, test_client):
        """Test sending immediate message"""
        message_data = {
            "client_ids": [test_client],
            "message_type": "celebration",
            "content": "Test celebration message! 🎉",
            "schedule_type": "now"
        }
        
        with patch('backend_api.WhatsAppClient.send_message') as mock_send:
            mock_send.return_value = {"messages": [{"id": "test_msg_id_123"}]}
            
            response = await api_client.post("/messages/send", json=message_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "scheduled"
            assert len(data["message_ids"]) == 1
    
    @pytest.mark.asyncio
    async def test_send_scheduled_message(self, api_client, test_coach, test_client):
        """Test sending scheduled message"""
        future_time = (datetime.now() + timedelta(hours=2)).isoformat()
        
        message_data = {
            "client_ids": [test_client],
            "message_type": "accountability",
            "content": "How are your goals going?",
            "schedule_type": "specific",
            "scheduled_time": future_time
        }
        
        response = await api_client.post("/messages/send", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "scheduled"
    
    @pytest.mark.asyncio
    async def test_bulk_message_sending(self, api_client, test_coach):
        """Test bulk message operations"""
        # Create multiple test clients
        client_ids = []
        for i in range(3):
            client_data = {
                "name": f"Bulk Test Client {i}",
                "phone_number": f"+155566677{i}",
                "country": "USA",
                "timezone": "EST",
                "categories": ["Health"]
            }
            
            response = await api_client.post(f"/coaches/{test_coach}/clients", json=client_data)
            client_id = response.json()["client_id"]
            client_ids.append(client_id)
        
        # Send bulk message
        bulk_data = {
            "client_ids": client_ids,
            "content": "Bulk test message for everyone!",
            "message_type": "general",
            "schedule_type": "now"
        }
        
        with patch('worker.WhatsAppClient.send_message') as mock_send:
            mock_send.return_value = {"messages": [{"id": f"bulk_msg_{i}"}]}
            
            response = await api_client.post(f"/coaches/{test_coach}/bulk-message", json=bulk_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "queued"
            assert len(data["message_ids"]) == 3

class TestVoiceProcessing:
    """Test voice message processing pipeline"""
    
    @pytest.mark.asyncio
    async def test_voice_transcription_workflow(self, api_client, test_coach):
        """Test complete voice processing workflow"""
        voice_data = {
            "coach_id": test_coach,
            "whatsapp_message_id": "voice_msg_123",
            "audio_url": "https://example.com/test_audio.ogg",
            "message_type": "celebration"
        }
        
        with patch('backend_api.VoiceTranscriptionService.transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = "This is a test transcribed message"
            
            with patch('backend_api.VoiceTranscriptionService.correct_message') as mock_correct:
                mock_correct.return_value = "This is a test corrected message."
                
                with patch('backend_api.WhatsAppClient.send_interactive_message') as mock_interactive:
                    mock_interactive.return_value = {"messages": [{"id": "interactive_msg_123"}]}
                    
                    response = await api_client.post("/voice/process", json=voice_data)
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert "processing_id" in data
                    assert data["corrected_text"] == "This is a test corrected message."
    
    @pytest.mark.asyncio
    async def test_voice_confirmation_flow(self, db_conn, test_coach):
        """Test voice message confirmation"""
        # Create voice processing record
        processing_id = await db_conn.fetchval(
            """INSERT INTO voice_message_processing 
               (coach_id, whatsapp_message_id, transcribed_text, corrected_text, processing_status)
               VALUES ($1, 'test_msg', 'original', 'corrected', 'corrected')
               RETURNING id""",
            test_coach
        )
        
        # Test confirmation
        from backend_api import handle_voice_confirmation
        await handle_voice_confirmation(str(processing_id), True)
        
        # Verify status update
        status = await db_conn.fetchval(
            "SELECT processing_status FROM voice_message_processing WHERE id = $1",
            processing_id
        )
        assert status == "confirmed"

class TestWhatsAppIntegration:
    """Test WhatsApp webhook and API integration"""
    
    @pytest.mark.asyncio
    async def test_webhook_verification(self, api_client):
        """Test WhatsApp webhook verification"""
        params = {
            "hub.mode": "subscribe",
            "hub.challenge": "test_challenge_12345",
            "hub.verify_token": "test_verify_token"
        }
        
        with patch.dict(os.environ, {"WEBHOOK_VERIFY_TOKEN": "test_verify_token"}):
            response = await api_client.get("/webhook/whatsapp", params=params)
            assert response.status_code == 200
            assert response.text == "test_challenge_12345"
    
    @pytest.mark.asyncio
    async def test_webhook_message_processing(self, api_client, test_coach):
        """Test processing incoming WhatsApp messages"""
        webhook_data = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "entry_id",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "+1234567890"},
                        "messages": [{
                            "from": "+1234567890",
                            "id": "test_msg_id",
                            "timestamp": "1234567890",
                            "text": {"body": "send celebration to Mike"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Mock webhook signature verification
        with patch('whatsapp_webhook_handler.verify_webhook_signature') as mock_verify:
            mock_verify.return_value = True
            
            with patch('whatsapp_webhook_handler.process_webhook_async.delay') as mock_process:
                response = await api_client.post("/webhook/whatsapp", json=webhook_data)
                assert response.status_code == 200
                assert response.json()["status"] == "received"
                
                # Verify background task was queued
                mock_process.assert_called_once()

class TestSchedulingSystem:
    """Test message scheduling and automation"""
    
    @pytest.mark.asyncio
    async def test_schedule_future_message(self, db_conn, test_coach, test_client):
        """Test scheduling messages for future delivery"""
        future_time = datetime.now() + timedelta(hours=2)
        
        # Create scheduled message
        scheduled_id = await db_conn.fetchval(
            """INSERT INTO scheduled_messages 
               (coach_id, client_id, message_type, content, schedule_type, scheduled_time, status)
               VALUES ($1, $2, 'accountability', 'Test scheduled message', 'specific', $3, 'scheduled')
               RETURNING id""",
            test_coach, test_client, future_time
        )
        
        assert scheduled_id is not None
        
        # Verify message is in database
        message = await db_conn.fetchrow(
            "SELECT * FROM scheduled_messages WHERE id = $1",
            scheduled_id
        )
        assert message["status"] == "scheduled"
        assert message["scheduled_time"] == future_time
    
    @pytest.mark.asyncio
    async def test_recurring_message_setup(self, db_conn, test_coach, test_client):
        """Test recurring message configuration"""
        recurring_pattern = {
            "frequency": "daily",
            "interval": 1,
            "time": "09:00"
        }
        
        scheduled_id = await db_conn.fetchval(
            """INSERT INTO scheduled_messages 
               (coach_id, client_id, message_type, content, schedule_type, recurring_pattern, status)
               VALUES ($1, $2, 'accountability', 'Daily check-in', 'recurring', $3, 'scheduled')
               RETURNING id""",
            test_coach, test_client, json.dumps(recurring_pattern)
        )
        
        assert scheduled_id is not None

class TestFileImport:
    """Test file import functionality"""
    
    @pytest.mark.asyncio
    async def test_csv_import(self, api_client, test_coach):
        """Test CSV file import"""
        # Create test CSV
        csv_data = """name,phone_number,country,timezone,categories
John Doe,+1111111111,USA,EST,"Health,Finance"
Jane Smith,+2222222222,Canada,PST,"Business,Growth"
Bob Johnson,+3333333333,USA,CST,"Health"
"""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = f.name
        
        try:
            # Upload file
            with open(temp_path, 'rb') as f:
                files = {"file": ("test_clients.csv", f, "text/csv")}
                
                response = await api_client.post(
                    f"/coaches/{test_coach}/import-clients",
                    files=files
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["count"] == 3
        
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_excel_import(self, api_client, test_coach):
        """Test Excel file import"""
        # Create test Excel file
        df = pd.DataFrame({
            'name': ['Excel Client 1', 'Excel Client 2'],
            'phone_number': ['+4444444444', '+5555555555'],
            'country': ['USA', 'UK'],
            'timezone': ['EST', 'GMT'],
            'categories': ['Health,Business', 'Finance']
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                files = {"file": ("test_clients.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                
                response = await api_client.post(
                    f"/coaches/{test_coach}/import-clients",
                    files=files
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["count"] == 2
        
        finally:
            os.unlink(temp_path)

class TestGoogleSheetsIntegration:
    """Test Google Sheets integration"""
    
    @pytest.mark.asyncio
    async def test_export_to_sheets(self, api_client, test_coach, test_client):
        """Test Google Sheets export"""
        with patch('backend_api.GoogleSheetsService.create_or_update_sheet') as mock_sheets:
            mock_sheets.return_value = "test_sheet_id_12345"
            
            response = await api_client.get(f"/coaches/{test_coach}/export")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "exported"
            assert "sheet_url" in data
            assert "test_sheet_id_12345" in data["sheet_url"]

class TestAnalytics:
    """Test analytics and reporting"""
    
    @pytest.mark.asyncio
    async def test_coach_analytics(self, api_client, test_coach):
        """Test coach analytics endpoint"""
        response = await api_client.get(f"/coaches/{test_coach}/analytics")
        assert response.status_code == 200
        
        data = response.json()
        assert "message_analytics" in data
        assert "client_engagement" in data
        assert isinstance(data["message_analytics"], list)
        assert isinstance(data["client_engagement"], list)
    
    @pytest.mark.asyncio
    async def test_system_stats(self, api_client):
        """Test system statistics"""
        # This would require admin authentication in production
        with patch('admin_api_endpoints.verify_admin_access') as mock_admin:
            mock_admin.return_value = {"id": "admin_id", "name": "Admin"}
            
            response = await api_client.get("/admin/stats?range=7d")
            assert response.status_code == 200
            
            data = response.json()
            assert "total_coaches" in data
            assert "total_clients" in data
            assert "messages_sent" in data
            assert "success_rate" in data

class TestBackgroundTasks:
    """Test background task processing"""
    
    @pytest.mark.asyncio
    async def test_scheduled_message_processing(self, db_conn, test_coach, test_client):
        """Test scheduled message background processing"""
        # Create a message due now
        past_time = datetime.now() - timedelta(minutes=1)
        
        scheduled_id = await db_conn.fetchval(
            """INSERT INTO scheduled_messages 
               (coach_id, client_id, message_type, content, schedule_type, scheduled_time, status)
               VALUES ($1, $2, 'celebration', 'Overdue test message', 'specific', $3, 'scheduled')
               RETURNING id""",
            test_coach, test_client, past_time
        )
        
        # Test the background task
        with patch('worker.WhatsAppClient.send_message') as mock_send:
            mock_send.return_value = {"messages": [{"id": "bg_task_msg_id"}]}
            
            from worker import send_whatsapp_message
            
            # Run the task synchronously for testing
            result = send_whatsapp_message.apply(args=[str(scheduled_id)])
            assert result.successful()
            
            # Verify message status updated
            status = await db_conn.fetchval(
                "SELECT status FROM scheduled_messages WHERE id = $1",
                scheduled_id
            )
            assert status == "sent"

class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_api_error_responses(self, api_client):
        """Test API error handling"""
        # Test invalid coach ID
        response = await api_client.get("/coaches/invalid-uuid/clients")
        assert response.status_code == 500  # Should handle gracefully
        
        # Test missing data
        response = await api_client.post("/messages/send", json={})
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_whatsapp_api_failure_handling(self, api_client, test_coach, test_client):
        """Test handling WhatsApp API failures"""
        message_data = {
            "client_ids": [test_client],
            "message_type": "celebration",
            "content": "Test message",
            "schedule_type": "now"
        }
        
        # Mock WhatsApp API failure
        with patch('backend_api.WhatsAppClient.send_message') as mock_send:
            mock_send.side_effect = Exception("WhatsApp API Error")
            
            response = await api_client.post("/messages/send", json=message_data)
            # Should still return success but message will be marked as failed
            assert response.status_code == 200

class TestIntegrationWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_coaching_workflow(self, api_client, db_conn):
        """Test complete workflow from registration to message sending"""
        # Step 1: Coach registration
        registration_data = {
            "barcode": f"integration_test_{datetime.now().timestamp()}",
            "whatsapp_token": "integration_test_token",
            "name": "Integration Test Coach",
            "email": "integration@test.com",
            "timezone": "EST"
        }
        
        reg_response = await api_client.post("/register", json=registration_data)
        assert reg_response.status_code == 200
        coach_id = reg_response.json()["coach_id"]
        
        # Step 2: Add clients
        clients = []
        for i in range(2):
            client_data = {
                "name": f"Integration Client {i}",
                "phone_number": f"+199999999{i}",
                "country": "USA",
                "timezone": "EST",
                "categories": ["Health", "Business"]
            }
            
            client_response = await api_client.post(f"/coaches/{coach_id}/clients", json=client_data)
            assert client_response.status_code == 200
            clients.append(client_response.json()["client_id"])
        
        # Step 3: Send celebration messages
        with patch('backend_api.WhatsAppClient.send_message') as mock_send:
            mock_send.return_value = {"messages": [{"id": "integration_msg_id"}]}
            
            message_data = {
                "client_ids": clients,
                "message_type": "celebration",
                "content": "🎉 Integration test celebration!",
                "schedule_type": "now"
            }
            
            msg_response = await api_client.post("/messages/send", json=message_data)
            assert msg_response.status_code == 200
            assert len(msg_response.json()["message_ids"]) == 2
        
        # Step 4: Export to Google Sheets
        with patch('backend_api.GoogleSheetsService.create_or_update_sheet') as mock_sheets:
            mock_sheets.return_value = "integration_sheet_id"
            
            export_response = await api_client.get(f"/coaches/{coach_id}/export")
            assert export_response.status_code == 200
            assert export_response.json()["status"] == "exported"
        
        # Step 5: Verify data in database
        client_count = await db_conn.fetchval(
            "SELECT COUNT(*) FROM clients WHERE coach_id = $1",
            coach_id
        )
        assert client_count == 2

class TestPerformance:
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, api_client):
        """Test handling concurrent API requests"""
        async def make_request():
            return await api_client.get("/health")
        
        # Create 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful responses
        success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        
        # At least 90% should succeed
        assert success_count >= 45
    
    @pytest.mark.asyncio
    async def test_large_client_list_performance(self, api_client, test_coach):
        """Test performance with large client lists"""
        import time
        
        # Add 100 clients
        start_time = time.time()
        
        client_ids = []
        for i in range(100):
            client_data = {
                "name": f"Performance Client {i}",
                "phone_number": f"+1{str(i).zfill(10)}",
                "country": "USA",
                "timezone": "EST",
                "categories": ["Health"]
            }
            
            response = await api_client.post(f"/coaches/{test_coach}/clients", json=client_data)
            if response.status_code == 200:
                client_ids.append(response.json()["client_id"])
        
        creation_time = time.time() - start_time
        
        # Test retrieving all clients
        start_time = time.time()
        response = await api_client.get(f"/coaches/{test_coach}/clients")
        retrieval_time = time.time() - start_time
        
        assert response.status_code == 200
        clients = response.json()
        assert len(clients) >= 100
        
        # Performance assertions
        assert creation_time < 60  # Should create 100 clients in under 60 seconds
        assert retrieval_time < 5   # Should retrieve clients in under 5 seconds

# Test runner and configuration
class TestRunner:
    """Test runner with custom configuration"""
    
    @staticmethod
    def setup_test_database():
        """Set up test database"""
        try:
            # Create test database if it doesn't exist
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            
            # Connect to postgres to create test database
            conn = psycopg2.connect(
                host=TEST_CONFIG["DB_CONFIG"]["host"],
                port=TEST_CONFIG["DB_CONFIG"]["port"],
                user=TEST_CONFIG["DB_CONFIG"]["user"],
                password=TEST_CONFIG["DB_CONFIG"]["password"],
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS {TEST_CONFIG['DB_CONFIG']['database']}")
            cursor.execute(f"CREATE DATABASE {TEST_CONFIG['DB_CONFIG']['database']}")
            
            cursor.close()
            conn.close()
            
            # Run schema on test database
            test_conn = psycopg2.connect(**TEST_CONFIG["DB_CONFIG"])
            test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with open('database_schema.sql', 'r') as f:
                schema_sql = f.read()
            
            cursor = test_conn.cursor()
            cursor.execute(schema_sql)
            cursor.close()
            test_conn.close()
            
            print("✅ Test database setup completed")
            
        except Exception as e:
            print(f"❌ Test database setup failed: {e}")
            raise
    
    @staticmethod
    def run_all_tests():
        """Run comprehensive test suite"""
        print("🧪 Starting comprehensive test suite...")
        
        # Setup test environment
        TestRunner.setup_test_database()
        
        # Run tests with detailed output
        pytest_args = [
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "--strict-markers",  # Strict marker usage
            "--strict-config",  # Strict config
            "-x",  # Stop on first failure
            "--cov=backend_api",  # Code coverage for main API
            "--cov=worker",  # Code coverage for worker
            "--cov-report=html",  # HTML coverage report
            "--cov-report=term-missing",  # Terminal coverage report
            __file__  # This test file
        ]
        
        exit_code = pytest.main(pytest_args)
        
        if exit_code == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed. Check the output above.")
        
        return exit_code

# Stress testing
class StressTests:
    """Stress tests for system limits"""
    
    @pytest.mark.stress
    async def test_high_volume_message_sending(self, api_client, test_coach):
        """Test sending high volume of messages"""
        # Create 500 clients
        client_ids = []
        for i in range(500):
            client_data = {
                "name": f"Stress Client {i}",
                "phone_number": f"+1{str(i).zfill(10)}",
                "country": "USA",
                "timezone": "EST",
                "categories": ["Health"]
            }
            
            response = await api_client.post(f"/coaches/{test_coach}/clients", json=client_data)
            if response.status_code == 200:
                client_ids.append(response.json()["client_id"])
        
        # Send bulk message to all
        with patch('worker.WhatsAppClient.send_message') as mock_send:
            mock_send.return_value = {"messages": [{"id": "stress_msg_id"}]}
            
            bulk_data = {
                "client_ids": client_ids,
                "content": "Stress test message",
                "message_type": "general",
                "schedule_type": "now"
            }
            
            import time
            start_time = time.time()
            
            response = await api_client.post(f"/coaches/{test_coach}/bulk-message", json=bulk_data)
            
            processing_time = time.time() - start_time
            
            assert response.status_code == 200
            assert processing_time < 30  # Should queue 500 messages in under 30 seconds

# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "run":
            # Run all tests
            exit_code = TestRunner.run_all_tests()
            sys.exit(exit_code)
        elif sys.argv[1] == "setup":
            # Just setup test database
            TestRunner.setup_test_database()
        elif sys.argv[1] == "stress":
            # Run stress tests only
            pytest.main(["-v", "-m", "stress", __file__])
    else:
        print("Usage:")
        print("  python test_suite.py run     # Run all tests")
        print("  python test_suite.py setup   # Setup test database")
        print("  python test_suite.py stress  # Run stress tests only")