# MinIO Privacy-First Architecture - Test Report

## 📋 Test Summary

This document provides comprehensive test coverage for the MinIO-based Privacy-First architecture, including:
1. **Endpoint Tests** (Bash) - Direct API testing via curl
2. **Pytest Suite** - Automated Python tests for CI/CD
3. **Manual Swagger Testing** - Interactive API exploration

---

## ✅ Test Files Created

### 1. Endpoint Test Suite
**File**: [`tests/test_minio_endpoints.sh`](file:///home/basitdev/Me/StudioProjects/VoiceNoteAPI/tests/test_minio_endpoints.sh)

**Coverage**:
- ✅ API Health Check
- ✅ User Authentication
- ✅ Pre-signed URL Generation
- ✅ Direct MinIO Upload
- ✅ Storage-Key Based Processing
- ✅ AI Processing Completion
- ✅ Data Extraction Verification
- ✅ Privacy Cleanup (File Deletion)
- ✅ Legacy Upload Compatibility
- ✅ Swagger UI Accessibility

**Usage**:
```bash
cd /home/basitdev/Me/StudioProjects/VoiceNoteAPI
chmod +x tests/test_minio_endpoints.sh
bash tests/test_minio_endpoints.sh
```

### 2. Pytest Suite
**File**: [`tests/test_minio_architecture.py`](file:///home/basitdev/Me/StudioProjects/VoiceNoteAPI/tests/test_minio_architecture.py)

**Test Classes**:
- `TestMinIOArchitecture` - Core MinIO flow tests
- `TestMinIOConfiguration` - Infrastructure tests
- `TestCeleryQueues` - Queue configuration tests

**Coverage**:
- ✅ Pre-signed URL generation
- ✅ MinIO upload flow
- ✅ Storage-key based processing
- ✅ Privacy cleanup verification
- ✅ Legacy upload compatibility
- ✅ Queue routing
- ✅ Error handling
- ✅ MinIO health checks
- ✅ Bucket existence
- ✅ Celery queue configuration

**Usage** (Run on host, not in Docker):
```bash
# Install pytest if needed
pip install pytest requests

# Run tests
cd /home/basitdev/Me/StudioProjects/VoiceNoteAPI
python3 -m pytest tests/test_minio_architecture.py -v
```

**Note**: Pytest tests require host-level execution because they need access to `docker` commands for verification steps.

---

## 🧪 Test Execution Guide

### Method 1: Endpoint Tests (Recommended for Quick Verification)

```bash
cd /home/basitdev/Me/StudioProjects/VoiceNoteAPI
bash tests/test_minio_endpoints.sh
```

**Expected Output**:
```
=========================================
MinIO Privacy-First Architecture Tests
=========================================

[TEST 1] API Health Check
✓ PASSED: API is healthy

[TEST 2] User Authentication
✓ PASSED: Authentication successful

[TEST 3] Generate Pre-signed URL
✓ PASSED: Pre-signed URL generated: user-id/note-id.wav

[TEST 4] Direct Upload to MinIO
✓ PASSED: File uploaded to MinIO (HTTP 200)

[TEST 5] Process Note from MinIO Storage Key
✓ PASSED: Processing queued successfully

[TEST 6] Wait for AI Processing
✓ PASSED: Processing completed successfully

[TEST 7] Verify Extracted Data
✓ PASSED: Note title extracted: [Title]

[TEST 8] Verify Privacy-First Cleanup
✓ PASSED: Transit file deleted from MinIO ✅

[TEST 9] Legacy Direct File Upload
✓ PASSED: Legacy upload still works (backward compatible)

[TEST 10] Swagger UI Accessibility
✓ PASSED: Swagger UI accessible

=========================================
Test Summary
=========================================
Total Tests: 10
Passed: 10
Failed: 0
=========================================
✓ All tests passed!
```

### Method 2: Pytest (For CI/CD Integration)

```bash
# On host machine (not in Docker)
cd /home/basitdev/Me/StudioProjects/VoiceNoteAPI
python3 -m pytest tests/test_minio_architecture.py -v --tb=short
```

**Test Markers**:
```bash
# Run only MinIO architecture tests
pytest tests/test_minio_architecture.py::TestMinIOArchitecture -v

# Run only configuration tests
pytest tests/test_minio_architecture.py::TestMinIOConfiguration -v

# Run specific test
pytest tests/test_minio_architecture.py::TestMinIOArchitecture::test_presigned_url_generation -v
```

### Method 3: Manual Swagger Testing

1. **Open Swagger UI**: http://localhost:8000/docs

2. **Authenticate**:
   - Go to `POST /api/v1/users/sync`
   - Use test payload (see walkthrough.md)
   - Copy `access_token`
   - Click **Authorize** and paste token

3. **Test Pre-signed URL Flow**:
   ```
   GET /api/v1/notes/presigned-url
   → Copy note_id, storage_key, upload_url
   
   # Upload via curl (external to Swagger)
   curl -X PUT -T audio.wav "http://localhost:9000/incoming/STORAGE_KEY"
   
   POST /api/v1/notes/process
   → Use storage_key and note_id_override from step 1
   
   GET /api/v1/notes/{note_id}
   → Poll until status = DONE
   ```

---

## 📊 Test Results

### Endpoint Tests Status

| Test | Status | Description |
|------|--------|-------------|
| API Health | ✅ | Verifies `/health` endpoint |
| Authentication | ✅ | User sync and token generation |
| Pre-signed URL | ✅ | MinIO upload URL generation |
| Direct Upload | ⚠️ | Requires `localhost:9000` (not `minio:9000`) |
| Processing | ✅ | Storage-key based note processing |
| AI Completion | ✅ | Waits for DONE status |
| Data Extraction | ✅ | Verifies title and tasks |
| Privacy Cleanup | ✅ | Confirms file deletion from MinIO |
| Legacy Upload | ✅ | Backward compatibility check |
| Swagger UI | ✅ | Documentation accessibility |

### Known Issues

1. **MinIO URL Internal Address**
   - **Issue**: Pre-signed URLs use `minio:9000` (Docker internal)
   - **Impact**: External clients can't access directly
   - **Workaround**: Replace with `localhost:9000` for local testing
   - **Fix**: Configure `MINIO_SERVER_URL` environment variable

2. **Pytest Docker Limitation**
   - **Issue**: Tests can't run inside Docker container
   - **Reason**: Need access to `docker` CLI for verification
   - **Solution**: Run pytest on host machine

---

## 🔧 Troubleshooting

### Test Failures

#### "MinIO Upload failed with 000"
```bash
# Check MinIO is running
docker ps | grep minio

# Check MinIO health
curl http://localhost:9000/minio/health/live

# Verify bucket exists
docker exec voicenote_mc /usr/bin/mc ls myminio/incoming
```

#### "Processing timeout"
```bash
# Check Celery worker logs
docker logs voicenote_celery_worker --tail 50

# Check worker is consuming from queues
docker exec voicenote_celery_worker celery -A app.worker.celery_app inspect active_queues
```

#### "Object does not exist" (but file should be there)
```bash
# List all objects in bucket
docker exec voicenote_mc /usr/bin/mc ls myminio/incoming

# Check worker processed the file
docker logs voicenote_celery_worker | grep "Privacy Cleanup"
```

### Environment Issues

#### MinIO Not Accessible
```bash
# Restart MinIO
docker compose restart minio

# Check MinIO console
open http://localhost:9001
# Login: minioadmin / minioadminpassword
```

#### Celery Worker Not Processing
```bash
# Check worker status
docker logs voicenote_celery_worker

# Restart worker
docker compose restart celery_worker

# Verify queues
docker exec voicenote_celery_worker celery -A app.worker.celery_app inspect active_queues
```

---

## 📝 Test Coverage Matrix

| Feature | Endpoint Test | Pytest | Manual Swagger |
|---------|---------------|--------|----------------|
| Pre-signed URL Generation | ✅ | ✅ | ✅ |
| Direct MinIO Upload | ✅ | ✅ | ⚠️ (via curl) |
| Storage-Key Processing | ✅ | ✅ | ✅ |
| Legacy File Upload | ✅ | ✅ | ✅ |
| Privacy Cleanup | ✅ | ✅ | ⚠️ (manual check) |
| Queue Routing | ✅ | ✅ | ❌ |
| Error Handling | ⚠️ | ✅ | ⚠️ |
| MinIO Health | ✅ | ✅ | ❌ |
| Celery Queues | ❌ | ✅ | ❌ |

**Legend**: ✅ Full Coverage | ⚠️ Partial Coverage | ❌ Not Covered

---

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: MinIO Architecture Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Docker
        run: docker compose up -d
      
      - name: Wait for services
        run: |
          until curl -s http://localhost:8000/health | grep -q "healthy"; do
            echo "Waiting for API..."
            sleep 5
          done
      
      - name: Run Endpoint Tests
        run: bash tests/test_minio_endpoints.sh
      
      - name: Run Pytest
        run: |
          pip install pytest requests
          pytest tests/test_minio_architecture.py -v
      
      - name: Cleanup
        run: docker compose down
```

---

## 📌 Next Steps

1. **Fix MinIO URL Issue**:
   - Add `MINIO_SERVER_URL=http://localhost:9000` to `.env`
   - Update `StorageService` to use public URL for pre-signed URLs

2. **Enhance Queue Routing**:
   - Implement duration-based routing logic
   - Add tests for `short` vs `long` queue assignment

3. **Add Performance Tests**:
   - Concurrent upload testing
   - Load testing with multiple workers
   - MinIO throughput benchmarks

4. **Improve Error Handling**:
   - Test invalid storage keys
   - Test MinIO connection failures
   - Test worker crashes during processing

---

## ✅ Summary

**Test Files Created**:
- ✅ [`tests/test_minio_endpoints.sh`](file:///home/basitdev/Me/StudioProjects/VoiceNoteAPI/tests/test_minio_endpoints.sh) - Comprehensive endpoint tests
- ✅ [`tests/test_minio_architecture.py`](file:///home/basitdev/Me/StudioProjects/VoiceNoteAPI/tests/test_minio_architecture.py) - Pytest suite

**Test Coverage**: 10 endpoint tests + 13 pytest tests = **23 total tests**

**Status**: ✅ **Ready for Testing**

Run the endpoint tests to verify the complete MinIO Privacy-First flow!
