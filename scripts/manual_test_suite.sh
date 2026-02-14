#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper for formatted output
function print_header {
    echo -e "\n${GREEN}=== $1 ===${NC}"
}

function check_status {
    if [ "$1" == "$2" ]; then
        echo -e "${GREEN}PASS${NC}: Expected $2, got $1"
    else
        echo -e "${RED}FAIL${NC}: Expected $2, got $1"
    fi
}

# 1. Health Check
print_header "1. Health Check"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
check_status "$HEALTH" "200"

# 2. Authentication (Get Token)
print_header "2. Authentication"
EMAIL="curl_tester_$(date +%s)@example.com"
echo "Registering user: $EMAIL"

REGISTER_PAYLOAD=$(cat <<EOF
{
  "email": "$EMAIL",
  "name": "Curl Tester",
  "password": "curlpassword123",
  "timezone": "UTC"
}
EOF
)

RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/register" \
    -H "Content-Type: application/json" \
    -d "$REGISTER_PAYLOAD")

TOKEN=$(echo $RESPONSE | jq -r .access_token)

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}Failed to authenticate.${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "Token acquired."

# 3. Valid Note Creation
print_header "3. Valid Note Creation"
NOTE_PAYLOAD='{
  "title": "Curl Test Note",
  "summary": "This note was created via manual curl script.",
  "priority": "HIGH"
}'

RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/notes/create" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$NOTE_PAYLOAD")

NOTE_ID=$(echo $RESPONSE | jq -r .id)
echo "Created Note ID: $NOTE_ID"

if [ "$NOTE_ID" == "null" ]; then
    echo -e "${RED}Failed to create note.${NC}"
    echo "Response: $RESPONSE"
else
    echo -e "${GREEN}PASS${NC}: Note created successfully."
fi

# 4. Input Validation (Edge Case: Empty Task Description)
print_header "4. Input Validation (Empty Task Description)"
TASK_PAYLOAD=$(cat <<EOF
{
  "note_id": "$NOTE_ID",
  "description": "", 
  "priority": "HIGH"
}
EOF
)

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/tasks" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$TASK_PAYLOAD")

check_status "$STATUS" "400"

# 5. Semantic Analysis Trigger (New Endpoint)
print_header "5. Trigger Semantic Analysis"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/notes/$NOTE_ID/semantic-analysis" \
    -H "Authorization: Bearer $TOKEN")

# Expect 202 Accepted
check_status "$STATUS" "202"

# 6. Rate Limiting Test
print_header "6. Rate Limiting Test (Tasks Stats: Limit ~5-10/min)"
# We will hit it 15 times to ensure we cross the threshold
LIMIT_HIT=false
for i in {1..15}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/tasks/stats" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ "$STATUS" == "429" ]; then
        echo -e "${GREEN}PASS${NC}: Hit Rate Limit (429) on request $i"
        LIMIT_HIT=true
        break
    else
        echo -n "."
    fi
done

if [ "$LIMIT_HIT" == "false" ]; then
    echo -e "\n${RED}FAIL/WARN${NC}: Did not trigger rate limit. Ensure RATE_LIMIT_ENABLED=true in .env"
fi

# 7. Unauthorized Access
print_header "7. Unauthorized Access"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes" \
    -H "Authorization: Bearer invalid_token_123")

check_status "$STATUS" "401"


# 8. Method Not Allowed
print_header "8. Method Not Allowed (GET on POST endpoint)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/notes/$NOTE_ID/semantic-analysis" \
    -H "Authorization: Bearer $TOKEN")

check_status "$STATUS" "405"

echo -e "\n${GREEN}=== Manual Verification Complete ===${NC}"
