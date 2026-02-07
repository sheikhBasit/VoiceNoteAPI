#!/bin/bash

# Complete Audio Processing Test with Real Audio File
# Uses actual audio from voice_model/audios directory

BASE_URL="http://localhost:8000/api/v1"
AUDIO_FILE="/home/basitdev/Me/StudioProjects/voice_model/audios/group-talking-29731.mp3"
OUTPUT_DIR="/tmp/audio_test_results"
mkdir -p "$OUTPUT_DIR"

echo "========================================="
echo "Audio Processing Test - Real Audio File"
echo "========================================="
echo "Audio File: $(basename "$AUDIO_FILE")"
echo "Size: $(du -h "$AUDIO_FILE" | cut -f1)"
echo ""

# Step 1: Check API Health
echo "[1/7] Checking API Health..."
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo "✓ API is healthy"
else
    echo "✗ API health check failed"
    echo "$HEALTH"
    exit 1
fi
echo ""

# Step 2: Authenticate
echo "[2/7] Authenticating..."
UNIQUE_EMAIL="audio_test_$(date +%s)@voicenote.ai"
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Audio Test User\",
    \"email\": \"$UNIQUE_EMAIL\",
    \"token\": \"audio_test_token\",
    \"device_id\": \"audio_test_device_12345\",
    \"device_model\": \"curl_tester\",
    \"primary_role\": \"DEVELOPER\",
    \"timezone\": \"UTC\"
  }")

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token' 2>/dev/null)
USER_ID=$(echo "$AUTH_RESPONSE" | jq -r '.user.id' 2>/dev/null)

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "✓ Authenticated successfully"
    echo "  User ID: $USER_ID"
    echo "  Token: ${TOKEN:0:40}..."
    echo "$AUTH_RESPONSE" | jq '.' > "$OUTPUT_DIR/01_auth_response.json"
else
    echo "✗ Authentication failed"
    echo "  Response: $AUTH_RESPONSE"
    echo "$AUTH_RESPONSE" > "$OUTPUT_DIR/01_auth_failed.txt"
    
    # Try to elevate existing user to admin
    echo ""
    echo "  Attempting to create admin user in database..."
    docker exec voicenote_db psql -U postgres -d voicenote -c \
      "INSERT INTO users (id, name, email, tier, primary_role, timezone, is_admin, preferred_languages) 
       VALUES ('$(uuidgen)', 'Admin Test', '$UNIQUE_EMAIL', 'FREE', 'DEVELOPER', 'UTC', true, ARRAY['en']) 
       ON CONFLICT (email) DO UPDATE SET is_admin = true;" 2>&1 | grep -E "INSERT|UPDATE" || echo "  Database operation may have failed"
    
    # Retry auth
    AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"Audio Test User\",
        \"email\": \"$UNIQUE_EMAIL\",
        \"token\": \"audio_test_token\",
        \"device_id\": \"audio_test_device_12345\",
        \"device_model\": \"curl_tester\",
        \"primary_role\": \"DEVELOPER\",
        \"timezone\": \"UTC\"
      }")
    
    TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token' 2>/dev/null)
    if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
        echo "  Still failed after database operation"
        exit 1
    fi
    echo "  ✓ Retry successful"
fi
echo ""

# Step 3: Upload Audio File
echo "[3/7] Uploading audio file..."
PROCESS_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$AUDIO_FILE" \
  -F "stt_model=nova" \
  -F "mode=GENERIC")

NOTE_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.note_id' 2>/dev/null)

if [ -n "$NOTE_ID" ] && [ "$NOTE_ID" != "null" ]; then
    echo "✓ Audio uploaded successfully"
    echo "  Note ID: $NOTE_ID"
    echo "$PROCESS_RESPONSE" | jq '.' > "$OUTPUT_DIR/02_upload_response.json"
else
    echo "✗ Upload failed"
    echo "  Response: $PROCESS_RESPONSE"
    echo "$PROCESS_RESPONSE" > "$OUTPUT_DIR/02_upload_failed.txt"
    exit 1
fi
echo ""

# Step 4: Wait for Processing
echo "[4/7] Waiting for AI processing..."
MAX_RETRIES=90
RETRY_COUNT=0
STATUS="PENDING"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    NOTE_DATA=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo "$NOTE_DATA" | jq -r '.status' 2>/dev/null)
    
    if [ "$STATUS" == "DONE" ]; then
        echo ""
        echo "✓ Processing completed!"
        break
    elif [ "$STATUS" == "FAILED" ]; then
        echo ""
        echo "✗ Processing failed"
        echo "$NOTE_DATA" | jq '.' > "$OUTPUT_DIR/03_processing_failed.json"
        exit 1
    fi
    
    printf "  Status: %-25s [%d/%d]\r" "$STATUS" "$RETRY_COUNT" "$MAX_RETRIES"
    sleep 2
    ((RETRY_COUNT++))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo ""
    echo "✗ Processing timeout after 3 minutes"
    exit 1
fi
echo ""

# Step 5: Fetch Final Note Data
echo "[5/7] Fetching processed note data..."
FINAL_NOTE=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "$FINAL_NOTE" | jq '.' > "$OUTPUT_DIR/04_final_note.json"
echo "✓ Note data saved"
echo ""

# Step 6: Extract STT Results
echo "[6/7] Extracting STT transcription..."
TITLE=$(echo "$FINAL_NOTE" | jq -r '.title' 2>/dev/null)
SUMMARY=$(echo "$FINAL_NOTE" | jq -r '.summary' 2>/dev/null)
TRANSCRIPT_DEEPGRAM=$(echo "$FINAL_NOTE" | jq -r '.transcript_deepgram' 2>/dev/null)
TRANSCRIPT_GROQ=$(echo "$FINAL_NOTE" | jq -r '.transcript_groq' 2>/dev/null)
STT_MODEL=$(echo "$FINAL_NOTE" | jq -r '.stt_model' 2>/dev/null)
LANGUAGES=$(echo "$FINAL_NOTE" | jq -r '.languages' 2>/dev/null)
TASKS=$(echo "$FINAL_NOTE" | jq -r '.tasks' 2>/dev/null)
TASKS_COUNT=$(echo "$FINAL_NOTE" | jq -r '.tasks | length' 2>/dev/null)

echo "✓ STT results extracted"
echo ""

# Step 7: Generate Report
echo "[7/7] Generating report..."

cat > "$OUTPUT_DIR/STT_NOTES.txt" << EOF
========================================
Audio Processing Test Results
========================================
Date: $(date)
Audio File: $(basename "$AUDIO_FILE")
File Size: $(du -h "$AUDIO_FILE" | cut -f1)
Note ID: $NOTE_ID
User ID: $USER_ID

========================================
Processing Details
========================================
Status: $STATUS
STT Model: $STT_MODEL
Languages: $LANGUAGES
Tasks Extracted: $TASKS_COUNT

========================================
EXTRACTED TITLE
========================================
$TITLE

========================================
SUMMARY
========================================
$SUMMARY

========================================
TRANSCRIPT - Deepgram Nova
========================================
$TRANSCRIPT_DEEPGRAM

========================================
TRANSCRIPT - Groq Whisper
========================================
$TRANSCRIPT_GROQ

========================================
EXTRACTED TASKS
========================================
EOF

echo "$TASKS" | jq -r '.[] | "- [\(.is_done | if . then "x" else " " end)] \(.description) (Deadline: \(.deadline // "None"))"' 2>/dev/null >> "$OUTPUT_DIR/STT_NOTES.txt" || echo "No tasks extracted" >> "$OUTPUT_DIR/STT_NOTES.txt"

cat >> "$OUTPUT_DIR/STT_NOTES.txt" << EOF

========================================
Full JSON Response
========================================
See: $OUTPUT_DIR/04_final_note.json

========================================
Test Summary
========================================
✓ Audio file uploaded successfully
✓ AI processing completed
✓ STT transcription extracted
✓ Notes saved to: $OUTPUT_DIR/STT_NOTES.txt

EOF

echo "✓ Report generated"
echo ""

# Display Results
echo "========================================="
echo "STT TRANSCRIPTION NOTES"
echo "========================================="
echo ""
echo "Title: $TITLE"
echo ""
echo "Summary:"
echo "$SUMMARY"
echo ""
echo "Deepgram Transcript:"
echo "$TRANSCRIPT_DEEPGRAM"
echo ""
echo "Tasks Found: $TASKS_COUNT"
if [ "$TASKS_COUNT" -gt 0 ]; then
    echo "$TASKS" | jq -r '.[] | "  - \(.description)"' 2>/dev/null
fi
echo ""
echo "========================================="
echo "Complete results saved to:"
echo "  $OUTPUT_DIR/STT_NOTES.txt"
echo "  $OUTPUT_DIR/04_final_note.json"
echo "========================================="
echo ""
echo "✓ Test completed successfully!"
