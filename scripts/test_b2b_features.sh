#!/bin/bash

# Configuration
API_URL="http://localhost:8001"
USER_ID="bench-admin-id"
AUTH_TOKEN=""

# 1. Authenticate / Setup
echo "--- Setting up Test Bench ---"
AUTH_TOKEN=$(curl -s -X POST "$API_URL/api/v1/users/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin User",
    "email": "admin@voicenote.api",
    "device_id": "bench-admin-device",
    "token": "bench-admin-biometric-token",
    "device_model": "Benchmark Runner",
    "timezone": "UTC"
  }' | grep -oP '(?<="access_token":")[^"]+')

if [ -z "$AUTH_TOKEN" ]; then
    echo "Auth failed!"
    exit 1
fi
echo "Auth Token obtained."

# 2. Create Organization & Work Location
echo "--- Creating Organization ---"
ORG_ID_JSON=$(curl -s -X POST "$API_URL/api/v1/admin/organizations" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$(python3 -c 'import uuid; print(uuid.uuid4())')\",
    \"name\": \"Antigravity HQ\",
    \"admin_user_id\": \"$USER_ID\"
  }")
ORG_ID=$(echo $ORG_ID_JSON | jq -r .id)
echo "Org Created: $ORG_ID ($ORG_ID_JSON)"

echo "--- Checking Initial Corporate Wallet Balance ---"
curl -s -X GET "$API_URL/api/v1/admin/organizations/$ORG_ID/balance" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq .

echo "--- Adding Work Location (Geofence) ---"
curl -s -X POST "$API_URL/api/v1/admin/locations" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"org_id\": \"$ORG_ID\",
    \"name\": \"Main Lab\",
    \"latitude\": 37.7749,
    \"longitude\": -122.4194,
    \"radius\": 500
  }"

# 3. Upload Note inside Geofence (HQ)
echo "--- Uploading Note inside Geofence ---"
UPLOAD_RES=$(curl -s -X POST "$API_URL/api/v1/notes/process" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "X-GPS-Coords: 37.7749,-122.4194" \
  -F "file=@tests/test_audio.wav" \
  -F "debug_sync=true")
echo "DEBUG UPLOAD_RES: $UPLOAD_RES"
NOTE_ID=$(echo $UPLOAD_RES | jq -r .note_id)
echo "Note Created: $NOTE_ID"

echo "Waiting for background billing task..."
sleep 2

echo "--- Checking Wallet Balances after Upload ---"
echo "Admin Personal Balance:"
curl -s -X GET "$API_URL/api/v1/users/balance" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq .

echo "Corporate Wallet Balance (should be reduced):"
curl -s -X GET "$API_URL/api/v1/admin/organizations/$ORG_ID/balance" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq .

# 4. Semantic Linking Test
echo "--- Verifying Semantic Linking ---"
curl -s -X GET "$API_URL/api/v1/notes/$NOTE_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq .related_notes

echo "--- Test Complete ---"
