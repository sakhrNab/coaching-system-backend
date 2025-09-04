# WhatsApp Template & Conversation Tracking Deployment Guide

## 🎯 **Overview**

This guide covers deploying the enhanced WhatsApp messaging system with:
- 24-hour conversation window tracking
- Automatic template message detection
- Enhanced webhook handling
- Database conversation tracking

## 📋 **Prerequisites**

1. **WhatsApp Business API Access**
2. **10 Approved Templates** (already created)
3. **Meta Developer Account**
4. **Production Domain** with HTTPS

## 🔧 **Environment Variables**

Add these to your `.env` file:

```bash
# WhatsApp Configuration
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WEBHOOK_VERIFY_TOKEN=your_secure_verify_token

# Database (already configured)
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=coaching_system
```

## 🗄️ **Database Migration**

### 1. Run Conversation Tracking Migration

```bash
# Copy migration to container
docker cp database/conversation_tracking.sql coaching_postgres_prod:/tmp/conversation_tracking.sql

# Run migration
docker-compose exec postgres psql -U postgres -d coaching_system -f /tmp/conversation_tracking.sql
```

### 2. Verify Migration

```bash
# Check tables created
docker-compose exec postgres psql -U postgres -d coaching_system -c "\dt whatsapp_conversations"

# Test functions
docker-compose exec postgres psql -U postgres -d coaching_system -c "SELECT can_send_free_message('201280682640');"
```

## 🌐 **Meta Webhook Configuration**

### 1. Webhook URL
```
https://your-production-domain.com/webhook/whatsapp
```

### 2. Verify Token
Use the same token as `WEBHOOK_VERIFY_TOKEN` in your environment variables.

### 3. Webhook Fields
Enable these fields in Meta Developer Console:
- ✅ `messages`
- ✅ `messages.status` 
- ✅ `conversations`

### 4. Webhook Verification Test

```bash
# Test webhook verification
curl -X GET "https://your-domain.com/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=your_verify_token&hub.challenge=test123"
```

Expected response: `test123`

## 🧪 **Testing the Implementation**

### 1. Run Template Tests

```bash
# Run comprehensive tests
python test_whatsapp_templates.py
```

### 2. Test Template Message Sending

```bash
# Test celebration message (should send as template)
curl -X POST http://localhost:8001/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "client_ids": ["your-client-id"],
    "message_type": "celebration",
    "content": "🎉 What are we celebrating today?",
    "schedule_type": "now"
  }'
```

### 3. Test Conversation Status

```bash
# Check conversation status
curl -X GET http://localhost:8001/webhook/conversation-status/201280682640
```

## 📱 **Frontend Updates**

The frontend now shows:
- ✅ Template indicators on celebration messages
- ✅ Clear distinction between template and custom messages
- ✅ Information about conversation initiation

## 🔄 **Message Flow Logic**

### Template Messages (Always Templates)
These messages are automatically sent as WhatsApp templates:
- 🎉 What are we celebrating today?
- ✨ What are you grateful for?
- 🌟 What victory are you proud of today?
- 🎊 What positive moment made your day?
- 💫 What breakthrough did you experience?
- 📝 How did you progress on your goals today?
- 🎯 What action did you take towards your target?
- 💪 What challenge did you overcome today?
- 📈 How are you measuring your progress?
- 🔥 What will you commit to tomorrow?

### Custom Messages
- **Within 24h window**: Sent as free text message
- **Outside 24h window**: Sent as template (charged)

## 🚀 **Deployment Steps**

### 1. Deploy Backend Changes

```bash
# Commit all changes
git add .
git commit -m "Implement WhatsApp template messaging and conversation tracking"

# Push to production
git push origin main
```

### 2. Deploy Frontend Changes

```bash
cd ../coaching-system-frontend
git add .
git commit -m "Add template indicators to frontend"
git push origin main
```

### 3. Restart Services

```bash
# Restart backend
docker-compose down
docker-compose up -d

# Run database migration
docker-compose exec postgres psql -U postgres -d coaching_system -f /tmp/conversation_tracking.sql
```

### 4. Configure Meta Webhook

1. Go to Meta Developer Console
2. Navigate to WhatsApp > Configuration
3. Set Webhook URL: `https://your-domain.com/webhook/whatsapp`
4. Set Verify Token: `your_verify_token`
5. Subscribe to: `messages`, `messages.status`, `conversations`

## 🔍 **Monitoring & Debugging**

### 1. Check Logs

```bash
# Backend logs
docker-compose logs backend --tail=50

# Look for these log entries:
# 🚀 WhatsApp Template API Request
# 📥 WhatsApp Template API Response
# 💬 Recorded conversation
# 📤 Sending template message
```

### 2. Database Queries

```bash
# Check active conversations
docker-compose exec postgres psql -U postgres -d coaching_system -c "
SELECT wa_id, conversation_id, expires_at, is_active 
FROM whatsapp_conversations 
WHERE is_active = true;"

# Check conversation status for specific user
docker-compose exec postgres psql -U postgres -d coaching_system -c "
SELECT can_send_free_message('201280682640');"
```

### 3. Webhook Testing

```bash
# Test webhook endpoint
curl -X POST https://your-domain.com/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "test",
      "changes": [{
        "value": {
          "statuses": [{
            "id": "test_msg",
            "recipient_id": "201280682640",
            "status": "sent",
            "conversation": {
              "id": "test_conv",
              "expiration_timestamp": "1694209856",
              "origin": {"type": "user_initiated"}
            }
          }]
        },
        "field": "messages.status"
      }]
    }]
  }'
```

## ✅ **Verification Checklist**

- [ ] Database migration completed successfully
- [ ] Environment variables configured
- [ ] Meta webhook configured and verified
- [ ] Template messages send as templates
- [ ] Custom messages respect 24h window
- [ ] Conversation tracking working
- [ ] Frontend shows template indicators
- [ ] All tests passing
- [ ] Production deployment successful

## 🆘 **Troubleshooting**

### Common Issues

1. **Template not found**: Check template name mapping in `whatsapp_templates.py`
2. **Webhook not receiving**: Verify URL and token in Meta console
3. **Conversation not tracked**: Check webhook fields subscription
4. **Messages not sending**: Check WhatsApp access token and phone number ID

### Debug Commands

```bash
# Check template mapping
python -c "from backend.whatsapp_templates import template_manager; print(template_manager.get_all_templates())"

# Test conversation functions
docker-compose exec postgres psql -U postgres -d coaching_system -c "SELECT * FROM get_active_conversation('201280682640');"

# Check webhook logs
docker-compose logs backend | grep -i webhook
```

## 📞 **Support**

If you encounter issues:
1. Check the logs first
2. Verify environment variables
3. Test webhook configuration
4. Run the test scripts
5. Check Meta Developer Console for API errors

