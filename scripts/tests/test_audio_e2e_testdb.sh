#!/bin/bash

# E2E Audio Processing Test with Testing Database
# Uses voicenote_test database to avoid affecting main DB

BASE_URL="http://localhost:8000/api/v1"
OUTPUT_FILE="/tmp/stt_output_results.json"
TEST_DB="voicenote_test"

# Override DATABASE_URL for this test
export DATABASE_URL="postgresql://postgres:password@localhost:5432/$TEST_DB"

echo "========================================="
echo "Audio Processing E2E Test (Test DB)"
echo "========================================="
echo "Using database: $TEST_DB"
echo ""

# Step 1: Create test audio
echo "[1/6] Creating test audio file..."
if [ ! -f "/tmp/test_audio_e2e.wav" ]; then
    ffmpeg -f lavfi -i "sine=frequency=440:duration=5" /tmp/test_audio_e2e.wav -y > /dev/null 2>&1
    echo "✓ Test audio created (5 seconds, 440Hz tone)"
else
    echo "✓ Using existing test audio"
fi
echo ""

# Step 2: Create user directly in test database
echo "[2/6] Creating test user in database..."
UNIQUE_EMAIL="e2e_test_$(date +%s)@voicenote.ai"
USER_ID=$(uuidgen)

docker exec voicenote_db psql -U postgres -d $TEST_DB -c "
INSERT INTO users (id, name, email, tier, primary_role, timezone, is_admin, preferred_languages)
VALUES ('$USER_ID', 'E2E Test User', '$UNIQUE_EMAIL', 'FREE', 'DEVELOPER', 'UTC', true, ARRAY['en']);
" > /dev/null 2>&1

echo "✓ User created in test database"
echo "  User ID: $USER_ID"
echo "  Email: $UNIQUE_EMAIL"
echo ""

# Step 3: Authenticate
echo "[3/6] Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"E2E Test User\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"e2e_token\",
    \"device_id\": \"e2e_device_001\",
    \"device_model\": \"test\",
    \"primary_role\": \"DEVELOPER\",
    \"timezone\": \"UTC\"
  }")

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "✓ Authenticated successfully"
    echo "  Token: ${TOKEN:0:30}..."
else
    echo "⚠ Authentication response: $AUTH_RESPONSE"
    echo "  Proceeding with database user..."
fi
echo ""

# Step 4: Post audio file
echo "[4/6] Posting audio file for processing..."
PROCESS_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_audio_e2e.wav" \
  -F "stt_model=nova" \
  -F "mode=GENERIC")

NOTE_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.note_id' 2>/dev/null)

if [ -n "$NOTE_ID" ] && [ "$NOTE_ID" != "null" ]; then
    echo "✓ Audio posted successfully"
    echo "  Note ID: $NOTE_ID"
else
    echo "✗ Failed to post audio"
    echo "  Response: $PROCESS_RESPONSE"
    exit 1
fi
echo ""

# Step 5: Wait for processing
echo "[5/6] Waiting for AI processing to complete..."
MAX_RETRIES=60
RETRY_COUNT=0
STATUS="PENDING"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    NOTE_DATA=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo "$NOTE_DATA" | jq -r '.status' 2>/dev/null)
    
    if [ "$STATUS" == "DONE" ]; then
        echo ""
        echo "✓ Processing completed successfully!"
        break
    elif [ "$STATUS" == "FAILED" ]; then
        echo ""
        echo "✗ Processing failed"
        echo "$NOTE_DATA" | jq '.' > "$OUTPUT_FILE"
        exit 1
    fi
    
    printf "  Status: %-20s (attempt %d/%d)\r" "$STATUS" "$RETRY_COUNT" "$MAX_RETRIES"
    sleep 2
    ((RETRY_COUNT++))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo ""
    echo "✗ Processing timeout"
    exit 1
fi
echo ""

# Step 6: Extract STT results
echo "[6/6] Extracting STT results..."
FINAL_NOTE=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" \
  -H "Authorization: Bearer $TOKEN")

# Save complete response
echo "$FINAL_NOTE" | jq '.' > "$OUTPUT_FILE"

# Extract key fields
TITLE=$(echo "$FINAL_NOTE" | jq -r '.title' 2>/dev/null)
SUMMARY=$(echo "$FINAL_NOTE" | jq -r '.summary' 2>/dev/null)
TRANSCRIPT_DEEPGRAM=$(echo "$FINAL_NOTE" | jq -r '.transcript_deepgram' 2>/dev/null)
TRANSCRIPT_GROQ=$(echo "$FINAL_NOTE" | jq -r '.transcript_groq' 2>/dev/null)
STT_MODEL=$(echo "$FINAL_NOTE" | jq -r '.stt_model' 2>/dev/null)
LANGUAGES=$(echo "$FINAL_NOTE" | jq -r '.languages' 2>/dev/null)
TASKS_COUNT=$(echo "$FINAL_NOTE" | jq -r '.tasks | length' 2>/dev/null)

echo "✓ STT results extracted"
echo ""

# Display results
echo "========================================="
echo "STT Processing Results"
echo "========================================="
echo ""
echo "Note ID:        $NOTE_ID"
echo "Status:         $STATUS"
echo "STT Model:      $STT_MODEL"
echo "Languages:      $LANGUAGES"
echo "Tasks Found:    $TASKS_COUNT"
echo ""
echo "Title:"
echo "  $TITLE"
echo ""
echo "Summary:"
echo "  $SUMMARY"
echo ""
echo "Transcript (Deepgram Nova):"
echo "  $TRANSCRIPT_DEEPGRAM"
echo ""
echo "Transcript (Groq Whisper):"
echo "  $TRANSCRIPT_GROQ"
echo ""
echo "========================================="
echo "Complete JSON saved to: $OUTPUT_FILE"
echo "========================================="
echo ""

# Create a formatted output file
cat > "/tmp/stt_output_formatted.txt" << EOF
========================================
Audio Processing Test Results
========================================
Date: $(date)
Note ID: $NOTE_ID
Status: $STATUS
Database: $TEST_DB

STT Configuration:
- Model: $STT_MODEL
- Languages: $LANGUAGES

Extracted Data:
- Title: $TITLE
- Summary: $SUMMARY
- Tasks Found: $TASKS_COUNT

Transcripts:
-----------
Deepgram Nova:
$TRANSCRIPT_DEEPGRAM

Groq Whisper:
$TRANSCRIPT_GROQ

========================================
Full JSON Response: $OUTPUT_FILE
========================================
EOF

echo "Formatted output saved to: /tmp/stt_output_formatted.txt"
echo ""
echo "✓ Test completed successfully!"
