# Complete API Documentation - Coaching System Backend

## 📋 **Overview**
This document contains **ALL 45+ endpoints** in your coaching system API with complete request examples and real-world testing instructions.

## 🔧 **Base URL**
```
http://localhost:8001
```

## ✅ **Tested Endpoints Status**
- ✅ = Successfully tested and working
- ⚠️ = Requires authentication/configuration
- ❌ = Not found or not working

---

## **🔧 Core Endpoints**

### 1. Root Endpoint
**✅ GET /**

**Description:** Get API status information

**Request:**
```bash
curl -X GET http://localhost:8001/
```

**Response:**
```json
{
  "message": "Coaching System API",
  "status": "operational"
}
```

### 2. Health Check
**✅ GET /health**

**Description:** Basic health check with database status

**Request:**
```bash
curl -X GET http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-03T16:03:01.947195",
  "database": "connected"
}
```

### 3. Detailed Health Check
**❌ GET /health/detailed**

**Description:** Comprehensive system health monitoring

**Request:**
```bash
curl -X GET http://localhost:8001/health/detailed
```

**Status:** Not found - endpoint may not be properly registered

### 4. System Configuration
**✅ GET /config**

**Description:** Get system features and configuration

**Request:**
```bash
curl -X GET http://localhost:8001/config
```

**Response:**
```json
{
  "features": {
    "google_contacts": true,
    "voice_processing": true,
    "whatsapp_integration": true,
    "google_sheets": true
  },
  "timezones": ["EST", "PST", "CST", "MST", "GMT", "CET", "JST", "AEST"],
  "supported_file_types": [".csv", ".xlsx", ".json"]
}
```

---

## **👤 Coach Management**

### 5. Coach Registration
**✅ POST /register**

**Description:** Register a new coach account

**Request:**
```bash
curl -X POST http://localhost:8001/register \
  -H "Content-Type: application/json" \
  -d '{
    "barcode": "test-coach-123",
    "name": "John Coach",
    "email": "john@coaching.com",
    "whatsapp_token": "wa_token_123",
    "timezone": "EST"
  }'
```

**Response:**
```json
{
  "status": "registered",
  "coach_id": "a61b09a2-1f8d-473c-9e48-6dc50f5a2eac"
}
```

### 6. Get Coach Categories
**✅ GET /coaches/{coach_id}/categories**

**Description:** Get all coaching categories for a coach

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/categories
```

**Response:**
```json
[
  {"name": "Business", "is_predefined": true},
  {"name": "Career", "is_predefined": true},
  {"name": "Communication", "is_predefined": true},
  {"name": "Creativity", "is_predefined": true},
  {"name": "Diet", "is_predefined": true},
  {"name": "Finance", "is_predefined": true},
  {"name": "Growth", "is_predefined": true},
  {"name": "Health", "is_predefined": true},
  {"name": "Relationship", "is_predefined": true},
  {"name": "Socialization", "is_predefined": true},
  {"name": "Writing", "is_predefined": true},
  {"name": "Weight", "is_predefined": true}
]
```

### 7. Create Category
**⚠️ POST /coaches/{coach_id}/categories**

**Description:** Create a custom category for a coach

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/categories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Category"
  }'
```

---

## **👥 Client Management**

### 8. Get All Clients
**✅ GET /coaches/{coach_id}/clients**

**Description:** Get all clients for a coach

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/clients
```

**Response:**
```json
[
  {
    "id": "09859d4c-aa56-4eed-82f2-e669b182c534",
    "name": "Test Client API",
    "phone_number": "+1555000APIDOC",
    "country": "US",
    "timezone": "EST",
    "is_active": true,
    "created_at": "2025-09-03T16:03:37Z"
  }
]
```

### 9. Add New Client
**✅ POST /coaches/{coach_id}/clients**

**Description:** Add a new client to a coach

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sarah Johnson",
    "phone_number": "+15551234567",
    "country": "US",
    "timezone": "PST",
    "categories": ["Health", "Career"]
  }'
```

**Response:**
```json
{
  "client_id": "09859d4c-aa56-4eed-82f2-e669b182c534",
  "status": "created"
}
```

### 10. Update Client
**⚠️ PUT /coaches/{coach_id}/clients/{client_id}**

**Description:** Update client information

**Request:**
```bash
curl -X PUT http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/clients/09859d4c-aa56-4eed-82f2-e669b182c534 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sarah Johnson Updated",
    "phone_number": "+15551234567",
    "country": "US",
    "timezone": "PST"
  }'
```

### 11. Delete Client
**⚠️ DELETE /coaches/{coach_id}/clients/{client_id}**

**Description:** Delete a client

**Request:**
```bash
curl -X DELETE http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/clients/09859d4c-aa56-4eed-82f2-e669b182c534
```

### 12. Get Client Message History
**⚠️ GET /coaches/{coach_id}/clients/{client_id}/history**

**Description:** Get message history for a specific client

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/clients/09859d4c-aa56-4eed-82f2-e669b182c534/history
```

---

## **📝 Message Templates**

### 13. Get Message Templates
**✅ GET /coaches/{coach_id}/templates**

**Description:** Get all message templates for a coach

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/templates
```

**Response:**
```json
[
  {
    "id": "337b70ae-71a0-4597-87a8-18b66a33eeca",
    "message_type": "celebration",
    "content": "🎉 What are we celebrating today?",
    "is_default": true
  },
  {
    "id": "d78c4eb1-fc41-484b-a353-1cbbfb0ed376",
    "message_type": "celebration",
    "content": "✨ What are you grateful for?",
    "is_default": true
  }
]
```

### 14. Create Template
**⚠️ POST /coaches/{coach_id}/templates**

**Description:** Create a custom message template

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/templates \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "celebration",
    "content": "🎊 What victory are you proud of today?"
  }'
```

---

## **💬 Messaging**

### 15. Send Message
**⚠️ POST /messages/send**

**Description:** Send a message to a client

**Request:**
```bash
curl -X POST http://localhost:8001/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "coach_id": "a61b09a2-1f8d-473c-9e48-6dc50f5a2eac",
    "client_id": "09859d4c-aa56-4eed-82f2-e669b182c534",
    "message": "Hello! How are you doing today?",
    "message_type": "general"
  }'
```

### 16. Send Message (Alternative)
**⚠️ POST /coaches/{coach_id}/send-message**

**Description:** Send message using coach-specific endpoint

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "09859d4c-aa56-4eed-82f2-e669b182c534",
    "message_type": "celebration",
    "content": "Great job today! Keep it up!"
  }'
```

### 17. Bulk Message
**⚠️ POST /coaches/{coach_id}/bulk-message**

**Description:** Send messages to multiple clients

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/bulk-message \
  -H "Content-Type: application/json" \
  -d '{
    "client_ids": ["client_id_1", "client_id_2"],
    "message": "Weekly check-in: How are your goals progressing?",
    "message_type": "checkin"
  }'
```

---

## **📊 Analytics & Reporting**

### 18. Coach Statistics
**✅ GET /coaches/{coach_id}/stats**

**Description:** Get coach performance statistics

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/stats
```

**Response:**
```json
{
  "total_clients": 1,
  "messages_sent_month": 0,
  "pending_messages": 0,
  "active_goals": 0,
  "recent_activity": []
}
```

### 19. Coach Analytics
**⚠️ GET /coaches/{coach_id}/analytics**

**Description:** Get detailed analytics for a coach

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/analytics
```

### 20. Data Export
**⚠️ GET /coaches/{coach_id}/export**

**Description:** Export coach data

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/export
```

---

## **🎯 Goals Management**

### 21. Get Client Goals
**⚠️ GET /coaches/{coach_id}/goals**

**Description:** Get all goals for a coach's clients

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/goals
```

### 22. Create Client Goal
**⚠️ POST /coaches/{coach_id}/clients/{client_id}/goals**

**Description:** Create a goal for a client

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/clients/09859d4c-aa56-4eed-82f2-e669b182c534/goals \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Lose 10 pounds",
    "description": "Weight loss goal for better health",
    "category_id": "category_id_here",
    "target_date": "2025-12-31"
  }'
```

---

## **📅 Scheduled Messages**

### 23. Get Scheduled Messages
**⚠️ GET /coaches/{coach_id}/scheduled-messages**

**Description:** Get all scheduled messages for a coach

**Request:**
```bash
curl -X GET http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/scheduled-messages
```

### 24. Delete Scheduled Message
**⚠️ DELETE /scheduled-messages/{message_id}**

**Description:** Delete a scheduled message

**Request:**
```bash
curl -X DELETE http://localhost:8001/scheduled-messages/message_id_here
```

---

## **🔗 External Integrations**

### 25. Import Clients
**⚠️ POST /coaches/{coach_id}/import-clients**

**Description:** Import clients from CSV or other sources

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/import-clients \
  -H "Content-Type: application/json" \
  -d '{
    "source": "csv",
    "data": "CSV_DATA_HERE"
  }'
```

### 26. Import Google Contacts
**⚠️ POST /coaches/{coach_id}/import-google-contacts**

**Description:** Import contacts from Google

**Request:**
```bash
curl -X POST http://localhost:8001/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/import-google-contacts \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "google_oauth_token_here"
  }'
```

---

## **🎤 Voice Processing**

### 27. Process Voice Message
**⚠️ POST /voice/process**

**Description:** Process voice messages for transcription

**Request:**
```bash
curl -X POST http://localhost:8001/voice/process \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://example.com/audio.mp3",
    "coach_id": "a61b09a2-1f8d-473c-9e48-6dc50f5a2eac"
  }'
```

---

## **📱 WhatsApp Webhooks**

### 28. WhatsApp Webhook Verification
**⚠️ GET /webhook/whatsapp**

**Description:** Verify WhatsApp webhook

**Request:**
```bash
curl -X GET "http://localhost:8001/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test_challenge"
```

**Note:** Returns challenge string if verification token matches

### 29. WhatsApp Webhook Handler
**⚠️ POST /webhook/whatsapp**

**Description:** Handle incoming WhatsApp messages

**Request:**
```bash
curl -X POST http://localhost:8001/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "+15551234567",
            "text": {"body": "Hello"}
          }]
        }
      }]
    }]
  }'
```

---

## **⚙️ Admin Endpoints** (Require Authentication)

### 30. System Statistics
**⚠️ GET /admin/stats**

**Description:** Get system-wide statistics

**Request:**
```bash
curl -X GET http://localhost:8001/admin/stats \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 31. List All Coaches
**⚠️ GET /admin/coaches**

**Description:** Get all coaches in the system

**Request:**
```bash
curl -X GET http://localhost:8001/admin/coaches \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 32. Detailed Coach Info
**⚠️ GET /admin/coaches/{coach_id}/detailed**

**Description:** Get detailed information about a coach

**Request:**
```bash
curl -X GET http://localhost:8001/admin/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/detailed \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 33. Suspend Coach
**⚠️ POST /admin/coaches/{coach_id}/suspend**

**Description:** Suspend a coach account

**Request:**
```bash
curl -X POST http://localhost:8001/admin/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/suspend \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Violation of terms"}'
```

### 34. Reset API Token
**⚠️ POST /admin/coaches/{coach_id}/reset-api**

**Description:** Reset a coach's API token

**Request:**
```bash
curl -X POST http://localhost:8001/admin/coaches/a61b09a2-1f8d-473c-9e48-6dc50f5a2eac/reset-api \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_token": "new_whatsapp_token_here"}'
```

### 35. System Activity
**⚠️ GET /admin/activity**

**Description:** Get system activity logs

**Request:**
```bash
curl -X GET http://localhost:8001/admin/activity \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 36. Export Reports
**⚠️ GET /admin/export-report**

**Description:** Export system reports

**Request:**
```bash
curl -X GET http://localhost:8001/admin/export-report \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 37. Analytics Summary
**⚠️ GET /admin/analytics/summary**

**Description:** Get system-wide analytics

**Request:**
```bash
curl -X GET http://localhost:8001/admin/analytics/summary \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 38. System Restart
**⚠️ POST /admin/system/restart**

**Description:** Restart system services

**Request:**
```bash
curl -X POST http://localhost:8001/admin/system/restart \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 39. System Performance
**⚠️ GET /admin/system/performance**

**Description:** Get system performance metrics

**Request:**
```bash
curl -X GET http://localhost:8001/admin/system/performance \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 40. Queue Status
**⚠️ GET /admin/system/queue-status**

**Description:** Get message queue status

**Request:**
```bash
curl -X GET http://localhost:8001/admin/system/queue-status \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 41. Clear Cache
**⚠️ POST /admin/system/clear-cache**

**Description:** Clear system cache

**Request:**
```bash
curl -X POST http://localhost:8001/admin/system/clear-cache \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 42. System Cleanup
**⚠️ POST /admin/maintenance/cleanup**

**Description:** Run system maintenance cleanup

**Request:**
```bash
curl -X POST http://localhost:8001/admin/maintenance/cleanup \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 43. System Logs
**⚠️ GET /admin/logs**

**Description:** Get system logs

**Request:**
```bash
curl -X GET http://localhost:8001/admin/logs \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 44. Recent Errors
**⚠️ GET /admin/errors/recent**

**Description:** Get recent system errors

**Request:**
```bash
curl -X GET http://localhost:8001/admin/errors/recent \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 45. Database Backup
**⚠️ POST /admin/backup**

**Description:** Create database backup

**Request:**
```bash
curl -X POST http://localhost:8001/admin/backup \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## **📊 Testing Summary**

### **✅ Successfully Tested Endpoints:**
1. `GET /` - Root endpoint
2. `GET /health` - Health check
3. `GET /config` - System configuration
4. `POST /register` - Coach registration
5. `GET /coaches/{id}/categories` - Get categories
6. `GET /coaches/{id}/clients` - Get clients
7. `POST /coaches/{id}/clients` - Add client
8. `GET /coaches/{id}/templates` - Get templates
9. `GET /coaches/{id}/stats` - Coach statistics

### **⚠️ Endpoints Requiring Authentication:**
- All `/admin/*` endpoints require admin authentication
- Some coach-specific endpoints may require authentication
- WhatsApp webhooks require proper verification tokens

### **❌ Endpoints Not Working:**
- `GET /health/detailed` - Not found (endpoint may not be registered)

---

## **🔐 Authentication Notes**

### **For Admin Endpoints:**
Most admin endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer YOUR_ADMIN_JWT_TOKEN
```

### **For WhatsApp Webhooks:**
Webhook verification requires matching the `WEBHOOK_VERIFY_TOKEN` environment variable.

### **For Coach-Specific Endpoints:**
Some endpoints may require coach authentication (JWT token).

---

## **🚀 Quick Test Commands**

### **Test Basic Functionality:**
```bash
# 1. Check API status
curl http://localhost:8001/

# 2. Register a coach
curl -X POST http://localhost:8001/register -H "Content-Type: application/json" -d '{"barcode": "test-123", "name": "Test Coach", "email": "test@example.com", "whatsapp_token": "test-token", "timezone": "EST"}'

# 3. Get categories (replace COACH_ID)
curl http://localhost:8001/coaches/COACH_ID/categories

# 4. Add a client
curl -X POST http://localhost:8001/coaches/COACH_ID/clients -H "Content-Type: application/json" -d '{"name": "Test Client", "phone_number": "+15550001234", "country": "US", "timezone": "EST"}'

# 5. Get templates
curl http://localhost:8001/coaches/COACH_ID/templates
```

### **Test Admin Endpoints (if authenticated):**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8001/admin/stats
```

---

## **📝 Notes**

- **Coach ID**: `a61b09a2-1f8d-473c-9e48-6dc50f5a2eac` (from our test registration)
- **Client ID**: `09859d4c-aa56-4eed-82f2-e669b182c534` (from our test client)
- **Base URL**: `http://localhost:8001`
- **Content-Type**: Always use `application/json` for POST/PUT requests
- **Authentication**: Required for admin endpoints and some coach operations

This documentation covers all **45+ endpoints** in your coaching system API! 🎉
