#!/bin/bash

# Batch Testing Script for voice_model audio files and task extraction
BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

VOICE_MODEL_DIR="/home/basitdev/Me/StudioProjects/voice_model"

echo "=== Batch Testing Voice Model Files & Task Extraction ==="

# 1. Get Token & Authenticate
echo "1. Getting auth token..."
UNIQUE_EMAIL="batch_tester_$(date +%s)@voicenote.ai"
SYNC_OUT=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Batch Tester\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"test_token\",
    \"device_id\": \"batch_device_001\",
    \"device_model\": \"curl-batch-tester\",
    \"primary_role\": \"DEVELOPER\",
    \"timezone\": \"UTC\"
  }")
TOKEN=$(echo "$SYNC_OUT" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo -e "${RED}✗ Failed to get token${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Token retrieved${NC}"

# Elevate to Admin
docker exec voicenote_db psql -U postgres -d voicenote -c "UPDATE users SET is_admin = true WHERE email = '$UNIQUE_EMAIL';" > /dev/null
echo "✓ Elevated $UNIQUE_EMAIL to admin"

# 2. Upload Batch
echo "2. Uploading batch files..."

# Test 1: Hybrid Pro Agent (Nova)
FILE1="$VOICE_MODEL_DIR/hybrid_pro_processed_agent.wav"
echo "   -> Processing $FILE1 with docs..."
UPLOAD_1=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE1" \
  -F "stt_model=nova" \
  -F "document_urls=https://example.com/spec.pdf,https://notion.so/meeting_notes")

# Test 2: Clean STT (Whisper)
FILE2="$VOICE_MODEL_DIR/clean_for_stt.wav"
echo "   -> Processing $FILE2..."
UPLOAD_2=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE2" \
  -F "stt_model=whisper")

# Test 3: Final STT (Both)
FILE3="$VOICE_MODEL_DIR/final_stt_audio.wav"
echo "   -> Processing $FILE3 (Both)..."
UPLOAD_3=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE3" \
  -F "stt_model=both")

echo "3. Waiting for AI processing (30s)..."
sleep 30

# 4. Results check via DB
echo "4. Querying results from database..."
docker exec voicenote_db psql -U postgres -d voicenote -c "
SELECT 
    n.id, 
    n.title, 
    n.status, 
    n.stt_model, 
    array_to_string(n.document_urls, ',') as docs,
    count(t.id) as task_count
FROM notes n
LEFT JOIN tasks t ON n.id = t.note_id
WHERE n.user_id = (SELECT id FROM users WHERE email = '$UNIQUE_EMAIL')
GROUP BY n.id, n.title, n.status, n.stt_model, n.document_urls, n.timestamp
ORDER BY n.timestamp DESC;"

echo ""
echo "5. Verifying Tasks for the latest note..."
LATEST_NOTE_ID=$(docker exec voicenote_db psql -U postgres -d voicenote -t -c "SELECT id FROM notes WHERE user_id = (SELECT id FROM users WHERE email = '$UNIQUE_EMAIL') ORDER BY timestamp DESC LIMIT 1;" | xargs)
if [ -n "$LATEST_NOTE_ID" ]; then
    docker exec voicenote_db psql -U postgres -d voicenote -c "SELECT description, priority, deadline FROM tasks WHERE note_id = '$LATEST_NOTE_ID';"
fi

echo ""
echo "6. Testing Docs Endpoint (API Docs)..."
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
REDOC_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/redoc)
echo "   - Swagger UI: $DOCS_STATUS"
echo "   - ReDoc UI: $REDOC_STATUS"

echo "=== Batch Verification Complete ==="
