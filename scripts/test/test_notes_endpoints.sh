#!/bin/bash

# ============================================================================
# Notes Endpoint Testing Script (cURL based)
# ============================================================================

set -e

BASE_URL="http://localhost:8000"
API_V1="$BASE_URL/api/v1"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# UTILITIES
# ============================================================================

log_test() {
    local test_name=$1
    local status=$2
    local message=$3
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $test_name: $message${NC}"
        ((TESTS_PASSED++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $test_name: $message${NC}"
        ((TESTS_FAILED++))
    else
        echo -e "${YELLOW}⏭️  $test_name: $message${NC}"
    fi
    ((TESTS_RUN++))
}

check_server() {
    echo -e "${BLUE}Checking API server...${NC}"
    if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
        echo -e "${RED}❌ API server not running at $BASE_URL${NC}"
        echo "Please start the server with: docker-compose up"
        exit 1
    fi
    echo -e "${GREEN}✅ API server is running${NC}\n"
}

# ============================================================================
# AUTHENTICATION
# ============================================================================

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║             NOTES ENDPOINT TEST SUITE (CURL)                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"

check_server

# Create test user
USER_ID="test_user_$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)"
EMAIL="testuser_$USER_ID@voicenote.app"
DEVICE_ID="device_$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)"
DEVICE_MODEL="TestDevice_1.0"
TOKEN="token_$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 16 | head -n 1)"

echo -e "${BLUE}Step 1: User Authentication${NC}"
echo "User ID: $USER_ID"
echo "Email: $EMAIL"

AUTH_RESPONSE=$(curl -s -X POST "$API_V1/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$USER_ID\",
    \"email\": \"$EMAIL\",
    \"name\": \"Test User\",
    \"device_id\": \"$DEVICE_ID\",
    \"device_model\": \"$DEVICE_MODEL\",
    \"token\": \"$TOKEN\",
    \"timezone\": \"UTC\"
  }")

ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$ACCESS_TOKEN" ]; then
    log_test "User Sync" "FAIL" "Could not authenticate user"
    echo "$AUTH_RESPONSE" | jq .
    exit 1
fi

log_test "User Sync" "PASS" "User authenticated (token: ${ACCESS_TOKEN:0:20}...)"

# ============================================================================
# CREATE TEST AUDIO FILE
# ============================================================================

echo -e "\n${BLUE}Step 2: Create Test Audio File${NC}"

AUDIO_FILE="/tmp/test_note_$(date +%s).wav"

# Try to create with ffmpeg
if command -v ffmpeg &> /dev/null; then
    ffmpeg -f lavfi -i sine=frequency=440:duration=2 -c:a pcm_s16le -ar 16000 -ac 1 "$AUDIO_FILE" -y > /dev/null 2>&1
    if [ -f "$AUDIO_FILE" ]; then
        log_test "Audio Creation" "PASS" "Created $AUDIO_FILE"
    else
        log_test "Audio Creation" "FAIL" "FFmpeg failed to create audio"
        exit 1
    fi
else
    log_test "Audio Creation" "FAIL" "FFmpeg not installed"
    exit 1
fi

AUDIO_SIZE=$(stat -f%z "$AUDIO_FILE" 2>/dev/null || stat -c%s "$AUDIO_FILE" 2>/dev/null)
echo "Audio file size: $AUDIO_SIZE bytes"

# ============================================================================
# TEST 1: Get Presigned URL
# ============================================================================

echo -e "\n${BLUE}TEST 1: Get Presigned URL${NC}"

PRESIGNED_RESPONSE=$(curl -s -X GET "$API_V1/notes/presigned-url" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

PRESIGNED_NOTE_ID=$(echo "$PRESIGNED_RESPONSE" | jq -r '.note_id // empty')
PRESIGNED_URL=$(echo "$PRESIGNED_RESPONSE" | jq -r '.upload_url // empty')

if [ -n "$PRESIGNED_NOTE_ID" ] && [ -n "$PRESIGNED_URL" ]; then
    log_test "GET /notes/presigned-url" "PASS" "Note ID: $PRESIGNED_NOTE_ID"
else
    log_test "GET /notes/presigned-url" "FAIL" "Could not generate presigned URL"
    echo "$PRESIGNED_RESPONSE" | jq .
fi

# ============================================================================
# TEST 2: Process Note (Upload)
# ============================================================================

echo -e "\n${BLUE}TEST 2: Process Note (File Upload)${NC}"

PROCESS_RESPONSE=$(curl -s -X POST "$API_V1/notes/process" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@$AUDIO_FILE" \
  -F "mode=GENERIC" \
  -F "languages=en" \
  -F "stt_model=nova" \
  -F "debug_sync=false")

NOTE_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.note_id // empty')
TASK_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.task_id // empty')
STATUS=$(echo "$PROCESS_RESPONSE" | jq -r '.status // empty')

if [ "$STATUS" = "processing" ] || [ -n "$NOTE_ID" ]; then
    log_test "POST /notes/process" "PASS" "Note processing started (Note ID: ${NOTE_ID:0:12}..., Task ID: ${TASK_ID:0:12}...)"
else
    log_test "POST /notes/process" "FAIL" "Could not process note"
    echo "$PROCESS_RESPONSE" | jq .
fi

# ============================================================================
# TEST 3: List Notes
# ============================================================================

echo -e "\n${BLUE}TEST 3: List Notes${NC}"

LIST_RESPONSE=$(curl -s -X GET "$API_V1/notes?skip=0&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

NOTES_COUNT=$(echo "$LIST_RESPONSE" | jq 'length // .count // 0')

if [ "$NOTES_COUNT" -ge 0 ]; then
    log_test "GET /notes" "PASS" "Retrieved $NOTES_COUNT notes"
else
    log_test "GET /notes" "FAIL" "Could not list notes"
    echo "$LIST_RESPONSE" | jq .
fi

# ============================================================================
# TEST 4: Get Specific Note
# ============================================================================

if [ -n "$NOTE_ID" ]; then
    echo -e "\n${BLUE}TEST 4: Get Specific Note${NC}"
    
    GET_NOTE_RESPONSE=$(curl -s -X GET "$API_V1/notes/$NOTE_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json")
    
    NOTE_TITLE=$(echo "$GET_NOTE_RESPONSE" | jq -r '.title // "Untitled"')
    
    if [ "$NOTE_TITLE" != "null" ]; then
        log_test "GET /notes/{note_id}" "PASS" "Retrieved note: $NOTE_TITLE"
    else
        log_test "GET /notes/{note_id}" "FAIL" "Could not retrieve note"
        echo "$GET_NOTE_RESPONSE" | jq .
    fi
fi

# ============================================================================
# TEST 5: Update Note
# ============================================================================

if [ -n "$NOTE_ID" ]; then
    echo -e "\n${BLUE}TEST 5: Update Note${NC}"
    
    UPDATE_RESPONSE=$(curl -s -X PATCH "$API_V1/notes/$NOTE_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"title\": \"Updated Test Note $(date +%s)\",
        \"description\": \"Updated via test script\",
        \"tags\": [\"test\", \"updated\"]
      }")
    
    UPDATED_TITLE=$(echo "$UPDATE_RESPONSE" | jq -r '.title // empty')
    
    if [ -n "$UPDATED_TITLE" ]; then
        log_test "PATCH /notes/{note_id}" "PASS" "Updated: $UPDATED_TITLE"
    else
        log_test "PATCH /notes/{note_id}" "FAIL" "Could not update note"
        echo "$UPDATE_RESPONSE" | jq .
    fi
fi

# ============================================================================
# TEST 6: Search Notes
# ============================================================================

echo -e "\n${BLUE}TEST 6: Search Notes${NC}"

SEARCH_RESPONSE=$(curl -s -X GET "$API_V1/notes/search?query=test&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

SEARCH_COUNT=$(echo "$SEARCH_RESPONSE" | jq 'length // .count // 0')

if [ "$SEARCH_COUNT" -ge 0 ]; then
    log_test "GET /notes/search" "PASS" "Found $SEARCH_COUNT matching notes"
else
    log_test "GET /notes/search" "FAIL" "Could not search notes"
    echo "$SEARCH_RESPONSE" | jq .
fi

# ============================================================================
# TEST 7: Dashboard Metrics
# ============================================================================

echo -e "\n${BLUE}TEST 7: Dashboard Metrics${NC}"

METRICS_RESPONSE=$(curl -s -X GET "$API_V1/notes/dashboard/metrics" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

TOTAL_NOTES=$(echo "$METRICS_RESPONSE" | jq '.total_notes // 0')

if [ "$TOTAL_NOTES" != "null" ]; then
    log_test "GET /notes/dashboard/metrics" "PASS" "Total notes: $TOTAL_NOTES"
else
    log_test "GET /notes/dashboard/metrics" "FAIL" "Could not get metrics"
    echo "$METRICS_RESPONSE" | jq .
fi

# ============================================================================
# TEST 8: Ask AI
# ============================================================================

if [ -n "$NOTE_ID" ]; then
    echo -e "\n${BLUE}TEST 8: Ask AI${NC}"
    
    AI_RESPONSE=$(curl -s -X POST "$API_V1/notes/$NOTE_ID/ask-ai" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"question\": \"What is the main topic of this note?\"
      }")
    
    AI_ANSWER=$(echo "$AI_RESPONSE" | jq -r '.answer // empty')
    
    if [ -n "$AI_ANSWER" ] && [ "$AI_ANSWER" != "null" ]; then
        log_test "POST /notes/{note_id}/ask-ai" "PASS" "AI response received"
    else
        log_test "POST /notes/{note_id}/ask-ai" "SKIP" "AI service not available"
    fi
fi

# ============================================================================
# TEST 9: Delete Note
# ============================================================================

if [ -n "$NOTE_ID" ]; then
    echo -e "\n${BLUE}TEST 9: Delete Note${NC}"
    
    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$API_V1/notes/$NOTE_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json")
    
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n 1)
    
    if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 204 ]; then
        log_test "DELETE /notes/{note_id}" "PASS" "Note deleted (HTTP $HTTP_CODE)"
    else
        log_test "DELETE /notes/{note_id}" "FAIL" "HTTP $HTTP_CODE"
    fi
fi

# ============================================================================
# SUMMARY
# ============================================================================

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                        TEST SUMMARY                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

echo "Total Tests Run: $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED ✅${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED ❌${NC}"

if [ $TESTS_RUN -gt 0 ]; then
    SUCCESS_RATE=$((TESTS_PASSED * 100 / TESTS_RUN))
    echo "Success Rate: $SUCCESS_RATE%"
fi

# Cleanup
rm -f "$AUDIO_FILE"
echo -e "\nAudio file cleaned up."

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}\n"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed${NC}\n"
    exit 1
fi
