#!/bin/bash

# Audio Processing Test with Admin User
# Uses admin@voicenote.ai credentials

BASE_URL="http://localhost:8000/api/v1"
AUDIO_FILE="/home/basitdev/Me/StudioProjects/voice_model/audios/group-talking-29731.mp3"
OUTPUT_DIR="/tmp/audio_test_results"
mkdir -p "$OUTPUT_DIR"

echo "========================================="
echo "Audio Processing Test - Admin User"
echo "========================================="
echo "Audio File: $(basename "$AUDIO_FILE")"
echo "Size: $(du -h "$AUDIO_FILE" | cut -f1)"
echo "User: admin@voicenote.ai"
echo ""

# Authenticate as admin
echo "[1/5] Authenticating as admin..."
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/users/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin User",
    "email": "admin@voicenote.ai",
    "token": "admin_token",
    "device_id": "admin_device_12345",
    "device_model": "curl_admin",
    "primary_role": "DEVELOPER",
    "timezone": "UTC"
  }')

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "✓ Authenticated as admin"
    echo "  Token: ${TOKEN:0:40}..."
else
    echo "✗ Authentication failed: $AUTH_RESPONSE"
    exit 1
fi
echo ""

# Upload audio
echo "[2/5] Uploading audio file..."
PROCESS_RESPONSE=$(curl -s -X POST "$BASE_URL/notes/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$AUDIO_FILE" \
  -F "stt_model=nova" \
  -F "mode=GENERIC")

NOTE_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.note_id' 2>/dev/null)

if [ -n "$NOTE_ID" ] && [ "$NOTE_ID" != "null" ]; then
    echo "✓ Audio uploaded - Note ID: $NOTE_ID"
else
    echo "✗ Upload failed: $PROCESS_RESPONSE"
    exit 1
fi
echo ""

# Wait for processing
echo "[3/5] Waiting for AI processing..."
MAX_RETRIES=90
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    NOTE_DATA=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo "$NOTE_DATA" | jq -r '.status' 2>/dev/null)
    
    if [ "$STATUS" == "DONE" ]; then
        echo "✓ Processing completed!"
        break
    elif [ "$STATUS" == "FAILED" ]; then
        echo "✗ Processing failed"
        exit 1
    fi
    
    printf "  Status: %-25s [%d/%d]\r" "$STATUS" "$RETRY_COUNT" "$MAX_RETRIES"
    sleep 2
    ((RETRY_COUNT++))
done
echo ""
echo ""

# Extract results
echo "[4/5] Extracting STT notes..."
FINAL_NOTE=$(curl -s -X GET "$BASE_URL/notes/$NOTE_ID" -H "Authorization: Bearer $TOKEN")

TITLE=$(echo "$FINAL_NOTE" | jq -r '.title' 2>/dev/null)
SUMMARY=$(echo "$FINAL_NOTE" | jq -r '.summary' 2>/dev/null)
TRANSCRIPT=$(echo "$FINAL_NOTE" | jq -r '.transcript_deepgram' 2>/dev/null)
TASKS=$(echo "$FINAL_NOTE" | jq -r '.tasks' 2>/dev/null)

echo "$FINAL_NOTE" | jq '.' > "$OUTPUT_DIR/note_$NOTE_ID.json"
echo "✓ Results saved"
echo ""

# Display results
echo "[5/5] STT Transcription Notes"
echo "========================================="
echo ""
echo "TITLE:"
echo "$TITLE"
echo ""
echo "SUMMARY:"
echo "$SUMMARY"
echo ""
echo "TRANSCRIPT:"
echo "$TRANSCRIPT"
echo ""
echo "TASKS:"
echo "$TASKS" | jq -r '.[] | "  - \(.description)"' 2>/dev/null || echo "  No tasks extracted"
echo ""
echo "========================================="
echo "Full JSON: $OUTPUT_DIR/note_$NOTE_ID.json"
echo "========================================="
