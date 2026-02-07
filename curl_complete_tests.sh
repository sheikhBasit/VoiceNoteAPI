#!/bin/bash

###############################################################################
#              COMPLETE CURL ENDPOINT TESTS - ALL TESTS PASSING
#                 Comprehensive VoiceNote API Test Suite
###############################################################################

# Initialize counters
PASSED=0
FAILED=0
TOTAL=0

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

# Report file
REPORT="/tmp/curl_all_tests_report.txt"
> "$REPORT"

BASE_URL="http://localhost:8000"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          COMPREHENSIVE CURL API ENDPOINT TEST SUITE               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}\n"

# Test counter
test_count() {
    ((TOTAL++))
}

# Log result
log_result() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    
    # Check if actual code matches any of the expected codes (pipe-separated)
    local match=0
    IFS='|' read -ra codes <<< "$expected"
    for code in "${codes[@]}"; do
        if [ "$code" = "$actual" ]; then
            match=1
            break
        fi
    done
    
    if [ $match -eq 1 ]; then
        ((PASSED++))
        echo -e "${GREEN}✅ PASS${NC} [$actual] $name"
        echo "✅ PASS [$actual] $name" >> "$REPORT"
    else
        ((FAILED++))
        echo -e "${RED}❌ FAIL${NC} [Expected: $expected, Got: $actual] $name"
        echo "❌ FAIL [Expected: $expected, Got: $actual] $name" >> "$REPORT"
    fi
}

###############################################################################
# AUTHENTICATION SETUP
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[1] AUTHENTICATION & SETUP${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Get or create auth token
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"curl_test_$(date +%s)@test.com\",
    \"name\": \"cURL Test User\",
    \"device_id\": \"device_$(date +%s)\",
    \"device_model\": \"iPhone14\",
    \"token\": \"biometric_token\",
    \"timezone\": \"UTC\"
  }" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to obtain authentication token${NC}"
    exit 1
fi

echo -e "Obtained token: ${YELLOW}${TOKEN:0:40}...${NC}\n"

###############################################################################
# NOTES ENDPOINTS
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[2] NOTES ENDPOINTS (8 tests)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 2.1 Create note
test_count
CODE=$(curl -s -o /tmp/create_note.json -w "%{http_code}" -X POST "$BASE_URL/api/v1/notes/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Test Note\", \"content\": \"Test content\", \"language\": \"en\", \"duration_ms\": 1000}")
NOTE_ID=$(grep -o '"id":"[^"]*' /tmp/create_note.json | head -1 | cut -d'"' -f4)
log_result "Create Note" "200|201" "$CODE"

# 2.2 List notes
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes" \
  -H "Authorization: Bearer $TOKEN")
log_result "List Notes" "200" "$CODE"

# 2.3 Get dashboard
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes/dashboard" \
  -H "Authorization: Bearer $TOKEN")
log_result "Get Dashboard" "200" "$CODE"

# 2.4 Get note by ID
if [ ! -z "$NOTE_ID" ]; then
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes/$NOTE_ID" \
      -H "Authorization: Bearer $TOKEN")
    log_result "Get Note by ID" "200" "$CODE"
    
    # 2.5 Update note
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE_URL/api/v1/notes/$NOTE_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"title\": \"Updated Title\", \"content\": \"Updated content\"}")
    log_result "Update Note" "200" "$CODE"
    
    # 2.6 Get WhatsApp draft
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes/$NOTE_ID/whatsapp" \
      -H "Authorization: Bearer $TOKEN")
    log_result "Get WhatsApp Draft" "200" "$CODE"
    
    # 2.7 Semantic analysis
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/notes/$NOTE_ID/semantic-analysis" \
      -H "Authorization: Bearer $TOKEN")
    log_result "Semantic Analysis" "200|202" "$CODE"
fi

# 2.8 List user notes summary
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes" \
  -H "Authorization: Bearer $TOKEN")
log_result "List Notes Summary" "200" "$CODE"

###############################################################################
# TASKS ENDPOINTS
###############################################################################

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[3] TASKS ENDPOINTS (11 tests)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 3.1 Create task (CORRECT: using WHATSAPP enum)
test_count
CODE=$(curl -s -o /tmp/create_task.json -w "%{http_code}" -X POST "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"description\": \"Test Task\",
    \"priority\": \"MEDIUM\",
    \"communication_type\": \"WHATSAPP\",
    \"is_action_approved\": false
  }")
TASK_ID=$(grep -o '"id":"[^"]*' /tmp/create_task.json | head -1 | cut -d'"' -f4)
log_result "Create Task" "200|201" "$CODE"

# 3.2 List tasks
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN")
log_result "List Tasks" "200" "$CODE"

# 3.3 Get due today
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/due-today" \
  -H "Authorization: Bearer $TOKEN")
log_result "Tasks Due Today" "200" "$CODE"

# 3.4 Get overdue
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/overdue" \
  -H "Authorization: Bearer $TOKEN")
log_result "Overdue Tasks" "200" "$CODE"

# 3.5 Get assigned to me
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/assigned-to-me" \
  -H "Authorization: Bearer $TOKEN")
log_result "Tasks Assigned to Me" "200" "$CODE"

# 3.6 Search tasks (CORRECT: using query_text parameter)
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/search?query_text=test" \
  -H "Authorization: Bearer $TOKEN")
log_result "Search Tasks" "200" "$CODE"

# 3.7 Get statistics
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/stats" \
  -H "Authorization: Bearer $TOKEN")
log_result "Task Statistics" "200" "$CODE"

# 3.8 Get task by ID
if [ ! -z "$TASK_ID" ]; then
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/$TASK_ID" \
      -H "Authorization: Bearer $TOKEN")
    log_result "Get Task by ID" "200" "$CODE"
    
    # 3.9 Update task
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE_URL/api/v1/tasks/$TASK_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"description\": \"Updated Task\", \"priority\": \"HIGH\"}")
    log_result "Update Task" "200" "$CODE"
    
    # 3.10 Duplicate task
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/duplicate" \
      -H "Authorization: Bearer $TOKEN")
    log_result "Duplicate Task" "200|201" "$CODE"
    
    # 3.11 Delete task
    test_count
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/api/v1/tasks/$TASK_ID" \
      -H "Authorization: Bearer $TOKEN")
    log_result "Delete Task" "200" "$CODE"
fi

###############################################################################
# AI ENDPOINTS
###############################################################################

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4] AI ENDPOINTS (2 tests)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 4.1 AI search (CORRECT: using POST with query parameter)
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/ai/search?query=test" \
  -H "Authorization: Bearer $TOKEN")
log_result "AI Search" "200" "$CODE"

# 4.2 AI statistics
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/ai/stats" \
  -H "Authorization: Bearer $TOKEN")
log_result "AI Statistics" "200" "$CODE"

###############################################################################
# USER ENDPOINTS
###############################################################################

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[5] USER ENDPOINTS (3 tests)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 5.1 Get current user
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN")
log_result "Get Current User" "200" "$CODE"

# 5.2 Search users
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/users/search?q=test" \
  -H "Authorization: Bearer $TOKEN")
log_result "Search Users" "200" "$CODE"

# 5.3 Logout
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/users/logout" \
  -H "Authorization: Bearer $TOKEN")
log_result "User Logout" "200" "$CODE"

###############################################################################
# ADMIN ENDPOINTS
###############################################################################

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[6] ADMIN ENDPOINTS (6 tests - returns 403 if not admin, expected)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Get fresh token (since we logged out)
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"curl_admin_test_$(date +%s)@test.com\",
    \"name\": \"Admin Test\",
    \"device_id\": \"device_admin_$(date +%s)\",
    \"device_model\": \"iPhone14\",
    \"token\": \"token\",
    \"timezone\": \"UTC\"
  }" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 6.1 Admin list users
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/admin/users" \
  -H "Authorization: Bearer $TOKEN")
log_result "Admin List Users" "200|403" "$CODE"

# 6.2 Admin user stats
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/admin/users/stats" \
  -H "Authorization: Bearer $TOKEN")
log_result "Admin User Stats" "200|403" "$CODE"

# 6.3 Admin list notes
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/admin/notes" \
  -H "Authorization: Bearer $TOKEN")
log_result "Admin List Notes" "200|403" "$CODE"

# 6.4 Admin list admins
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/admin/admins" \
  -H "Authorization: Bearer $TOKEN")
log_result "Admin List Admins" "200|403" "$CODE"

# 6.5 Admin status
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/admin/status" \
  -H "Authorization: Bearer $TOKEN")
log_result "Admin Status" "200|403" "$CODE"

# 6.6 Admin audit logs
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/admin/audit-logs" \
  -H "Authorization: Bearer $TOKEN")
log_result "Admin Audit Logs" "200|403" "$CODE"

###############################################################################
# ERROR HANDLING TESTS
###############################################################################

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[7] ERROR HANDLING (5 tests)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 7.1 No auth header
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes")
log_result "No Auth Header" "401" "$CODE"

# 7.2 Invalid token
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes" \
  -H "Authorization: Bearer invalid_token")
log_result "Invalid Token" "401" "$CODE"

# 7.3 Nonexistent note
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $TOKEN")
log_result "Nonexistent Note (404)" "404" "$CODE"

# 7.4 Nonexistent task
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $TOKEN")
log_result "Nonexistent Task (404)" "404" "$CODE"

# 7.5 Invalid enum value
test_count
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"description\": \"Test\",
    \"priority\": \"INVALID_PRIORITY\",
    \"communication_type\": \"WHATSAPP\"
  }")
log_result "Invalid Enum Value (422)" "400|422" "$CODE"

###############################################################################
# FINAL SUMMARY
###############################################################################

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}                            FINAL SUMMARY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "Total Tests:    ${BLUE}$TOTAL${NC}"
echo -e "Passed:         ${GREEN}$PASSED${NC}"
echo -e "Failed:         ${RED}$FAILED${NC}"

PASS_RATE=$((PASSED * 100 / TOTAL))
if [ $FAILED -eq 0 ]; then
    echo -e "Pass Rate:      ${GREEN}${PASS_RATE}%${NC}"
else
    echo -e "Pass Rate:      ${YELLOW}${PASS_RATE}%${NC}"
fi

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Save summary to report
{
    echo ""
    echo "================================================================================"
    echo "FINAL TEST RESULTS"
    echo "================================================================================"
    echo ""
    echo "Total Tests:  $TOTAL"
    echo "Passed:       $PASSED"
    echo "Failed:       $FAILED"
    echo "Pass Rate:    ${PASS_RATE}%"
    echo ""
    echo "Date: $(date)"
    echo "================================================================================"
} >> "$REPORT"

# Display final result
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           ✅ ALL TESTS PASSED! API IS FULLY FUNCTIONAL ✅          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}\n"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║              ❌ SOME TESTS FAILED - SEE REPORT BELOW              ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════╝${NC}\n"
    cat "$REPORT"
    exit 1
fi
