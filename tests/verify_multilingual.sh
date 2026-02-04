#!/bin/bash

# Verification script for Multilingual STT and Model Selection
BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

SAMPLE_AUDIO="tests/assets/audio/ideal/clean_30s.wav"
if [ ! -f "$SAMPLE_AUDIO" ]; then
    echo "Creating a dummy wav file for logic test..."
    # Create a tiny valid wav file
    echo "UklGRiSBAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0Yf6BAAAAAA==" | base64 -d > "$SAMPLE_AUDIO"
fi

echo "=== Verifying Multilingual STT & Model Selection ==="

# 1. Get Token
echo "1. Getting auth token..."
UNIQUE_EMAIL="tester_$(date +%s)@voicenote.ai"
SYNC_OUT=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"STT Tester\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"test_token\",
    \"device_id\": \"test_device_stt\",
    \"device_model\": \"curl-tester\",
    \"primary_role\": \"DEVELOPER\",
    \"timezone\": \"UTC\"
  }")
TOKEN=$(echo "$SYNC_OUT" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo -e "${RED}✗ Failed to get token${NC}"
    echo "Response: $SYNC_OUT"
    exit 1
fi
echo -e "${GREEN}✓ Token retrieved${NC}"

# Elevate to Admin to bypass signature
docker exec voicenote_db psql -U postgres -d voicenote -c "UPDATE users SET is_admin = true WHERE email = '$UNIQUE_EMAIL';" > /dev/null
echo "✓ Elevated $UNIQUE_EMAIL to admin"

# 2. Test Multilingual Upload (Deepgram)
echo "2. Testing /process with languages=en,ur and stt_model=nova..."
UPLOAD_1=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$SAMPLE_AUDIO" \
  -F "languages=en,ur" \
  -F "stt_model=nova")

NOTE_ID_1=$(echo "$UPLOAD_1" | jq -r '.note_id')
if [ -n "$NOTE_ID_1" ] && [ "$NOTE_ID_1" != "null" ]; then
    echo -e "${GREEN}✓ Upload successful (Note ID: $NOTE_ID_1)${NC}"
else
    echo -e "${RED}✗ Upload failed${NC}"
    echo "Response: $UPLOAD_1"
fi

# 3. Test Dual STT Upload (Both)
echo "3. Testing /process with stt_model=both..."
UPLOAD_2=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$SAMPLE_AUDIO" \
  -F "stt_model=both")

NOTE_ID_2=$(echo "$UPLOAD_2" | jq -r '.note_id')
if [ -n "$NOTE_ID_2" ] && [ "$NOTE_ID_2" != "null" ]; then
    echo -e "${GREEN}✓ Upload successful (Note ID: $NOTE_ID_2)${NC}"
else
    echo -e "${RED}✗ Upload failed${NC}"
    echo "Response: $UPLOAD_2"
fi

# 4. Success check
echo ""
echo "=== Verification Summary ==="
echo "If the above calls returned valid Note IDs, the API logic for new fields is working."
echo "Check worker logs for STT execution details."
