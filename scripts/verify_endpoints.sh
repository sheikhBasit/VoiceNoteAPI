#!/bin/bash
set -e

BASE_URL="http://localhost:8000/api/v1"
echo "🔍 Starting API Verification..."

# 1. Register/Login User
echo -e "\n1. 🔑 Authenticating User..."
SYNC_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Integration Test User",
    "email": "integration@test.com",
    "token": "tok_12345",
    "device_id": "device_int_001",
    "device_model": "CurlScript",
    "timezone": "UTC"
  }')

ACCESS_TOKEN=$(echo $SYNC_RESPONSE | jq -r '.access_token')
USER_ID=$(echo $SYNC_RESPONSE | jq -r '.user.id')

if [ "$ACCESS_TOKEN" == "null" ]; then
  echo "❌ Auth Failed: $SYNC_RESPONSE"
  exit 1
fi
echo "✅ Authenticated as $USER_ID"

AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"

# 2. Create a Note
echo -e "\n2. 📝 Creating Note..."
NOTE_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/create" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Integration Test Note",
    "summary": "This is a test note created by the curl verification script",
    "is_audio_note": false
  }')

NOTE_ID=$(echo $NOTE_RESPONSE | jq -r '.id')
echo "✅ Created Note: $NOTE_ID"

# 3. Create a Task (Linked to Note)
echo -e "\n3. ✅ Creating Task..."
TASK_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Follow up on integration test",
    "priority": "LOW",
    "note_id": "'"$NOTE_ID"'"
  }')

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.id')
echo "✅ Created Task: $TASK_ID"

# 4. List Tasks
echo -e "\n4. 📋 Listing Tasks..."
curl -s -X GET "$BASE_URL/tasks" -H "$AUTH_HEADER" | jq '.[:2]'

# 5. Soft Delete Note
echo -e "\n5. 🗑️ Soft Deleting Note..."
curl -s -X DELETE "$BASE_URL/notes/$NOTE_ID" -H "$AUTH_HEADER" | jq .

# 6. Verify Note is Deleted (Should be in trash list or 404 on normal get check implementation)
# Assuming normal list filters out deleted
echo -e "\n6. 🔍 Verifying Deletion..."
LIST_NOTES=$(curl -s -X GET "$BASE_URL/notes" -H "$AUTH_HEADER")
echo $LIST_NOTES | jq 'map(select(.id == "'"$NOTE_ID"'"))'

# 7. Restore Note (New Endpoint)
echo -e "\n7. ♻️ Restoring Note..."
RESTORE_RESP=$(curl -s -X PATCH "$BASE_URL/notes/$NOTE_ID/restore" -H "$AUTH_HEADER")
echo $RESTORE_RESP | jq .
IS_DELETED=$(echo $RESTORE_RESP | jq -r '.is_deleted')

if [ "$IS_DELETED" == "false" ]; then
    echo "✅ Note Restored Successfully"
else
    echo "❌ Restore Failed"
fi

# 8. Bulk Delete Tasks (New Endpoint)
echo -e "\n8. 💥 Bulk Deleting Tasks..."
BULK_DEL=$(curl -s -X DELETE "$BASE_URL/tasks" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "task_ids": ["'"$TASK_ID"'"]
  }')
echo $BULK_DEL | jq .

echo -e "\n🎉 Verification Complete!"
