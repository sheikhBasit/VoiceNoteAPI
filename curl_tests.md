# VoiceNote API - Professional Deployment & Integration Tests (2026)

This document contains full payloads and `curl` commands for testing all critical endpoints of the VoiceNote API.

## 1. Authentication & Lifecycle

### Register / Login (Auth)
```bash
curl -X POST "http://localhost:8000/api/v1/users/sync" \
     -H "Content-Type: application/json" \
     -d '{
       "id": "test_user_uuid",
       "name": "Basit Sheikh",
       "email": "basit@example.com",
       "device_id": "phone_android_001",
       "device_model": "Pixel 8 Pro",
       "token": "biometric_token_xyz"
     }'
```

### Refresh Token (Rotation)
```bash
curl -X POST "http://localhost:8000/api/v1/users/refresh?token=YOUR_REFRESH_TOKEN"
```

## 2. Voice Note Processing

### Upload & Process (Geofenced)
> Note: Sending coordinates to test Geofencing accuracy.
```bash
curl -X POST "http://localhost:8000/api/v1/notes/upload" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "X-GPS-Coords: 40.7128,-74.0060" \
     -F "file=@/path/to/meeting_audio.wav" \
     -F "user_role=BUSINESS_MAN"
```

### Get Note Details
```bash
curl -X GET "http://localhost:8000/api/v1/notes/YOUR_NOTE_ID" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 3. Task Management

### Create Manual Task
```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Follow up with client",
       "description": "Send a thank you email after the demo.",
       "priority": "HIGH",
       "deadline": 1738944000000,
       "assigned_entities": [{"name": "John", "email": "john@client.com"}]
     }'
```

### Upload Task Image (Thumbnail Test)
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/YOUR_TASK_ID/multimedia" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -F "file=@/path/to/whiteboard.jpg"
```

## 4. B2B & Billing

### Check Balance
```bash
curl -X GET "http://localhost:8000/api/v1/users/balance" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Corporate Wallet Simulation
> If the user is in an Organization, the `UsageMiddleware` will detect the Geofence and charge the `corporate_wallet_id`.

## 5. Search & RAG

### Semantic Search (Vector)
```bash
curl -X GET "http://localhost:8000/api/v1/notes/search?query=business%20meeting" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Ask AI about Note (RAG)
```bash
curl -X POST "http://localhost:8000/api/v1/notes/YOUR_NOTE_ID/ask" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What were the main action items discussed?"
     }'
```

---
**Status Checklist:**
- [x] Wallet Atomicity (`with_for_update`)
- [x] Task Deduplication (Ghost Task Fix)
- [x] GPS Buffer (100m Drift)
- [x] Notification Scheduler (Celery Beat)
- [x] Image Thumbnails (Worker processing)
- [x] JWT Refresh Rotation (Rotation enabled)
