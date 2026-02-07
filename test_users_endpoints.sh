#!/bin/bash

# Comprehensive Curl Tests for Users API Endpoints
# Tests all 10 user endpoints with detailed logging

set -e

BASE_URL="http://localhost:8000/api/v1"
TEST_USER_EMAIL="test_user_$(date +%s)@example.com"
TEST_USER_NAME="Test User"
TEST_DEVICE_ID="device_$(openssl rand -hex 6)"
TEST_DEVICE_MODEL="TestDevice_1.0"
TEST_TOKEN="test_biometric_token"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function for pretty output
print_header() {
    echo -e "\n${BLUE}=================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_response() {
    echo -e "${BLUE}RESPONSE:${NC}"
    echo "$1" | jq '.' 2>/dev/null || echo "$1"
}

# ============================================================================
# TEST 1: POST /users/sync - Create New User
# ============================================================================
print_header "TEST 1: POST /api/v1/users/sync - Create New User"
print_test "Creating new user with email: $TEST_USER_EMAIL"

SYNC_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_USER_EMAIL\",
    \"name\": \"$TEST_USER_NAME\",
    \"device_id\": \"$TEST_DEVICE_ID\",
    \"device_model\": \"$TEST_DEVICE_MODEL\",
    \"token\": \"$TEST_TOKEN\",
    \"timezone\": \"UTC\"
  }")

print_response "$SYNC_RESPONSE"

# Extract user ID and token
USER_ID=$(echo "$SYNC_RESPONSE" | jq -r '.user.id // empty')
ACCESS_TOKEN=$(echo "$SYNC_RESPONSE" | jq -r '.access_token // empty')
IS_NEW=$(echo "$SYNC_RESPONSE" | jq -r '.is_new_user // empty')

if [ -n "$USER_ID" ] && [ -n "$ACCESS_TOKEN" ] && [ "$IS_NEW" = "true" ]; then
    print_success "User created successfully (ID: $USER_ID)"
else
    print_error "Failed to create user"
    echo "USER_ID=$USER_ID, ACCESS_TOKEN=$ACCESS_TOKEN, IS_NEW=$IS_NEW"
fi

# ============================================================================
# TEST 2: POST /users/sync - Login Existing User
# ============================================================================
print_header "TEST 2: POST /api/v1/users/sync - Login Existing User"
print_test "Authenticating same user again"

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_USER_EMAIL\",
    \"name\": \"$TEST_USER_NAME\",
    \"device_id\": \"$TEST_DEVICE_ID\",
    \"device_model\": \"$TEST_DEVICE_MODEL\",
    \"token\": \"$TEST_TOKEN\",
    \"timezone\": \"UTC\"
  }")

print_response "$LOGIN_RESPONSE"

IS_NEW_LOGIN=$(echo "$LOGIN_RESPONSE" | jq -r '.is_new_user // empty')
if [ "$IS_NEW_LOGIN" = "false" ]; then
    print_success "Existing user authenticated (is_new_user=false)"
else
    print_error "Expected is_new_user=false for existing user"
fi

# ============================================================================
# TEST 3: GET /users/me - Get Current User Profile
# ============================================================================
print_header "TEST 3: GET /api/v1/users/me - Get Current User Profile"
print_test "Fetching current user profile"

ME_RESPONSE=$(curl -s -X GET "$BASE_URL/users/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

print_response "$ME_RESPONSE"

ME_ID=$(echo "$ME_RESPONSE" | jq -r '.id // empty')
ME_EMAIL=$(echo "$ME_RESPONSE" | jq -r '.email // empty')

if [ "$ME_ID" = "$USER_ID" ] && [ "$ME_EMAIL" = "$TEST_USER_EMAIL" ]; then
    print_success "Current user profile retrieved correctly"
else
    print_error "Profile data mismatch"
fi

# ============================================================================
# TEST 4: GET /users/{user_id} - Get User Profile by ID
# ============================================================================
print_header "TEST 4: GET /api/v1/users/{user_id} - Get User Profile by ID"
print_test "Fetching user profile for: $USER_ID"

PROFILE_RESPONSE=$(curl -s -X GET "$BASE_URL/users/$USER_ID")

print_response "$PROFILE_RESPONSE"

PROFILE_ID=$(echo "$PROFILE_RESPONSE" | jq -r '.id // empty')
if [ "$PROFILE_ID" = "$USER_ID" ]; then
    print_success "User profile retrieved by ID"
else
    print_error "Failed to retrieve user profile by ID"
fi

# ============================================================================
# TEST 5: GET /users/search - Search Users
# ============================================================================
print_header "TEST 5: GET /api/v1/users/search - Search Users"
print_test "Searching for users with query: $TEST_USER_NAME"

SEARCH_RESPONSE=$(curl -s -X GET "$BASE_URL/users/search?query=$TEST_USER_NAME")

print_response "$SEARCH_RESPONSE"

SEARCH_COUNT=$(echo "$SEARCH_RESPONSE" | jq 'length // 0')
if [ "$SEARCH_COUNT" -gt 0 ]; then
    print_success "Search returned $SEARCH_COUNT results"
else
    print_error "Search returned no results"
fi

# ============================================================================
# TEST 6: PATCH /users/me - Update User Profile
# ============================================================================
print_header "TEST 6: PATCH /api/v1/users/me - Update User Profile"
print_test "Updating user profile with new name"

UPDATE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/users/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Updated User Name\",
    \"work_start_hour\": 9,
    \"work_end_hour\": 17,
    \"work_days\": [1, 2, 3, 4, 5]
  }")

print_response "$UPDATE_RESPONSE"

UPDATED_NAME=$(echo "$UPDATE_RESPONSE" | jq -r '.name // empty')
if [ "$UPDATED_NAME" = "Updated User Name" ]; then
    print_success "User profile updated successfully"
else
    print_error "Failed to update user profile"
fi

# ============================================================================
# TEST 7: Test Invalid Email in Sync
# ============================================================================
print_header "TEST 7: POST /api/v1/users/sync - Reject Invalid Email"
print_test "Testing invalid email validation"

INVALID_EMAIL_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"invalid_email\",
    \"name\": \"Test\",
    \"device_id\": \"device_test\",
    \"device_model\": \"TestDevice\",
    \"token\": \"token\",
    \"timezone\": \"UTC\"
  }")

print_response "$INVALID_EMAIL_RESPONSE"

ERROR_DETAIL=$(echo "$INVALID_EMAIL_RESPONSE" | jq -r '.detail // empty')
if [ -n "$ERROR_DETAIL" ]; then
    print_success "Invalid email properly rejected with error: $ERROR_DETAIL"
else
    print_error "Invalid email was not rejected"
fi

# ============================================================================
# TEST 8: Test Empty Device ID
# ============================================================================
print_header "TEST 8: POST /api/v1/users/sync - Reject Empty Device ID"
print_test "Testing empty device_id validation"

EMPTY_DEVICE_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"test_empty_device@example.com\",
    \"name\": \"Test\",
    \"device_id\": \"\",
    \"device_model\": \"TestDevice\",
    \"token\": \"token\",
    \"timezone\": \"UTC\"
  }")

print_response "$EMPTY_DEVICE_RESPONSE"

EMPTY_ERROR=$(echo "$EMPTY_DEVICE_RESPONSE" | jq -r '.detail // empty')
if [ -n "$EMPTY_ERROR" ]; then
    print_success "Empty device_id properly rejected"
else
    print_error "Empty device_id was not rejected"
fi

# ============================================================================
# TEST 9: GET /users/{user_id} - Non-existent User
# ============================================================================
print_header "TEST 9: GET /api/v1/users/{user_id} - Non-existent User"
print_test "Fetching non-existent user"

FAKE_ID="00000000-0000-0000-0000-000000000000"
NONEXISTENT_RESPONSE=$(curl -s -X GET "$BASE_URL/users/$FAKE_ID")

print_response "$NONEXISTENT_RESPONSE"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/users/$FAKE_ID")
if [ "$HTTP_STATUS" = "404" ]; then
    print_success "Non-existent user returns 404"
else
    print_error "Expected 404 for non-existent user, got $HTTP_STATUS"
fi

# ============================================================================
# TEST 10: DELETE /users/me - Soft Delete User
# ============================================================================
print_header "TEST 10: DELETE /api/v1/users/me - Soft Delete User"
print_test "Deleting user account (soft delete)"

DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/users/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

print_response "$DELETE_RESPONSE"

DELETE_SUCCESS=$(echo "$DELETE_RESPONSE" | jq -r '.success // .status // empty')
if [ -n "$DELETE_SUCCESS" ]; then
    print_success "User deleted successfully"
else
    print_error "Failed to delete user"
fi

# ============================================================================
# TEST 11: Verify User is Deleted
# ============================================================================
print_header "TEST 11: Verify Deleted User Cannot Be Accessed"
print_test "Attempting to fetch deleted user"

DELETED_VERIFY=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/users/$USER_ID")
if [ "$DELETED_VERIFY" = "404" ]; then
    print_success "Deleted user returns 404 (soft delete works)"
else
    print_error "Deleted user should return 404, got $DELETED_VERIFY"
fi

# ============================================================================
# TEST 12: POST /users/logout
# ============================================================================
print_header "TEST 12: POST /api/v1/users/logout - Logout User"
print_test "Creating new user for logout test"

# Create a new user for logout test
LOGOUT_SYNC=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"test_logout_$(date +%s)@example.com\",
    \"name\": \"Logout Test\",
    \"device_id\": \"device_logout_$(openssl rand -hex 6)\",
    \"device_model\": \"TestDevice\",
    \"token\": \"token\",
    \"timezone\": \"UTC\"
  }")

LOGOUT_TOKEN=$(echo "$LOGOUT_SYNC" | jq -r '.access_token // empty')

if [ -n "$LOGOUT_TOKEN" ]; then
    print_test "Testing logout with token"
    LOGOUT_RESPONSE=$(curl -s -X POST "$BASE_URL/users/logout" \
      -H "Authorization: Bearer $LOGOUT_TOKEN")
    
    print_response "$LOGOUT_RESPONSE"
    
    LOGOUT_MSG=$(echo "$LOGOUT_RESPONSE" | jq -r '.message // empty')
    if [ -n "$LOGOUT_MSG" ]; then
        print_success "User logged out successfully"
    else
        print_error "Failed to logout user"
    fi
else
    print_error "Failed to create test user for logout"
fi

# ============================================================================
# SUMMARY
# ============================================================================
print_header "TEST SUMMARY"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))

echo -e "${GREEN}✅ PASSED: $TESTS_PASSED${NC}"
echo -e "${RED}❌ FAILED: $TESTS_FAILED${NC}"
echo -e "${BLUE}📊 TOTAL:  $TOTAL_TESTS${NC}"
echo -e "${YELLOW}📈 SUCCESS RATE: ${PASS_RATE}%${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL TESTS PASSED!${NC}\n"
    exit 0
else
    echo -e "\n${RED}⚠️  SOME TESTS FAILED${NC}\n"
    exit 1
fi
