#!/bin/bash

# ============================================================================
# COMPREHENSIVE CURL ENDPOINT TESTING SUITE
# ============================================================================
# Tests all VoiceNote API endpoints using curl
# Generates detailed report with pass/fail results

set -e

BASE_URL="http://localhost:8000"
REPORT_FILE="/tmp/curl_test_report.txt"
PASSED=0
FAILED=0
TOTAL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Initialize report
cat > "$REPORT_FILE" << 'EOF'
================================================================================
                  COMPREHENSIVE CURL ENDPOINT TEST REPORT
================================================================================
Date: $(date)
Base URL: http://localhost:8000

================================================================================
EOF

log_test() {
    local name=$1
    local method=$2
    local endpoint=$3
    local expected_code=$4
    
    echo -e "${BLUE}Testing:${NC} [$method] $endpoint"
}

test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local expected_code=$4
    local data=$5
    local headers=$6
    
    ((TOTAL++))
    
    # Make the request
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" $headers)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            $headers \
            -d "$data")
    fi
    
    # Extract status code
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    # Check if it matches expected code
    if [[ "$http_code" =~ $expected_code ]]; then
        echo -e "${GREEN}✅ PASS${NC} [$http_code] $name"
        ((PASSED++))
        echo "✅ [$http_code] $name" >> "$REPORT_FILE"
    else
        echo -e "${RED}❌ FAIL${NC} [Expected: $expected_code, Got: $http_code] $name"
        ((FAILED++))
        echo "❌ [Expected: $expected_code, Got: $http_code] $name" >> "$REPORT_FILE"
        echo "   Response: ${body:0:200}" >> "$REPORT_FILE"
    fi
}

# ============================================================================
# STEP 1: USER AUTHENTICATION & REGISTRATION
# ============================================================================

echo -e "\n${BLUE}=== STEP 1: USER AUTHENTICATION ===${NC}\n"

# Create a new user
USER_EMAIL="test_$(date +%s)@test.com"
DEVICE_ID="device_$(date +%s)"

USER_PAYLOAD=$(cat <<EOF
{
  "email": "$USER_EMAIL",
  "name": "cURL Test User",
  "device_id": "$DEVICE_ID",
  "device_model": "iPhone12",
  "token": "biometric_token_123",
  "timezone": "UTC"
}
EOF
)

test_endpoint "User Sync - New User" "POST" "/api/v1/users/sync" "200" "$USER_PAYLOAD"

# Extract access token from response
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/sync" \
  -H "Content-Type: application/json" \
  -d "$USER_PAYLOAD")

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Could not extract token${NC}"
    TOKEN="test_token"
fi

echo -e "Token obtained: ${TOKEN:0:20}...\n"

AUTH_HEADER="-H \"Authorization: Bearer $TOKEN\""

# ============================================================================
# STEP 2: USER ENDPOINTS
# ============================================================================

echo -e "\n${BLUE}=== STEP 2: USER ENDPOINTS ===${NC}\n"

test_endpoint "Get Current User" "GET" "/api/v1/users/me" "200" "" "$AUTH_HEADER"

UPDATE_USER_PAYLOAD='{"name":"Updated Name","timezone":"PST"}'
test_endpoint "Update User" "PATCH" "/api/v1/users/me" "200" "$UPDATE_USER_PAYLOAD" "$AUTH_HEADER"

test_endpoint "Search Users" "GET" "/api/v1/users/search?q=test" "200" "" "$AUTH_HEADER"

test_endpoint "Logout User" "POST" "/api/v1/users/logout" "200" "" "$AUTH_HEADER"

# ============================================================================
# STEP 3: NOTE ENDPOINTS
# ============================================================================

echo -e "\n${BLUE}=== STEP 3: NOTE ENDPOINTS ===${NC}\n"

test_endpoint "Get Presigned URL" "GET" "/api/v1/notes/presigned-url" "200" "" "$AUTH_HEADER"

CREATE_NOTE_PAYLOAD='{"title":"Test Note","content":"Test Content","language":"en","duration_ms":1000}'
test_endpoint "Create Note" "POST" "/api/v1/notes/create" "201" "$CREATE_NOTE_PAYLOAD" "$AUTH_HEADER"

test_endpoint "List Notes" "GET" "/api/v1/notes" "200" "" "$AUTH_HEADER"

test_endpoint "Get Dashboard" "GET" "/api/v1/notes/dashboard" "200" "" "$AUTH_HEADER"

# Get a note ID to use in further tests
NOTE_ID=$(curl -s -X GET "$BASE_URL/api/v1/notes" -H "Authorization: Bearer $TOKEN" | \
    grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ ! -z "$NOTE_ID" ]; then
    test_endpoint "Get Note by ID" "GET" "/api/v1/notes/$NOTE_ID" "200" "" "$AUTH_HEADER"
    
    UPDATE_NOTE_PAYLOAD='{"title":"Updated Note Title","content":"Updated Content"}'
    test_endpoint "Update Note" "PATCH" "/api/v1/notes/$NOTE_ID" "200" "$UPDATE_NOTE_PAYLOAD" "$AUTH_HEADER"
    
    test_endpoint "Get WhatsApp Draft" "GET" "/api/v1/notes/$NOTE_ID/whatsapp" "200" "" "$AUTH_HEADER"
    
    test_endpoint "Semantic Analysis" "POST" "/api/v1/notes/$NOTE_ID/semantic-analysis" "202|200" "" "$AUTH_HEADER"
fi

# ============================================================================
# STEP 4: TASK ENDPOINTS
# ============================================================================

echo -e "\n${BLUE}=== STEP 4: TASK ENDPOINTS ===${NC}\n"

CREATE_TASK_PAYLOAD='{"description":"Test Task","priority":"MEDIUM","deadline":null,"assigned_entities":[],"image_uris":[],"document_uris":[],"external_links":[],"communication_type":"INTERNAL","is_action_approved":false}'
test_endpoint "Create Task" "POST" "/api/v1/tasks" "201" "$CREATE_TASK_PAYLOAD" "$AUTH_HEADER"

test_endpoint "List Tasks" "GET" "/api/v1/tasks" "200" "" "$AUTH_HEADER"

test_endpoint "Get Tasks Due Today" "GET" "/api/v1/tasks/due-today" "200" "" "$AUTH_HEADER"

test_endpoint "Get Overdue Tasks" "GET" "/api/v1/tasks/overdue" "200" "" "$AUTH_HEADER"

test_endpoint "Get Tasks Assigned to Me" "GET" "/api/v1/tasks/assigned-to-me" "200" "" "$AUTH_HEADER"

test_endpoint "Search Tasks" "GET" "/api/v1/tasks/search?q=test" "200" "" "$AUTH_HEADER"

test_endpoint "Get Task Statistics" "GET" "/api/v1/tasks/stats" "200" "" "$AUTH_HEADER"

# Get a task ID for further tests
TASK_ID=$(curl -s -X GET "$BASE_URL/api/v1/tasks" -H "Authorization: Bearer $TOKEN" | \
    grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ ! -z "$TASK_ID" ]; then
    test_endpoint "Get Task by ID" "GET" "/api/v1/tasks/$TASK_ID" "200" "" "$AUTH_HEADER"
    
    UPDATE_TASK_PAYLOAD='{"description":"Updated Task","priority":"HIGH"}'
    test_endpoint "Update Task" "PATCH" "/api/v1/tasks/$TASK_ID" "200" "$UPDATE_TASK_PAYLOAD" "$AUTH_HEADER"
    
    test_endpoint "Duplicate Task" "POST" "/api/v1/tasks/$TASK_ID/duplicate" "201" "" "$AUTH_HEADER"
fi

# ============================================================================
# STEP 5: AI ENDPOINTS
# ============================================================================

echo -e "\n${BLUE}=== STEP 5: AI ENDPOINTS ===${NC}\n"

AI_SEARCH_PAYLOAD='{"query":"test search"}'
test_endpoint "AI Search" "POST" "/api/v1/ai/search" "200" "$AI_SEARCH_PAYLOAD" "$AUTH_HEADER"

test_endpoint "AI Statistics" "GET" "/api/v1/ai/stats" "200" "" "$AUTH_HEADER"

# ============================================================================
# STEP 6: ADMIN ENDPOINTS
# ============================================================================

echo -e "\n${BLUE}=== STEP 6: ADMIN ENDPOINTS ===${NC}\n"

test_endpoint "Admin List Users" "GET" "/api/v1/admin/users" "200|403" "" "$AUTH_HEADER"

test_endpoint "Admin User Statistics" "GET" "/api/v1/admin/users/stats" "200|403" "" "$AUTH_HEADER"

test_endpoint "Admin List Notes" "GET" "/api/v1/admin/notes" "200|403" "" "$AUTH_HEADER"

test_endpoint "Admin List Admins" "GET" "/api/v1/admin/admins" "200|403" "" "$AUTH_HEADER"

test_endpoint "Admin Status" "GET" "/api/v1/admin/status" "200|403" "" "$AUTH_HEADER"

test_endpoint "Admin Audit Logs" "GET" "/api/v1/admin/audit-logs" "200|403" "" "$AUTH_HEADER"

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

echo -e "\n${BLUE}=== STEP 7: ERROR HANDLING ===${NC}\n"

test_endpoint "Unauthorized Request" "GET" "/api/v1/notes" "401" ""

test_endpoint "Invalid Token" "GET" "/api/v1/notes" "401" "" "-H \"Authorization: Bearer invalid_token\""

FAKE_ID=$(uuidgen 2>/dev/null || echo "550e8400-e29b-41d4-a716-446655440000")
test_endpoint "Nonexistent Note" "GET" "/api/v1/notes/$FAKE_ID" "404" "" "$AUTH_HEADER"

test_endpoint "Nonexistent Task" "GET" "/api/v1/tasks/$FAKE_ID" "404" "" "$AUTH_HEADER"

INVALID_TASK_PAYLOAD='{"description":"","priority":"INVALID"}'
test_endpoint "Invalid Task Data" "POST" "/api/v1/tasks" "400" "$INVALID_TASK_PAYLOAD" "$AUTH_HEADER"

# ============================================================================
# SUMMARY REPORT
# ============================================================================

echo -e "\n${BLUE}=== SUMMARY ===${NC}\n"
echo -e "Total Tests: ${BLUE}$TOTAL${NC}"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"

PASS_RATE=$((PASSED * 100 / TOTAL))
echo -e "Pass Rate: ${YELLOW}${PASS_RATE}%${NC}\n"

# Add to report
cat >> "$REPORT_FILE" << EOF

================================================================================
                              SUMMARY
================================================================================
Total Tests: $TOTAL
Passed: $PASSED
Failed: $FAILED
Pass Rate: ${PASS_RATE}%

Test Date: $(date)
API Base URL: $BASE_URL
Test User Email: $USER_EMAIL

================================================================================
EOF

echo "Report saved to: $REPORT_FILE"
echo -e "\n${YELLOW}Full report:${NC}"
cat "$REPORT_FILE"

# Exit with failure if any tests failed
if [ $FAILED -gt 0 ]; then
    exit 1
fi

exit 0
