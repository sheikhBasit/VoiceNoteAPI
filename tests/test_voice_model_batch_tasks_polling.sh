#!/bin/bash

# Improved Batch Testing Script with status polling and robust SQL
BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

VOICE_MODEL_DIR="/home/basitdev/Me/StudioProjects/voice_model"

echo "=== Robust Batch Testing: Voice Model & Task Extraction ==="

# 1. Get Token & Authenticate
echo "1. Getting auth token..."
UNIQUE_EMAIL="batch_tester_$(date +%s)@voicenote.ai"
SYNC_OUT=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Batch Tester\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"test_token\",
    \"device_id\": \"batch_device_002\",
    \"device_model\": \"curl-batch-tester-v2\",
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
declare -a NOTE_IDS
echo "2. Uploading batch files..."

# Test 1: Hybrid Pro Agent
FILE1="$VOICE_MODEL_DIR/hybrid_pro_processed_agent.wav"
echo "   -> Posting $FILE1 with docs..."
OUT1=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE1" \
  -F "stt_model=nova" \
  -F "document_urls=https://example.com/spec.pdf,https://notion.so/meeting_notes")
NOTE_IDS+=($(echo "$OUT1" | jq -r '.note_id'))

# Test 2: Clean STT
FILE2="$VOICE_MODEL_DIR/clean_for_stt.wav"
echo "   -> Posting $FILE2..."
OUT2=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE2" \
  -F "stt_model=whisper")
NOTE_IDS+=($(echo "$OUT2" | jq -r '.note_id'))

# Test 3: Final STT
FILE3="$VOICE_MODEL_DIR/final_stt_audio.wav"
echo "   -> Posting $FILE3 (Both)..."
OUT3=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE3" \
  -F "stt_model=both")
NOTE_IDS+=($(echo "$OUT3" | jq -r '.note_id'))

echo "3. Polling for completion..."
MAX_RETRIES=15
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    PENDING_COUNT=$(docker exec voicenote_db psql -U postgres -d voicenote -t -c "SELECT count(*) FROM notes WHERE id IN ('${NOTE_IDS[0]}', '${NOTE_IDS[1]}', '${NOTE_IDS[2]}') AND status IN ('PENDING', 'PROCESSING');" | xargs)
    if [ "$PENDING_COUNT" -eq "0" ]; then
        echo -e "${GREEN}✓ All notes processed!${NC}"
        break
    fi
    echo -e "${YELLOW}Waiting for $PENDING_COUNT notes... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 5
    ((RETRY_COUNT++))
done

# 4. Detailed Results
echo "4. Batch Results Dashboard:"
docker exec voicenote_db psql -U postgres -d voicenote -c "
SELECT 
    n.id, 
    LEFT(n.title, 30) as title_short, 
    n.status, 
    n.stt_model, 
    n.document_urls::text as docs,
    count(t.id) as tasks
FROM notes n
LEFT JOIN tasks t ON n.id = t.note_id
WHERE n.id IN ('${NOTE_IDS[0]}', '${NOTE_IDS[1]}', '${NOTE_IDS[2]}')
GROUP BY n.id, n.title, n.status, n.stt_model, n.document_urls, n.timestamp
ORDER BY n.timestamp ASC;"

echo ""
echo "5. Extracted Tasks Snapshot:"
docker exec voicenote_db psql -U postgres -d voicenote -c "
SELECT LEFT(description, 50) as task, priority, deadline 
FROM tasks 
WHERE note_id IN ('${NOTE_IDS[0]}', '${NOTE_IDS[1]}', '${NOTE_IDS[2]}')
LIMIT 10;"

echo ""
echo "6. Documentation Verification:"
SWAGGER_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
REDOC_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/redoc)
if [ "$SWAGGER_CODE" -eq "200" ]; then echo -e "   - Swagger UI: ${GREEN}200 OK${NC}"; else echo -e "   - Swagger UI: ${RED}$SWAGGER_CODE FAIL${NC}"; fi
if [ "$REDOC_CODE" -eq "200" ]; then echo -e "   - ReDoc UI: ${GREEN}200 OK${NC}"; else echo -e "   - ReDoc UI: ${RED}$REDOC_CODE FAIL${NC}"; fi

echo "=== Verification Complete ==="
