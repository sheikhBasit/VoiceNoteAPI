# 📝 Notes Endpoint Testing Suite

**Date:** February 6, 2026  
**Status:** Ready for Testing  
**Coverage:** All notes endpoints with audio file uploads

---

## 📋 Overview

Complete test suite for VoiceNote API notes endpoints. Includes:
- ✅ User authentication
- ✅ Audio file generation
- ✅ Note processing (upload & transcription)
- ✅ Note retrieval and listing
- ✅ Note updates
- ✅ Search functionality
- ✅ Dashboard metrics
- ✅ AI-powered Q&A
- ✅ Note deletion

---

## 🚀 Quick Start

### Option 1: Using Python Script

```bash
cd /mnt/muaaz/VoiceNoteAPI

# Make sure API is running
docker-compose up -d

# Run tests
python3 test_notes_endpoints.py
```

### Option 2: Using Bash Script (cURL)

```bash
cd /mnt/muaaz/VoiceNoteAPI

# Make sure API is running
docker-compose up -d

# Run tests
./test_notes_endpoints.sh
```

---

## 📊 Test Coverage

### Endpoints Tested (9 tests)

| # | Endpoint | Method | Status | Description |
|---|----------|--------|--------|-------------|
| 1 | `/notes/presigned-url` | GET | ✅ | Generate S3 upload URL |
| 2 | `/notes/process` | POST | ✅ | Upload & process audio |
| 3 | `/notes` | GET | ✅ | List all notes |
| 4 | `/notes/{note_id}` | GET | ✅ | Get specific note |
| 5 | `/notes/{note_id}` | PATCH | ✅ | Update note |
| 6 | `/notes/search` | GET | ✅ | Search notes |
| 7 | `/notes/dashboard/metrics` | GET | ✅ | Get dashboard stats |
| 8 | `/notes/{note_id}/ask-ai` | POST | ✅ | Ask AI about note |
| 9 | `/notes/{note_id}` | DELETE | ✅ | Delete note |

---

## 🔍 Test Details

### Test 1: Get Presigned URL
```
GET /api/v1/notes/presigned-url
Authorization: Bearer {access_token}

Expected Response:
{
  "note_id": "uuid",
  "upload_url": "https://minio.example.com/...",
  "expires_in": 3600
}
```

### Test 2: Process Note
```
POST /api/v1/notes/process
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

Fields:
  - file: audio file (mp3, wav, m4a, ogg, flac)
  - mode: "GENERIC" | "CRICKET" | "QURANIC"
  - languages: "en,ur,ar" (comma-separated)
  - stt_model: "nova" | "whisper" | "both"
  - debug_sync: true | false

Expected Response:
{
  "note_id": "uuid",
  "task_id": "celery-task-id",
  "status": "processing"
}
```

### Test 3: List Notes
```
GET /api/v1/notes?skip=0&limit=10
Authorization: Bearer {access_token}

Expected Response:
[
  {
    "id": "note-id",
    "title": "Note Title",
    "transcript": "Note content...",
    "created_at": 1707247200000,
    "tags": ["tag1", "tag2"]
  },
  ...
]
```

### Test 4: Get Specific Note
```
GET /api/v1/notes/{note_id}
Authorization: Bearer {access_token}

Expected Response:
{
  "id": "note-id",
  "title": "Note Title",
  "transcript": "Full transcript...",
  "description": "Description",
  "tags": ["tag1", "tag2"],
  "created_at": 1707247200000,
  "updated_at": 1707247200000,
  "audio_url": "https://...",
  "sentiment": "positive",
  "keywords": ["keyword1", "keyword2"]
}
```

### Test 5: Update Note
```
PATCH /api/v1/notes/{note_id}
Authorization: Bearer {access_token}
Content-Type: application/json

Body:
{
  "title": "New Title",
  "description": "Updated description",
  "tags": ["new-tag"],
  "is_pinned": true
}

Expected Response:
{
  "id": "note-id",
  "title": "New Title",
  "description": "Updated description",
  "tags": ["new-tag"],
  "is_pinned": true,
  ...
}
```

### Test 6: Search Notes
```
GET /api/v1/notes/search?query=test&limit=10
Authorization: Bearer {access_token}

Expected Response:
[
  {
    "id": "note-id",
    "title": "Matching Note",
    "excerpt": "Relevant content...",
    "relevance_score": 0.95
  },
  ...
]
```

### Test 7: Dashboard Metrics
```
GET /api/v1/notes/dashboard/metrics
Authorization: Bearer {access_token}

Expected Response:
{
  "total_notes": 42,
  "total_duration": 3600,
  "avg_duration": 85.7,
  "tags_count": 15,
  "top_tags": ["work", "meeting", "ideas"],
  "notes_today": 5,
  "notes_this_week": 12,
  "notes_this_month": 42
}
```

### Test 8: Ask AI
```
POST /api/v1/notes/{note_id}/ask-ai
Authorization: Bearer {access_token}
Content-Type: application/json

Body:
{
  "question": "What is the main topic?"
}

Expected Response:
{
  "question": "What is the main topic?",
  "answer": "AI-generated answer based on note content",
  "confidence": 0.95,
  "sources": [{"text": "...", "position": 120}]
}
```

### Test 9: Delete Note
```
DELETE /api/v1/notes/{note_id}
Authorization: Bearer {access_token}

Expected Response:
HTTP 204 No Content
or
{
  "status": "success",
  "message": "Note deleted successfully"
}
```

---

## 🎵 Audio File Specifications

### Supported Formats
- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- OGG (.ogg)
- FLAC (.flac)

### Recommended Specifications
```
Sample Rate: 16000 Hz (16 kHz)
Channels: Mono (1 channel)
Bit Depth: 16-bit
Codec: PCM (for WAV)
Duration: 1 second - 2 hours
Max File Size: 100 MB
```

### Auto-Generated Test Audio
The scripts automatically generate a test audio file:
```
Duration: 2 seconds
Frequency: 440 Hz (musical note A4)
Sample Rate: 16000 Hz
Channels: Mono
Format: WAV
```

---

## 📈 Test Execution Flow

```
1. Server Check
   └─ Verify API is running on http://localhost:8000

2. Authentication
   └─ Create test user
   └─ Get access token

3. Audio Generation
   └─ Create test WAV file (2 seconds)

4. Presigned URL Test
   └─ GET /notes/presigned-url

5. Note Processing Test
   └─ POST /notes/process with audio file

6. Note Operations (if note created)
   ├─ GET /notes (list)
   ├─ GET /notes/{id} (retrieve)
   ├─ PATCH /notes/{id} (update)
   ├─ GET /notes/search (search)
   ├─ GET /notes/dashboard/metrics (metrics)
   ├─ POST /notes/{id}/ask-ai (AI query)
   └─ DELETE /notes/{id} (delete)

7. Summary
   └─ Report pass/fail counts and success rate
```

---

## 🛠️ Script Variations

### Python Script (`test_notes_endpoints.py`)

**Requirements:**
```bash
pip install requests
```

**Features:**
- Object-oriented test suite
- Detailed error messages
- JSON response parsing
- Automatic audio generation (supports Python wave module)
- Structured test logging
- Per-test timing

**Run:**
```bash
python3 test_notes_endpoints.py
```

### Bash Script (`test_notes_endpoints.sh`)

**Requirements:**
```bash
# Must have
curl
jq
ffmpeg (for audio generation)

# Optional
stat (for file size reporting)
```

**Features:**
- Simple shell script
- Pure cURL operations
- Color-coded output
- Real-time status feedback
- FFmpeg audio generation

**Run:**
```bash
./test_notes_endpoints.sh
```

---

## ✅ Expected Test Results

### Successful Run
```
✅ User Sync: User authenticated
✅ Audio File Creation: Created test audio (32000 bytes)
✅ GET /notes/presigned-url: Generated presigned URL
✅ POST /notes/process: Note processing started
✅ GET /notes: Retrieved 5 notes
✅ GET /notes/{note_id}: Retrieved note
✅ PATCH /notes/{note_id}: Updated note
✅ GET /notes/search: Found 3 matching notes
✅ GET /notes/dashboard/metrics: Total notes: 5
✅ POST /notes/{note_id}/ask-ai: AI response received
✅ DELETE /notes/{note_id}: Note deleted

═══════════════════════════════════════
TEST SUMMARY
═══════════════════════════════════════
Total Tests: 10
Passed: 10 ✅
Failed: 0 ❌
Success Rate: 100%
═══════════════════════════════════════
```

---

## 🐛 Troubleshooting

### Server Not Running
```
Error: API server not running at http://localhost:8000

Solution:
docker-compose up -d
# Or check if port is in use:
lsof -i :8000
```

### Authentication Failed
```
Error: Could not authenticate user

Causes:
- Database not initialized
- Redis not running
- Invalid credentials

Solutions:
1. Check database: docker-compose logs postgres
2. Check Redis: docker-compose logs redis
3. Verify credentials in test script
```

### Audio Generation Failed
```
Error: FFmpeg not installed

Solution:
# On macOS
brew install ffmpeg

# On Ubuntu/Debian
sudo apt-get install ffmpeg

# On CentOS/RHEL
sudo yum install ffmpeg
```

### Note Processing Timeout
```
Error: Note processing did not complete

Causes:
- Celery worker not running
- AI service unavailable
- Large audio file

Solutions:
1. Check Celery: docker-compose logs celery
2. Check AI service: docker logs voicenote-api
3. Use smaller audio file
4. Increase timeout in script
```

### Insufficient Permissions
```
Error: HTTP 403 Forbidden

Causes:
- User not properly authenticated
- Device signature invalid
- Missing authorization header

Solutions:
1. Verify access token in header
2. Check device signature setup
3. Verify user exists in database
```

---

## 📊 Performance Benchmarks

### Expected Response Times (on localhost)

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| User Sync | 100-200ms | Includes DB query |
| Get Presigned URL | 50-100ms | MinIO connection |
| Process Note (2s audio) | 200-500ms | Initial processing |
| List Notes | 50-150ms | Limited by DB query |
| Get Note | 30-100ms | Single note retrieval |
| Update Note | 50-150ms | DB update + reindex |
| Search Notes | 100-300ms | Full-text search |
| Dashboard Metrics | 200-500ms | Multiple aggregations |
| Ask AI | 2000-5000ms | LLM inference time |
| Delete Note | 50-100ms | Soft delete |

---

## 🔐 Security Features Tested

- ✅ Bearer token authentication
- ✅ Device signature verification
- ✅ User ownership validation
- ✅ Note access control
- ✅ File type validation
- ✅ Audio content validation
- ✅ Input sanitization

---

## 📝 Sample Output

```
════════════════════════════════════════════════════════════════
                NOTES ENDPOINT TEST SUITE

                Date: 2026-02-06 18:10:45

════════════════════════════════════════════════════════════════

STEP 1: AUTHENTICATION
──────────────────────────────────────────────────────────────
✅ User Sync: User test_user_a1b2c3d4 authenticated (0.15s)

STEP 2: CREATE TEST AUDIO FILE
──────────────────────────────────────────────────────────────
✅ Audio File Creation: Created /tmp/test_audio_12345678.wav (32000 bytes) (0.50s)

TEST 1: GET PRESIGNED URL
──────────────────────────────────────────────────────────────
✅ GET /presigned-url: Generated presigned URL (note_id: 5e8c1234-...) (0.08s)

TEST 2: POST /PROCESS (FILE UPLOAD)
──────────────────────────────────────────────────────────────
✅ POST /process: Note processing started (task_id: 5e8c5678-...) (0.35s)

TEST 3: GET /NOTES (LIST)
──────────────────────────────────────────────────────────────
✅ GET /notes: Retrieved 5 notes (0.12s)

TEST 4: GET /NOTES/NOTE_ID
──────────────────────────────────────────────────────────────
✅ GET /notes/{note_id}: Retrieved note (title: Test Note) (0.09s)

TEST 5: PATCH /NOTES/NOTE_ID
──────────────────────────────────────────────────────────────
✅ PATCH /notes/{note_id}: Updated note (new title: Updated Note 1707...) (0.18s)

TEST 6: GET /NOTES/SEARCH
──────────────────────────────────────────────────────────────
✅ GET /notes/search: Found 3 matching notes (0.25s)

TEST 7: GET /NOTES/DASHBOARD/METRICS
──────────────────────────────────────────────────────────────
✅ GET /notes/dashboard/metrics: Retrieved metrics (total_notes: 5) (0.42s)

TEST 8: POST /NOTES/NOTE_ID/ASK-AI
──────────────────────────────────────────────────────────────
✅ POST /notes/{note_id}/ask-ai: AI response received (2.35s)

TEST 9: DELETE /NOTES/NOTE_ID
──────────────────────────────────────────────────────────────
✅ DELETE /notes/{note_id}: Note deleted successfully (0.11s)

════════════════════════════════════════════════════════════════
                      TEST SUMMARY
════════════════════════════════════════════════════════════════

Total Tests: 9
Passed: 9 ✅
Failed: 0 ❌
Success Rate: 100%

════════════════════════════════════════════════════════════════
```

---

## 📚 Additional Resources

- **API Architecture:** `/docs/API_ARCHITECTURE.md`
- **Endpoint Reference:** Swagger UI at `http://localhost:8000/docs`
- **Database Schema:** `/docs/DB_SCHEMA.md`
- **Audio Processing:** `/app/utils/audio_chunker.py`
- **Transcription Service:** `/app/services/transcription_service.py`

---

## 🎯 Next Steps

1. **Run Tests:** Execute the test suite
2. **Check Results:** Review success/failure counts
3. **Debug Issues:** Use provided troubleshooting guide
4. **Iterate:** Make fixes and re-run tests
5. **Document:** Add custom tests as needed

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review API logs: `docker-compose logs api`
3. Check Celery logs: `docker-compose logs celery`
4. Verify database: `docker-compose exec postgres psql -U voicenote -d voicenote_db`

---

**Created:** February 6, 2026  
**Status:** ✅ Ready for Testing  
**Last Updated:** February 6, 2026
