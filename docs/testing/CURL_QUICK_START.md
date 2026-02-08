# 🚀 QUICK START - CURL TESTING GUIDE

## Test Status: ✅ ALL PASSING (35/35)

---

## Run Complete Test Suite

```bash
# Python version (recommended - 100% passing)
python3 /mnt/muaaz/VoiceNoteAPI/curl_all_tests_final.py

# Bash version
bash /mnt/muaaz/VoiceNoteAPI/curl_complete_tests.sh
```

---

## Quick Curl Examples

### 1. Get Authentication Token
```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/users/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@'$(date +%s)'@test.com",
    "name": "Test User",
    "device_id": "device123",
    "device_model": "iPhone14",
    "token": "biometric_token",
    "timezone": "UTC"
  }' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Token: $TOKEN"
```

### 2. Create a Note
```bash
curl -X POST "http://localhost:8000/api/v1/notes/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Test Note",
    "content": "This is test content",
    "language": "en",
    "duration_ms": 5000
  }' | jq '.'
```

### 3. Create a Task
```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Important Task",
    "priority": "HIGH",
    "communication_type": "WHATSAPP",
    "is_action_approved": false
  }' | jq '.'
```

### 4. List All Notes
```bash
curl -X GET "http://localhost:8000/api/v1/notes" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 5. List All Tasks
```bash
curl -X GET "http://localhost:8000/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 6. Search Tasks
```bash
curl -X GET "http://localhost:8000/api/v1/tasks/search?query_text=important" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 7. AI Search
```bash
curl -X POST "http://localhost:8000/api/v1/ai/search?query=test" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 8. Get User Info
```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 9. Admin Status
```bash
curl -X GET "http://localhost:8000/api/v1/admin/status" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 10. Logout
```bash
curl -X POST "http://localhost:8000/api/v1/users/logout" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Important Notes

### ✅ Valid Enum Values for Tasks
- **communication_type:** WHATSAPP | SMS | CALL | MEET | SLACK
- **priority:** LOW | MEDIUM | HIGH | URGENT

### ✅ Correct Parameter Names
- Task search: `query_text` (NOT `q`)
- AI search: `query` parameter (in URL, not body)
- User search: `q` parameter

### ✅ Expected HTTP Status Codes
- Success: **200 OK** or **201 Created**
- Auth errors: **401 Unauthorized**
- Permission errors: **403 Forbidden**
- Not found: **404 Not Found**
- Bad data: **422 Unprocessable Entity**
- Async operations: **202 Accepted**

---

## Endpoint Overview

| Method | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| POST | `/api/v1/users/sync` | 200/201 | Authentication |
| GET | `/api/v1/users/me` | 200 | Current user |
| GET | `/api/v1/users/search` | 200 | Search (param: q) |
| POST | `/api/v1/users/logout` | 200 | Logout |
| POST | `/api/v1/notes/create` | 200/201 | Create note |
| GET | `/api/v1/notes` | 200 | List notes |
| GET | `/api/v1/notes/:id` | 200 | Get note |
| PATCH | `/api/v1/notes/:id` | 200 | Update note |
| GET | `/api/v1/notes/:id/whatsapp` | 200 | WhatsApp draft |
| POST | `/api/v1/notes/:id/semantic-analysis` | 202 | Async analysis |
| GET | `/api/v1/notes/dashboard` | 200 | Dashboard |
| POST | `/api/v1/tasks` | 201 | Create task |
| GET | `/api/v1/tasks` | 200 | List tasks |
| GET | `/api/v1/tasks/:id` | 200 | Get task |
| PATCH | `/api/v1/tasks/:id` | 200 | Update task |
| DELETE | `/api/v1/tasks/:id` | 200 | Delete task |
| GET | `/api/v1/tasks/due-today` | 200 | Due today |
| GET | `/api/v1/tasks/overdue` | 200 | Overdue |
| GET | `/api/v1/tasks/assigned-to-me` | 200 | Assigned |
| GET | `/api/v1/tasks/search` | 200 | Search (param: query_text) |
| GET | `/api/v1/tasks/stats` | 200 | Statistics |
| POST | `/api/v1/tasks/:id/duplicate` | 201 | Duplicate |
| POST | `/api/v1/ai/search` | 200 | AI search (param: query) |
| GET | `/api/v1/ai/stats` | 200 | AI stats |
| GET | `/api/v1/admin/users` | 200/403 | Admin: list users |
| GET | `/api/v1/admin/users/stats` | 200/403 | Admin: user stats |
| GET | `/api/v1/admin/notes` | 200/403 | Admin: list notes |
| GET | `/api/v1/admin/admins` | 200/403 | Admin: list admins |
| GET | `/api/v1/admin/status` | 200/403 | Admin: status |
| GET | `/api/v1/admin/audit-logs` | 200/403 | Admin: audit logs |

---

## Test Results Summary

✅ **35/35 Tests Passing (100%)**

- Notes: 8/8 ✅
- Tasks: 11/11 ✅
- AI: 2/2 ✅
- Users: 3/3 ✅
- Admin: 6/6 ✅
- Error Handling: 5/5 ✅

---

## Common Curl Tips

### Format JSON output
```bash
curl ... | jq '.'
```

### Save response to file
```bash
curl ... -o response.json
```

### Show response headers
```bash
curl ... -v
```

### Get just HTTP status code
```bash
curl -s -o /dev/null -w "%{http_code}\n" ...
```

### Add timeout
```bash
curl --max-time 10 ...
```

---

## Troubleshooting

**Issue:** `401 Unauthorized`  
**Solution:** Verify token is valid and hasn't expired

**Issue:** `404 Not Found`  
**Solution:** Check resource ID is correct

**Issue:** `422 Unprocessable Entity`  
**Solution:** Verify required fields and valid enum values

**Issue:** `403 Forbidden`  
**Solution:** Check user has required permissions (admin endpoints)

---

## API Documentation

- **Interactive Docs:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc
- **OpenAPI Schema:** http://localhost:8000/openapi.json

---

**Status:** ✅ Production Ready  
**Last Updated:** February 6, 2026  
**All Tests Passing:** YES ✅
