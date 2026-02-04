#!/bin/bash

# Comprehensive Endpoint Testing for MinIO Privacy-First Architecture
# Tests both legacy file upload and new pre-signed URL flow

set -e

BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper functions
test_start() {
    ((TESTS_TOTAL++))
    echo -e "\n${BLUE}[TEST $TESTS_TOTAL]${NC} $1"
}

test_pass() {
    ((TESTS_PASSED++))
    echo -e "${GREEN}✓ PASSED${NC}: $1"
}

test_fail() {
    ((TESTS_FAILED++))
    echo -e "${RED}✗ FAILED${NC}: $1"
}

# Create test audio file
create_test_audio() {
    if [ ! -f "/tmp/test_audio.wav" ]; then
        echo "Creating test audio file..."
        ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" /tmp/test_audio.wav -y > /dev/null 2>&1
    fi
}

echo "========================================="
echo "MinIO Privacy-First Architecture Tests"
echo "========================================="

create_test_audio

# Test 1: API Health Check
test_start "API Health Check"
HEALTH=$(curl -s $BASE_URL/../health)
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    test_pass "API is healthy"
else
    test_fail "API health check failed: $HEALTH"
    exit 1
fi

# Test 2: User Authentication
test_start "User Authentication"
UNIQUE_EMAIL="test_$(date +%s)@voicenote.ai"
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test User\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"test_token_123\",
    \"device_id\": \"test_device_001\",
    \"device_model\": \"curl-tester\",
    \"primary_role\": \"DEVELOPER\",
    \"timezone\": \"UTC\"
  }")

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token')
if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    test_pass "Authentication successful"
else
    test_fail "Failed to get access token"
    exit 1
fi

# Elevate to admin for signature bypass
docker exec voicenote_db psql -U postgres -d voicenote -c "UPDATE users SET is_admin = true WHERE email = '$UNIQUE_EMAIL';" > /dev/null 2>&1

# Test 3: Get Pre-signed URL
test_start "Generate Pre-signed URL"
PRESIGNED_RESPONSE=$(curl -s -X GET "$BASE_URL/notes/presigned-url" \
  -H "Authorization: Bearer $TOKEN")

UPLOAD_URL=$(echo "$PRESIGNED_RESPONSE" | jq -r '.upload_url')
STORAGE_KEY=$(echo "$PRESIGNED_RESPONSE" | jq -r '.storage_key')
NOTE_ID=$(echo "$PRESIGNED_RESPONSE" | jq -r '.note_id')

if [ -n "$UPLOAD_URL" ] && [ "$UPLOAD_URL" != "null" ]; then
    test_pass "Pre-signed URL generated: $STORAGE_KEY"
else
    test_fail "Failed to generate pre-signed URL"
fi

# Test 4: Direct MinIO Upload (using localhost)
test_start "Direct Upload to MinIO"
# Replace internal docker address with localhost
LOCALHOST_URL=$(echo "$UPLOAD_URL" | sed 's/minio:9000/localhost:9000/')
UPLOAD_STATUS=$(curl -s -X PUT -T /tmp/test_audio.wav "$LOCALHOST_URL" -o /dev/null -w "%{http_code}")

if [ "$UPLOAD_STATUS" -eq "200" ]; then
    test_pass "File uploaded to MinIO (HTTP $UPLOAD_STATUS)"
else
    test_fail "MinIO upload failed (HTTP $UPLOAD_STATUS)"
fi

# Test 5: Trigger Processing with Storage Key
test_start "Process Note from MinIO Storage Key"
PROCESS_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "storage_key=$STORAGE_KEY" \
  -F "note_id_override=$NOTE_ID" \
  -F "stt_model=nova")

PROCESS_STATUS=$(echo "$PROCESS_RESPONSE" | jq -r '.status')
if [ "$PROCESS_STATUS" == "ACCEPTED" ]; then
    test_pass "Processing queued successfully"
else
    test_fail "Failed to queue processing"
fi

# Test 6: Poll for Completion
test_start "Wait for AI Processing"
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN" | jq -r '.status')
    
    if [ "$STATUS" == "DONE" ]; then
        test_pass "Processing completed successfully"
        break
    elif [ "$STATUS" == "FAILED" ]; then
        test_fail "Processing failed"
        docker logs voicenote_celery_worker --tail 30
        break
    fi
    
    echo -e "${YELLOW}  Status: $STATUS ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
    ((RETRY_COUNT++))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    test_fail "Processing timeout"
fi

# Test 7: Verify Data Extraction
test_start "Verify Extracted Data"
NOTE_DATA=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN")
TITLE=$(echo "$NOTE_DATA" | jq -r '.title')
TASKS=$(echo "$NOTE_DATA" | jq -r '.tasks | length')

if [ -n "$TITLE" ] && [ "$TITLE" != "null" ]; then
    test_pass "Note title extracted: $TITLE"
else
    test_fail "No title extracted"
fi

# Test 8: Verify MinIO Cleanup
test_start "Verify Privacy-First Cleanup"
MC_CHECK=$(docker exec voicenote_mc /usr/bin/mc ls myminio/incoming/$STORAGE_KEY 2>&1 || true)
if echo "$MC_CHECK" | grep -q "Object does not exist"; then
    test_pass "Transit file deleted from MinIO ✅"
else
    test_fail "Transit file still exists in MinIO"
    echo "$MC_CHECK"
fi

# Test 9: Legacy File Upload (Backward Compatibility)
test_start "Legacy Direct File Upload"
LEGACY_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_audio.wav" \
  -F "stt_model=nova")

LEGACY_NOTE_ID=$(echo "$LEGACY_RESPONSE" | jq -r '.note_id')
if [ -n "$LEGACY_NOTE_ID" ] && [ "$LEGACY_NOTE_ID" != "null" ]; then
    test_pass "Legacy upload still works (backward compatible)"
else
    test_fail "Legacy upload broken"
fi

# Test 10: Swagger UI Accessibility
test_start "Swagger UI Accessibility"
SWAGGER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [ "$SWAGGER_STATUS" -eq "200" ]; then
    test_pass "Swagger UI accessible"
else
    test_fail "Swagger UI not accessible"
fi

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "Total Tests: ${BLUE}$TESTS_TOTAL${NC}"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo "========================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
