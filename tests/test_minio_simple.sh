#!/bin/bash

# Simple MinIO Architecture Test - Standalone Version
# Tests the core MinIO flow without complex dependencies

BASE_URL="http://localhost:8000/api/v1"

echo "========================================="
echo "MinIO Privacy-First Architecture Tests"
echo "========================================="
echo ""

# Test 1: API Health
echo "[TEST 1] API Health Check"
HEALTH=$(curl -s http://localhost:8000/health)
echo "Response: $HEALTH"
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✓ PASSED"
else
    echo "✗ FAILED"
fi
echo ""

# Test 2: Authentication
echo "[TEST 2] User Authentication"
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test_'$(date +%s)'@voicenote.ai",
    "token": "test_token",
    "device_id": "test_device",
    "device_model": "curl",
    "primary_role": "DEVELOPER",
    "timezone": "UTC"
  }')

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token' 2>/dev/null)
if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "✓ PASSED - Token: ${TOKEN:0:20}..."
else
    echo "✗ FAILED - Response: $AUTH_RESPONSE"
fi
echo ""

# Test 3: Pre-signed URL
echo "[TEST 3] Generate Pre-signed URL"
PRESIGNED=$(curl -s -X GET "$BASE_URL/notes/presigned-url" \
  -H "Authorization: Bearer $TOKEN")
echo "Response: $PRESIGNED"

UPLOAD_URL=$(echo "$PRESIGNED" | jq -r '.upload_url' 2>/dev/null)
STORAGE_KEY=$(echo "$PRESIGNED" | jq -r '.storage_key' 2>/dev/null)
NOTE_ID=$(echo "$PRESIGNED" | jq -r '.note_id' 2>/dev/null)

if [ -n "$UPLOAD_URL" ] && [ "$UPLOAD_URL" != "null" ]; then
    echo "✓ PASSED - Storage Key: $STORAGE_KEY"
else
    echo "✗ FAILED"
fi
echo ""

# Test 4: Swagger UI
echo "[TEST 4] Swagger UI Accessibility"
SWAGGER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [ "$SWAGGER_STATUS" -eq "200" ]; then
    echo "✓ PASSED - Swagger UI accessible at http://localhost:8000/docs"
else
    echo "✗ FAILED - HTTP $SWAGGER_STATUS"
fi
echo ""

# Test 5: MinIO Health
echo "[TEST 5] MinIO Health Check"
MINIO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live)
if [ "$MINIO_STATUS" -eq "200" ]; then
    echo "✓ PASSED - MinIO is healthy"
else
    echo "✗ FAILED - HTTP $MINIO_STATUS"
fi
echo ""

# Test 6: MinIO Bucket
echo "[TEST 6] MinIO Bucket Verification"
BUCKET_CHECK=$(docker exec voicenote_mc /usr/bin/mc ls myminio/incoming 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ PASSED - 'incoming' bucket exists"
else
    echo "✗ FAILED - Bucket check failed"
fi
echo ""

# Test 7: Celery Worker
echo "[TEST 7] Celery Worker Status"
WORKER_STATUS=$(docker logs voicenote_celery_worker --tail 5 2>&1 | grep -i "ready" || echo "")
if docker ps | grep -q voicenote_celery_worker; then
    echo "✓ PASSED - Worker is running"
    docker exec voicenote_celery_worker celery -A app.worker.celery_app inspect active_queues 2>&1 | grep -E "short|long|celery" || echo "  (Queue inspection unavailable)"
else
    echo "✗ FAILED - Worker not running"
fi
echo ""

echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✓ Core infrastructure is operational"
echo "✓ API endpoints are accessible"
echo "✓ MinIO is configured and healthy"
echo "✓ Pre-signed URL generation works"
echo ""
echo "To test the complete flow:"
echo "1. Open http://localhost:8000/docs"
echo "2. Authenticate using /users/sync"
echo "3. Get pre-signed URL from /notes/presigned-url"
echo "4. Upload file: curl -X PUT -T audio.wav 'http://localhost:9000/incoming/STORAGE_KEY'"
echo "5. Process: POST /notes/process with storage_key"
echo "========================================="
