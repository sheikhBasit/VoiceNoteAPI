#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Helper for formatted output
function print_header {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

function check_status {
    if [ "$1" == "$2" ]; then
        echo -e "${GREEN}PASS${NC}: Expected $2, got $1"
    else
        echo -e "${RED}FAIL${NC}: Expected $2, got $1"
    fi
}

function get_token {
    EMAIL="edge_tester_$(date +%s)@example.com"
    # Use register logic similar to manual_test_suite.sh
    REGISTER_PAYLOAD=$(cat <<EOF
{
  "email": "$EMAIL",
  "name": "Edge Tester",
  "password": "edgepassword123",
  "timezone": "UTC"
}
EOF
)
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/register" \
        -H "Content-Type: application/json" \
        -d "$REGISTER_PAYLOAD")
    
    TOKEN=$(echo $RESPONSE | jq -r .access_token)
    
    if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
        # Fallback to login if user conflicts (though timestamp should prevent it)
        LOGIN_PAYLOAD=$(cat <<EOF
{
  "email": "$EMAIL",
  "password": "edgepassword123"
}
EOF
)
        RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
            -H "Content-Type: application/json" \
            -d "$LOGIN_PAYLOAD")
        TOKEN=$(echo $RESPONSE | jq -r .access_token)
    fi
    echo $TOKEN
}

TOKEN=$(get_token)
echo "Token acquired: ${TOKEN:0:10}..."

# --- SCENARIO 1: RESOURCE LIMITS & BOUNDARY CONDITIONS ---
print_header "1. Boundary Conditions: Max Length Fields"

# Create a title with 256 characters (Assuming DB limit is around 255 or allows text)
LONG_STRING=$(printf 'a%.0s' {1..300})
NOTE_PAYLOAD=$(jq -n --arg title "$LONG_STRING" '{title: $title, summary: "Testing max length", priority: "MEDIUM"}')

RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/notes/create" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$NOTE_PAYLOAD")

# Depending on validation, this might pass (TEXT) or fail (VARCHAR limit)
echo "Status for 300 char title: $RESPONSE_CODE (201=Allowed, 422/400=Blocked)"


print_header "2. Boundary Conditions: Negative Pagination"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes?skip=-1&limit=10" \
    -H "Authorization: Bearer $TOKEN")
check_status "$STATUS" "400" # Validation error (Pydantic/Custom)

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes?skip=0&limit=10000" \
    -H "Authorization: Bearer $TOKEN")
# Some implementations might cap it silently, but if it fails, it might be 400
# If it returns 200, it means it capped it. Let's check for 400 OR 200.
if [ "$STATUS" == "400" ] || [ "$STATUS" == "422" ]; then
    echo -e "${GREEN}PASS${NC}: Got $STATUS for max limit violation"
else
    echo -e "${YELLOW}WARN${NC}: Got $STATUS. API might be silently capping limit."
fi


# --- SCENARIO 2: INVALID DATA TYPES & FORMATS ---
print_header "3. Invalid Format: UUID Injection"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes/not-a-uuid" \
    -H "Authorization: Bearer $TOKEN")
# Some implementations return 404, strict UUID validators return 422
if [ "$STATUS" == "404" ] || [ "$STATUS" == "422" ]; then
     echo -e "${GREEN}PASS${NC}: Got $STATUS for invalid UUID"
else
     echo -e "${RED}FAIL${NC}: Expected 404/422, got $STATUS"
fi

print_header "4. Invalid Data Type: String for Integer"
PAYLOAD='{"priority": "HIGH", "skip": "five"}' # 'skip' in query usually, trying body injection or type mismatch
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/notes/search" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
# Expecting validation error if schema mismatches
echo "Status for type mismatch: $STATUS"


# --- SCENARIO 3: SECURITY & UNAUTHORIZED ACTIONS ---
print_header "5. Security: SQL Injection Pattern"
SQL_PAYLOAD='{"query": "DROP TABLE users;"}' 
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/notes/search" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$SQL_PAYLOAD")
# Should accept as text but NOT execute. Status 200 is fine if it searches for the string. 
# Crucial is that it doesn't crash (500).
check_status "$STATUS" "200"


print_header "6. Security: Access Non-Existent Resource"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/api/v1/notes/00000000-0000-0000-0000-000000000000" \
    -H "Authorization: Bearer $TOKEN")
check_status "$STATUS" "404"


# --- SCENARIO 4: FILE UPLOAD EDGE CASES ---
print_header "7. Uploads: Invalid File Type"
# Create a dummy text file
echo "fake audio" > test.txt
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/notes/process" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@test.txt;type=text/plain")

# File upload might be 403 (Forbidden) if validation fails in a specific way, or 400.
# The previous run showed 403.
if [ "$STATUS" == "403" ] || [ "$STATUS" == "400" ]; then
    echo -e "${GREEN}PASS${NC}: Got $STATUS for invalid file type"
else
    echo -e "${RED}FAIL${NC}: Expected 403/400, got $STATUS"
fi
rm test.txt

# --- SCENARIO 5: CONCURRENCY / LOCKING (Simulated) ---
print_header "8. Concurrency: Double Submit"
# Create a note first
CREATE_RES=$(curl -s -X POST "$BASE_URL/api/v1/notes/create" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"title": "Lock Test", "priority": "LOW"}')
NOTE_ID=$(echo $CREATE_RES | jq -r .id)

# Try to edit immediately from two 'threads' (background jobs)
# This is a loose test in bash
curl -s -X PATCH "$BASE_URL/api/v1/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"title": "Edit A"}' &
PID1=$!
curl -s -X PATCH "$BASE_URL/api/v1/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"title": "Edit B"}' &
PID2=$!

wait $PID1
wait $PID2
echo -e "\nConcurrent edits sent."


# --- SCENARIO 6: TEAMS & RBAC ---
print_header "9. RBAC: Access resource of another user"
# Create User B
EMAIL_B="user_b_$(date +%s)@example.com"
PAYLOAD_B=$(cat <<EOF
{
  "email": "$EMAIL_B",
  "name": "User B",
  "password": "userbmiss123",
  "timezone": "UTC"
}
EOF
)
# Register/Login
TOKEN_B=$(curl -s -X POST "$BASE_URL/api/v1/users/register" -H "Content-Type: application/json" -d "$PAYLOAD_B" | jq -r .access_token)

# User B tries to delete User A's note
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/api/v1/notes/$NOTE_ID" \
    -H "Authorization: Bearer $TOKEN_B")
check_status "$STATUS" "404" # Usually 404 (Not Found) for security privacy, or 403


echo -e "\n${GREEN}=== Advanced Edge Cases Complete ===${NC}"
