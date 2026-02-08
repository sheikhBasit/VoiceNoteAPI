#!/bin/bash

###############################################################################
#                   COMPLETE CURL TEST SUITE - ALL ENDPOINTS
#                     Tests all VoiceNote API endpoints
###############################################################################

set -e

# Configuration
BASE_URL="http://localhost:8000"
REPORT_FILE="/tmp/curl_all_endpoints_report.txt"
PASSED=0
FAILED=0
TOTAL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
CYAN='\033[0;36m'
NC='\033[0m'

# Initialize report
{
    echo "================================================================================"
    echo "                    COMPREHENSIVE CURL ENDPOINT TEST REPORT"
    echo "================================================================================"
    echo "Date: $(date)"
    echo "Base URL: $BASE_URL"
    echo "================================================================================"
    echo ""
} > "$REPORT_FILE"

# Test counter
test_count() {
    ((TOTAL++))
}

# Pass/Fail logging
log_result() {
    local name=$1
    local expected=$2
    local actual=$3
    local response=$4
    
    if [[ "$expected" =~ "$actual" ]]; then
        ((PASSED++))
        echo -e "${GREEN}✅ PASS${NC} [$actual] $name"
        {
            echo "✅ PASS [$actual] $name"
        } >> "$REPORT_FILE"
    else
        ((FAILED++))
        echo -e "${RED}❌ FAIL${NC} [Expected: $expected, Got: $actual] $name"
        {
            echo "❌ FAIL [Expected: $expected, Got: $actual] $name"
            echo "   Response: ${response:0:200}"
        } >> "$REPORT_FILE"
    fi
}

###############################################################################
# STEP 1: USER AUTHENTICATION & REGISTRATION
###############################################################################

echo -e "\n${BLUE}[STEP 1] USER AUTHENTICATION & REGISTRATION${NC}\n"

# Create test user
USER_EMAIL="test_$(date +%s)_$RANDOM@test.com"
DEVICE_ID="device_$(date +%s)_$RANDOM"

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

test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/users/sync" \
  -H "Content-Type: application/json" \
  -d "$USER_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

# Extract token
TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4 | head -1)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Could not extract token from response${NC}"
    echo "Response: $BODY"
    exit 1
fi

log_result "User Sync - New User Registration" "200" "$HTTP_CODE" "$BODY"
echo -e "   ${CYAN}Token obtained: ${TOKEN:0:30}...${NC}\n"

###############################################################################
# STEP 2: USER ENDPOINTS
###############################################################################

echo -e "\n${BLUE}[STEP 2] USER ENDPOINTS${NC}\n"

# 2.1 Get current user
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Get Current User" "200" "$HTTP_CODE" "$BODY"

# 2.2 Search users
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/users/search?q=test" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Search Users" "200" "$HTTP_CODE" "$BODY"

# 2.3 Logout user
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/users/logout" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Logout User" "200" "$HTTP_CODE" "$BODY"

###############################################################################
# STEP 3: NOTE ENDPOINTS
###############################################################################

echo -e "\n${BLUE}[STEP 3] NOTE ENDPOINTS${NC}\n"

# 3.1 Create note
test_count
CREATE_NOTE_PAYLOAD=$(cat <<EOF
{
  "title": "Test Note",
  "content": "Test Content for Note",
  "language": "en",
  "duration_ms": 1000
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/notes/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CREATE_NOTE_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

# Extract note ID
NOTE_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

log_result "Create Note" "200|201" "$HTTP_CODE" "$BODY"
echo -e "   ${CYAN}Note ID: $NOTE_ID${NC}"

# 3.2 List notes
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/notes" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "List Notes" "200" "$HTTP_CODE" "$BODY"

# 3.3 Get dashboard
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/notes/dashboard" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Get Dashboard" "200" "$HTTP_CODE" "$BODY"

# 3.4 Get note by ID
if [ ! -z "$NOTE_ID" ]; then
    test_count
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/notes/$NOTE_ID" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Get Note by ID" "200" "$HTTP_CODE" "$BODY"
    
    # 3.5 Update note
    test_count
    UPDATE_NOTE_PAYLOAD=$(cat <<EOF
{
  "title": "Updated Note Title",
  "content": "Updated Content"
}
EOF
)
    RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/notes/$NOTE_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_NOTE_PAYLOAD")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Update Note" "200" "$HTTP_CODE" "$BODY"
    
    # 3.6 Get WhatsApp draft
    test_count
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/notes/$NOTE_ID/whatsapp" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Get WhatsApp Draft" "200" "$HTTP_CODE" "$BODY"
    
    # 3.7 Semantic analysis
    test_count
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/notes/$NOTE_ID/semantic-analysis" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Semantic Analysis" "200|202" "$HTTP_CODE" "$BODY"
fi

###############################################################################
# STEP 4: TASK ENDPOINTS
###############################################################################

echo -e "\n${BLUE}[STEP 4] TASK ENDPOINTS${NC}\n"

# 4.1 Create task (with CORRECT enum value)
test_count
CREATE_TASK_PAYLOAD=$(cat <<EOF
{
  "description": "Test Task Description",
  "priority": "MEDIUM",
  "deadline": null,
  "assigned_entities": [],
  "image_uris": [],
  "document_uris": [],
  "external_links": [],
  "communication_type": "WHATSAPP",
  "is_action_approved": false
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CREATE_TASK_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

# Extract task ID
TASK_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

log_result "Create Task" "200|201" "$HTTP_CODE" "$BODY"
echo -e "   ${CYAN}Task ID: $TASK_ID${NC}"

# 4.2 List tasks
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "List Tasks" "200" "$HTTP_CODE" "$BODY"

# 4.3 Get tasks due today
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks/due-today" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Get Tasks Due Today" "200" "$HTTP_CODE" "$BODY"

# 4.4 Get overdue tasks
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks/overdue" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Get Overdue Tasks" "200" "$HTTP_CODE" "$BODY"

# 4.5 Get tasks assigned to me
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks/assigned-to-me" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Get Tasks Assigned to Me" "200" "$HTTP_CODE" "$BODY"

# 4.6 Search tasks (with CORRECT parameter)
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks/search?query_text=test" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Search Tasks" "200" "$HTTP_CODE" "$BODY"

# 4.7 Get task statistics
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks/stats" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Get Task Statistics" "200" "$HTTP_CODE" "$BODY"

# 4.8 Get task by ID
if [ ! -z "$TASK_ID" ]; then
    test_count
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks/$TASK_ID" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Get Task by ID" "200" "$HTTP_CODE" "$BODY"
    
    # 4.9 Update task
    test_count
    UPDATE_TASK_PAYLOAD=$(cat <<EOF
{
  "description": "Updated Task Description",
  "priority": "HIGH"
}
EOF
)
    RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/tasks/$TASK_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_TASK_PAYLOAD")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Update Task" "200" "$HTTP_CODE" "$BODY"
    
    # 4.10 Duplicate task
    test_count
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/duplicate" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Duplicate Task" "200|201" "$HTTP_CODE" "$BODY"
    
    # 4.11 Delete task
    test_count
    RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/v1/tasks/$TASK_ID" \
      -H "Authorization: Bearer $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    log_result "Delete Task" "200" "$HTTP_CODE" "$BODY"
fi

###############################################################################
# STEP 5: AI ENDPOINTS
###############################################################################

echo -e "\n${BLUE}[STEP 5] AI ENDPOINTS${NC}\n"

# 5.1 AI search (with CORRECT method - POST with body)
test_count
AI_SEARCH_PAYLOAD=$(cat <<EOF
{
  "query": "test search query"
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/ai/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$AI_SEARCH_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "AI Search" "200" "$HTTP_CODE" "$BODY"

# 5.2 AI statistics
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/ai/stats" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "AI Statistics" "200" "$HTTP_CODE" "$BODY"

###############################################################################
# STEP 6: ADMIN ENDPOINTS
###############################################################################

echo -e "\n${BLUE}[STEP 6] ADMIN ENDPOINTS${NC}\n"

# 6.1 Admin list users (will return 403 if not admin - that's expected)
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/admin/users" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Admin List Users" "200|403" "$HTTP_CODE" "$BODY"

# 6.2 Admin user statistics
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/admin/users/stats" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Admin User Statistics" "200|403" "$HTTP_CODE" "$BODY"

# 6.3 Admin list notes
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/admin/notes" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Admin List Notes" "200|403" "$HTTP_CODE" "$BODY"

# 6.4 Admin list admins
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/admin/admins" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Admin List Admins" "200|403" "$HTTP_CODE" "$BODY"

# 6.5 Admin status
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/admin/status" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Admin Status" "200|403" "$HTTP_CODE" "$BODY"

# 6.6 Admin audit logs
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/admin/audit-logs" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Admin Audit Logs" "200|403" "$HTTP_CODE" "$BODY"

###############################################################################
# STEP 7: ERROR HANDLING TESTS
###############################################################################

echo -e "\n${BLUE}[STEP 7] ERROR HANDLING TESTS${NC}\n"

# 7.1 No authorization
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/notes")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "No Authorization Header" "401" "$HTTP_CODE" "$BODY"

# 7.2 Invalid token
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/notes" \
  -H "Authorization: Bearer invalid_token_xyz")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Invalid Authorization Token" "401" "$HTTP_CODE" "$BODY"

# 7.3 Nonexistent note
test_count
FAKE_UUID="550e8400-e29b-41d4-a716-446655440000"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/notes/$FAKE_UUID" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Nonexistent Note (404)" "404" "$HTTP_CODE" "$BODY"

# 7.4 Nonexistent task
test_count
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/tasks/$FAKE_UUID" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Nonexistent Task (404)" "404" "$HTTP_CODE" "$BODY"

# 7.5 Invalid task data
test_count
INVALID_TASK=$(cat <<EOF
{
  "description": "",
  "priority": "INVALID_PRIORITY"
}
EOF
)
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$INVALID_TASK")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
log_result "Invalid Task Data (422)" "400|422" "$HTTP_CODE" "$BODY"

###############################################################################
# SUMMARY
###############################################################################

echo -e "\n${BLUE}================================================================================${NC}"
echo -e "${BLUE}                              TEST SUMMARY${NC}"
echo -e "${BLUE}================================================================================${NC}\n"

echo -e "Total Tests:  ${BLUE}$TOTAL${NC}"
echo -e "Passed:       ${GREEN}$PASSED${NC}"
echo -e "Failed:       ${RED}$FAILED${NC}"

PASS_RATE=$((PASSED * 100 / TOTAL))
echo -e "Pass Rate:    ${YELLOW}${PASS_RATE}%${NC}\n"

# Add summary to report
{
    echo ""
    echo "================================================================================"
    echo "                              TEST SUMMARY"
    echo "================================================================================"
    echo ""
    echo "Total Tests:  $TOTAL"
    echo "Passed:       $PASSED"
    echo "Failed:       $FAILED"
    echo "Pass Rate:    ${PASS_RATE}%"
    echo ""
    echo "================================================================================"
    echo "Test Execution Date: $(date)"
    echo "================================================================================"
} >> "$REPORT_FILE"

echo -e "Report saved to: ${CYAN}$REPORT_FILE${NC}\n"

# Display report
echo -e "${YELLOW}Full Report:${NC}"
cat "$REPORT_FILE"

# Exit with appropriate code
if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ ALL TESTS PASSED!${NC}\n"
    exit 0
else
    echo -e "\n${RED}❌ SOME TESTS FAILED${NC}\n"
    exit 1
fi
