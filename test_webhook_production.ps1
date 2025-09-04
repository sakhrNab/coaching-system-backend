# Test Production Webhook Endpoints
Write-Host "🧪 Testing Production Webhook Endpoints" -ForegroundColor Green

$baseUrl = "http://s8oc4oswwgcc4gw4cwg8kcsw.63.250.59.208.sslip.io"
$verifyToken = "your_secure_verify_token"

# Test 1: Webhook Verification
Write-Host "`n1. Testing Webhook Verification..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=$verifyToken&hub.challenge=test123" -Method GET
    Write-Host "✅ Verification Success: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ Verification Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Webhook POST with proper JSON
Write-Host "`n2. Testing Webhook POST..." -ForegroundColor Yellow
$webhookData = @{
    object = "whatsapp_business_account"
    entry = @(
        @{
            id = "test"
            changes = @(
                @{
                    value = @{
                        messaging_product = "whatsapp"
                        statuses = @(
                            @{
                                id = "test_msg"
                                recipient_id = "201280682640"
                                status = "sent"
                                conversation = @{
                                    id = "test_conv"
                                    expiration_timestamp = "1694209856"
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

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/webhook/whatsapp" -Method POST -Headers @{"Content-Type"="application/json"} -Body $webhookData
    Write-Host "✅ POST Success: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ POST Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check available endpoints
Write-Host "`n3. Checking Available Endpoints..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/docs" -Method GET
    Write-Host "✅ API Docs accessible" -ForegroundColor Green
} catch {
    Write-Host "❌ API Docs failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 Webhook Testing Complete!" -ForegroundColor Cyan
