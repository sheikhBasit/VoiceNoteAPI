#!/bin/bash

# Test script for new API endpoints
# Tests: Note Creation, WhatsApp Draft, Semantic Analysis, Task Creation

BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=== Testing New API Endpoints ==="
echo ""

# 1. Get auth token (using sync for auto-registration)
echo "1. Getting auth token..."
UNIQUE_EMAIL="test_$(date +%s)@voicenote.ai"
TOKEN=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test User\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"biometric_test_token\",
    \"device_id\": \"test_device_$(date +%s)\",
    \"device_model\": \"API Tester\",
    \"primary_role\": \"DEVELOPER\",
    \"timezone\": \"UTC\"
  }" | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo -e "${RED}✗ Failed to get auth token${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Got auth token${NC}"
echo ""

# 2. Test Note Creation
echo "2. Testing POST /notes/create..."
NOTE_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Note from API",
    "summary": "This is a test note created via API",
    "priority": "HIGH"
  }')

NOTE_ID=$(echo $NOTE_RESPONSE | jq -r '.id')
if [ "$NOTE_ID" != "null" ] && [ -n "$NOTE_ID" ]; then
  echo -e "${GREEN}✓ Note created successfully (ID: $NOTE_ID)${NC}"
else
  echo -e "${RED}✗ Note creation failed${NC}"
  echo "Response: $NOTE_RESPONSE"
fi
echo ""

# 3. Test WhatsApp Draft
echo "3. Testing GET /notes/{id}/whatsapp..."
WHATSAPP_RESPONSE=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID/whatsapp" \
  -H "Authorization: Bearer $TOKEN")

DRAFT=$(echo $WHATSAPP_RESPONSE | jq -r '.draft')
if [ "$DRAFT" != "null" ] && [ -n "$DRAFT" ]; then
  echo -e "${GREEN}✓ WhatsApp draft generated${NC}"
  echo "Draft preview: ${DRAFT:0:50}..."
else
  echo -e "${RED}✗ WhatsApp draft generation failed${NC}"
  echo "Response: $WHATSAPP_RESPONSE"
fi
echo ""

# 4. Test Semantic Analysis
echo "4. Testing POST /notes/{id}/semantic-analysis..."
SEMANTIC_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/$NOTE_ID/semantic-analysis" \
  -H "Authorization: Bearer $TOKEN")

MESSAGE=$(echo $SEMANTIC_RESPONSE | jq -r '.message')
if [ "$MESSAGE" != "null" ] && [ -n "$MESSAGE" ]; then
  echo -e "${GREEN}✓ Semantic analysis triggered${NC}"
  echo "Message: $MESSAGE"
else
  echo -e "${RED}✗ Semantic analysis failed${NC}"
  echo "Response: $SEMANTIC_RESPONSE"
fi
echo ""

# 5. Test Task Creation
echo "5. Testing POST /tasks..."
TASK_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"note_id\": \"$NOTE_ID\",
    \"description\": \"Test task from API\",
    \"priority\": \"HIGH\"
  }")

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.id')
if [ "$TASK_ID" != "null" ] && [ -n "$TASK_ID" ]; then
  echo -e "${GREEN}✓ Task created successfully (ID: $TASK_ID)${NC}"
else
  echo -e "${RED}✗ Task creation failed${NC}"
  echo "Response: $TASK_RESPONSE"
fi
echo ""

# 6. Test Task Filtering - Due Today
echo "6. Testing GET /tasks/due-today..."
DUE_TODAY=$(curl -s -X GET "$BASE_URL/tasks/due-today" \
  -H "Authorization: Bearer $TOKEN")

if echo "$DUE_TODAY" | jq -e '. | length' > /dev/null 2>&1; then
  COUNT=$(echo "$DUE_TODAY" | jq '. | length')
  echo -e "${GREEN}✓ Due today tasks retrieved ($COUNT tasks)${NC}"
else
  echo -e "${RED}✗ Due today tasks failed${NC}"
fi
echo ""

# 7. Test Task Filtering - Overdue
echo "7. Testing GET /tasks/overdue..."
OVERDUE=$(curl -s -X GET "$BASE_URL/tasks/overdue" \
  -H "Authorization: Bearer $TOKEN")

if echo "$OVERDUE" | jq -e '. | length' > /dev/null 2>&1; then
  COUNT=$(echo "$OVERDUE" | jq '. | length')
  echo -e "${GREEN}✓ Overdue tasks retrieved ($COUNT tasks)${NC}"
else
  echo -e "${RED}✗ Overdue tasks failed${NC}"
fi
echo ""

# 8. Test Task Filtering - Assigned to Me
echo "8. Testing GET /tasks/assigned-to-me..."
ASSIGNED=$(curl -s -X GET "$BASE_URL/tasks/assigned-to-me" \
  -H "Authorization: Bearer $TOKEN")

if echo "$ASSIGNED" | jq -e '. | length' > /dev/null 2>&1; then
  COUNT=$(echo "$ASSIGNED" | jq '. | length')
  echo -e "${GREEN}✓ Assigned tasks retrieved ($COUNT tasks)${NC}"
else
  echo -e "${RED}✗ Assigned tasks failed${NC}"
fi
echo ""

# 9. Test Task Search
echo "9. Testing GET /tasks/search..."
SEARCH=$(curl -s -X GET "$BASE_URL/tasks/search?query=test" \
  -H "Authorization: Bearer $TOKEN")

if echo "$SEARCH" | jq -e '. | length' > /dev/null 2>&1; then
  COUNT=$(echo "$SEARCH" | jq '. | length')
  echo -e "${GREEN}✓ Task search working ($COUNT results)${NC}"
else
  echo -e "${RED}✗ Task search failed${NC}"
fi
echo ""

# 10. Test Task Statistics
echo "10. Testing GET /tasks/stats..."
STATS=$(curl -s -X GET "$BASE_URL/tasks/stats" \
  -H "Authorization: Bearer $TOKEN")

TOTAL=$(echo $STATS | jq -r '.total_tasks')
if [ "$TOTAL" != "null" ]; then
  echo -e "${GREEN}✓ Task statistics retrieved${NC}"
  echo "Total tasks: $TOTAL"
else
  echo -e "${RED}✗ Task statistics failed${NC}"
  echo "Response: $STATS"
fi
echo ""

# 11. Test Task Duplication
echo "11. Testing POST /tasks/{id}/duplicate..."
DUPLICATE=$(curl -s -X POST "$BASE_URL/tasks/$TASK_ID/duplicate" \
  -H "Authorization: Bearer $TOKEN")

DUP_ID=$(echo $DUPLICATE | jq -r '.id')
if [ "$DUP_ID" != "null" ] && [ -n "$DUP_ID" ] && [ "$DUP_ID" != "$TASK_ID" ]; then
  echo -e "${GREEN}✓ Task duplicated successfully (New ID: $DUP_ID)${NC}"
else
  echo -e "${RED}✗ Task duplication failed${NC}"
  echo "Response: $DUPLICATE"
fi
echo ""

echo "=== Test Summary ==="
echo "All 11 endpoint tests completed!"
echo "Check results above for any failures."
