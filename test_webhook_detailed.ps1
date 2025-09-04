# Detailed Webhook Test
Write-Host "🔍 Detailed Webhook Testing" -ForegroundColor Green

$baseUrl = "http://s8oc4oswwgcc4gw4cwg8kcsw.63.250.59.208.sslip.io"

# Test 1: Check if webhook endpoint exists
Write-Host "`n1. Checking webhook endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/webhook/whatsapp" -Method GET
    Write-Host "❌ GET should not work: $($response.StatusCode)" -ForegroundColor Red
} catch {
    Write-Host "✅ GET properly returns error: $($_.Exception.Message)" -ForegroundColor Green
}

# Test 2: Test webhook POST with detailed logging
Write-Host "`n2. Testing webhook POST with detailed data..." -ForegroundColor Yellow
$webhookData = @{
    object = "whatsapp_business_account"
    entry = @(
        @{
            id = "test_entry_123"
            changes = @(
                @{
                    value = @{
                        messaging_product = "whatsapp"
                        metadata = @{
                            display_phone_number = "1234567890"
                            phone_number_id = "123456789012345"
                        }
                        statuses = @(
                            @{
                                id = "wamid.test_message_123"
                                recipient_id = "201280682640"
                                status = "sent"
                                timestamp = "1694209856"
                                conversation = @{
                                    id = "test_conversation_123"
                                    expiration_timestamp = "1694296256"
                                    origin = @{
                                        type = "user_initiated"
                                    }
                                }
                            }
                        )
                    }
                    field = "messages.status"
                }
            )
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Sending webhook data:" -ForegroundColor Cyan
Write-Host $webhookData -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/webhook/whatsapp" -Method POST -Headers @{"Content-Type"="application/json"} -Body $webhookData
    Write-Host "✅ POST Response: $($response.Content)" -ForegroundColor Green
    Write-Host "✅ Status Code: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ POST Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check if we can access the conversation status endpoint
Write-Host "`n3. Testing conversation status endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/webhook/conversation-status/201280682640" -Method GET
    Write-Host "✅ Conversation Status: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ Conversation Status Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nDetailed Testing Complete!" -ForegroundColor Cyan
