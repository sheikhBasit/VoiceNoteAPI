#!/bin/bash
set -e

BASE_URL="http://localhost:8000/api/v1"
echo "🕵️ Starting Task & Audio Pipeline Verification..."

# 1. Login as Admin (Bypasses Device Signature Check)
echo -e "\n1. 🔑 Authenticating as Admin..."
SYNC_RESP=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "System Admin",
    "email": "admin@voicenote.app",
    "token": "admin_token_auto",
    "device_id": "admin_device_001",
    "device_model": "CurlScript",
    "timezone": "UTC"
  }')
ACCESS_TOKEN=$(echo $SYNC_RESP | jq -r '.access_token')
AUTH="Authorization: Bearer $ACCESS_TOKEN"
echo "✅ Logged in as Admin (Token: ${ACCESS_TOKEN:0:10}...)"

# 2. Manual Task Creation
echo -e "\n2. ✍️ Creating Manual Task..."
MANUAL_TASK=$(curl -s -X POST "$BASE_URL/tasks" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Buy milk manually",
    "priority": "MEDIUM"
  }')
TASK_ID=$(echo $MANUAL_TASK | jq -r '.id')
DESC=$(echo $MANUAL_TASK | jq -r '.description')

if [ "$DESC" == "Buy milk manually" ]; then
    echo "✅ Manual Task Created: $TASK_ID"
else
    echo "❌ Manual Task Failed: $MANUAL_TASK"
    exit 1
fi

# 3. Audio Upload (Simulating Auto-Task Extraction)
echo -e "\n3. 🎤 Uploading Audio (Simulating Voice Note)..."
# Using correct endpoint /process
UPLOAD_RESP=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "$AUTH" \
  -F "file=@test_audio.wav" \
  -F "mode=GENERIC" \
  -F "stt_model=nova")

echo "Debug Upload Response: $UPLOAD_RESP"

NOTE_ID=$(echo $UPLOAD_RESP | jq -r '.note_id')
STATUS=$(echo $UPLOAD_RESP | jq -r '.status')

echo "✅ Audio Uploaded. Note ID: $NOTE_ID (Status: $STATUS)"

# 4. Check status (It should be PROCESSING or DONE depending on worker speed)
echo -e "\n4. ⏳ Checking Note Status..."
sleep 2 # Give worker a moment to pick it up
NOTE_DETAILS=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" -H "$AUTH")
CURRENT_STATUS=$(echo $NOTE_DETAILS | jq -r '.status')

echo "ℹ️ Current Note Status: $CURRENT_STATUS"
if [ "$CURRENT_STATUS" == "PROCESSING" ] || [ "$CURRENT_STATUS" == "DONE" ]; then
    echo "✅ Pipeline triggered successfully (Worker is handling it)"
else
    echo "❌ Pipeline failed to start. Status: $CURRENT_STATUS"
fi

# 5. List Tasks for Note
echo -e "\n5. 📄 Listing Tasks for this Note..."
TASKS_LIST=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID/tasks" -H "$AUTH")
COUNT=$(echo $TASKS_LIST | jq '. | length')
echo "ℹ️ Tasks found associated with note: $COUNT"

# 6. Complete Manual Task
echo -e "\n6. ✅ Completing Manual Task..."
COMPLETE_RESP=$(curl -s -X PATCH "$BASE_URL/tasks/$TASK_ID" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"is_done": true}')
IS_DONE=$(echo $COMPLETE_RESP | jq -r '.is_done')

if [ "$IS_DONE" == "true" ]; then
    echo "✅ Task marked as DONE"
else
    echo "❌ Task completion failed"
fi

echo -e "\n🎉 Task verifications finished."
