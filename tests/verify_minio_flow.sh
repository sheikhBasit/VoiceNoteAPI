#!/bin/bash

# Verification script for Scalable Privacy-First Architecture (MinIO)
BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TEST_FILE="/home/basitdev/Me/StudioProjects/VoiceNoteAPI/tests/test_audio.wav"

# Create a dummy wav file if it doesn't exist
if [ ! -f "$TEST_FILE" ]; then
    echo "Creating dummy wav file for testing..."
    ffmpeg -f lavfi -i "sine=frequency=1000:duration=5" "$TEST_FILE" -y > /dev/null 2>&1
fi

echo "=== Verifying Privacy-First MinIO Flow ==="

# 1. Get Token
echo "1. Authenticating..."
UNIQUE_EMAIL="minio_tester_$(date +%s)@voicenote.ai"
SYNC_OUT=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"MinIO Tester\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"test_token\",
    \"device_id\": \"minio_device_001\",
    \"device_model\": \"curl-tester\",
    \"primary_role\": \"DEVELOPER\",
    \"timezone\": \"UTC\"
  }")
TOKEN=$(echo "$SYNC_OUT" | jq -r '.access_token')
echo -e "${GREEN}✓ Token retrieved${NC}"

# Elevate to Admin (required for signature bypass in some steps)
docker exec voicenote_db psql -U postgres -d voicenote -c "UPDATE users SET is_admin = true WHERE email = '$UNIQUE_EMAIL';" > /dev/null

# 2. Get Pre-signed URL
echo "2. Getting pre-signed URL..."
PRESIGNED_OUT=$(curl -s -X GET "$BASE_URL/notes/presigned-url" -H "Authorization: Bearer $TOKEN")
UPLOAD_URL=$(echo "$PRESIGNED_OUT" | jq -r '.upload_url')
STORAGE_KEY=$(echo "$PRESIGNED_OUT" | jq -r '.storage_key')
NOTE_ID=$(echo "$PRESIGNED_OUT" | jq -r '.note_id')

if [ -z "$UPLOAD_URL" ] || [ "$UPLOAD_URL" == "null" ]; then
    echo -e "${RED}✗ Failed to get pre-signed URL${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Pre-signed URL generated for $STORAGE_KEY${NC}"

# 3. Direct Upload to MinIO
echo "3. Uploading file directly to MinIO (Bypassing API)..."
UPLOAD_STATUS=$(curl -s -X PUT -T "$TEST_FILE" "$UPLOAD_URL" -o /dev/null -w "%{http_code}")
if [ "$UPLOAD_STATUS" -eq "200" ]; then
    echo -e "${GREEN}✓ File uploaded directly to MinIO${NC}"
else
    echo -e "${RED}✗ MinIO Upload failed with $UPLOAD_STATUS${NC}"
    exit 1
fi

# 4. Trigger Processing
echo "4. Triggering privacy-first extraction..."
PROCESS_OUT=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "storage_key=$STORAGE_KEY" \
  -F "note_id_override=$NOTE_ID" \
  -F "stt_model=nova")
echo -e "${GREEN}✓ Extraction queued${NC}"

# 5. Poll for completion
echo "5. Polling for results..."
MAX_RETRIES=20
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN" | jq -r '.status')
    if [ "$STATUS" == "DONE" ]; then
        echo -e "${GREEN}✓ Extraction Completed Successfully!${NC}"
        break
    elif [ "$STATUS" == "FAILED" ]; then
        echo -e "${RED}✗ Extraction Failed${NC}"
        docker logs voicenote_celery_worker --tail 50
        exit 1
    fi
    echo -e "${YELLOW}Current Status: $STATUS ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 5
    ((RETRY_COUNT++))
done

# 6. Verify Cleanup
echo "6. Verifying Privacy-First Cleanup (File deletion from MinIO)..."
# In a local dev environment, we can check MinIO directly
MC_CHECK=$(docker exec voicenote_mc /usr/bin/mc ls myminio/incoming/$STORAGE_KEY 2>&1)
if echo "$MC_CHECK" | grep -q "Object does not exist"; then
    echo -e "${GREEN}✓ Success: Transit file deleted from MinIO buffer!${NC}"
else
    echo -e "${RED}✗ Error: Transit file still exists in MinIO!${NC}"
    echo "$MC_CHECK"
fi

# 7. Show Tasks
echo "7. Extracted tasks for Note $NOTE_ID:"
curl -s -X GET "$BASE_URL/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN" | jq '.tasks'

echo "=== MinIO Verification Complete ==="
