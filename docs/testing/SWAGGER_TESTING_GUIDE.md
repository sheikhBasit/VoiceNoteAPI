# 🎨 Swagger Testing Guide - Quick Start

**Purpose:** Test your API endpoints using Swagger UI/ReDoc documentation  
**Time Required:** 5 minutes (start) + testing time  
**Prerequisites:** Docker installed and working  

---

## ⚡ Quick Start (2 commands)

```bash
# 1. Navigate to project
cd /mnt/muaaz/VoiceNoteAPI

# 2. Start all services in one command
make dev

# Wait 30 seconds for services to be ready...
```

That's it! Your API is now running. 🎉

---

## 🚀 What Gets Started?

When you run `make dev`, these services start automatically:

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| **PostgreSQL** | 5432 | Database | 🗄️ Internal |
| **Redis** | 6379 | Caching | ⚡ Internal |
| **Celery Worker** | Internal | Background tasks | 🔄 Internal |
| **Celery Beat** | Internal | Scheduled tasks | ⏰ Internal |
| **FastAPI** | 8000 | Your API | 🌐 **Open this!** |

---

## 📖 Access Swagger Docs (3 Options)

After running `make dev`, choose one:

### Option 1️⃣: Swagger UI (Interactive)
```
http://localhost:8000/docs
```
- **Best for:** Testing, trying endpoints, exploring API
- **Features:** Try it out button, request/response examples
- **What you'll see:** Beautiful interactive interface

### Option 2️⃣: ReDoc (Reference)
```
http://localhost:8000/redoc
```
- **Best for:** Reading documentation, understanding schemas
- **Features:** Organized by tags, detailed descriptions
- **What you'll see:** Professional API documentation

### Option 3️⃣: OpenAPI JSON (Raw Spec)
```
http://localhost:8000/openapi.json
```
- **Best for:** Importing to tools, automation
- **What you'll see:** Raw JSON schema

---

## 🧪 Testing Endpoints via Swagger UI

### 1. Open Swagger in Browser
```
1. Open: http://localhost:8000/docs
2. Wait for page to load (5 seconds)
3. You should see all available endpoints
```

### 2. Find Your Endpoint
```
Example: Testing Audio Upload

1. Expand section: "Audio (POST /upload-audio)"
2. Click "Try it out" button
3. Fill in the parameters/body
4. Click "Execute"
5. See the response below!
```

### 3. Common Endpoints to Test

**Health Check (No Auth Required):**
```
GET /health
- Click endpoint
- Click "Try it out"
- Click "Execute"
- Expected: {"status": "healthy", "version": "..."}
```

**Create Voice Note (Auth Required):**
```
POST /voice-notes
- You'll need a valid JWT token
- See authentication section below
```

**Admin System (Auth Required):**
```
GET /admin/stats
- Requires admin token
- See authentication section below
```

---

## 🔐 Authentication in Swagger

### Get JWT Token

**Step 1: Register/Login**
```
POST /auth/register  OR  POST /auth/login
- Fill in username and password
- Click Execute
- Copy the access_token from response
```

**Step 2: Add Token to Swagger**
```
1. Find the green "Authorize" button (top right)
2. Click it
3. Paste token in "Value" field: 
   Bearer YOUR_TOKEN_HERE
4. Click "Authorize"
5. Click "Close"
```

**Step 3: Test Protected Endpoints**
```
Now any endpoint requiring auth will work!
Try: GET /voice-notes
Expected: List of your voice notes
```

---

## ✅ Full Testing Workflow

### Quick Health Check (30 seconds)
```bash
# Terminal 1: Start services
make dev

# Terminal 2: Quick curl test
curl http://localhost:8000/health

# Expected output:
# {"status": "healthy", "version": "1.0.0", ...}
```

### Full Swagger Testing (5 minutes)
```bash
# 1. Start services
make dev

# 2. Open in browser
open http://localhost:8000/docs
# or use: firefox http://localhost:8000/docs
# or paste in any browser

# 3. Test endpoints:
   a) GET /health (no auth)
   b) POST /auth/register (create account)
   c) POST /auth/login (get token)
   d) Use token in Authorize button
   e) POST /voice-notes (create note)
   f) GET /voice-notes (list notes)
   g) GET /voice-notes/{id} (get one)
   h) DELETE /voice-notes/{id} (delete)

# 4. Check logs
make logs-api
```

---

## 🔥 Using Swagger Features

### Try It Out
```
Every endpoint has a "Try it out" button:

1. Click "Try it out"
2. Fill in parameters (they show in gray)
3. Scroll to blue "Execute" button
4. Click "Execute"
5. See response in "Response body" section
```

### Example Request/Response
```json
Request:
POST /voice-notes
{
  "title": "My Voice Note",
  "content": "This is a test note",
  "tags": ["test", "api"]
}

Response (200 OK):
{
  "id": "uuid-here",
  "title": "My Voice Note",
  "created_at": "2024-02-06T10:30:00Z",
  "status": "success"
}
```

### Curl Commands (Copy from Swagger)
```
Swagger shows curl commands automatically!

1. Make a request in Swagger
2. Look for "Request URL" (shows curl command)
3. Copy and use in terminal

Example:
curl -X 'GET' \
  'http://localhost:8000/voice-notes' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer token_here'
```

---

## 📊 Monitoring While Testing

### Watch API Logs (Real-time)
```bash
# Terminal 2: Keep open while testing
make logs-api

# You'll see:
# ✅ Each request logged
# ✅ Response times
# ✅ Any errors highlighted
# ✅ Database queries (if DEBUG=true)
```

### Check Service Health
```bash
# Terminal 3: Verify services are running
make health

# Expected output:
# ✅ API: RUNNING
# ✅ PostgreSQL: RUNNING
# ✅ Redis: RUNNING
# ✅ Celery Worker: RUNNING
# ✅ Celery Beat: RUNNING
```

### View Database (Optional)
```bash
# Terminal 3: Query database while testing
make db-shell

# Then in psql:
SELECT * FROM voice_notes;
SELECT * FROM users;
```

---

## 🛑 Stop Services

```bash
# When done testing
make down

# Or restart fresh
make restart

# Or rebuild from scratch
make fresh-start
```

---

## ⚠️ Troubleshooting

### API Not Responding
```bash
# 1. Check if services are running
make health

# 2. Check logs for errors
make logs

# 3. Restart services
make restart

# 4. Check ports are not in use
lsof -i :8000  # API port
lsof -i :5432  # Database port
lsof -i :6379  # Redis port
```

### Swagger Page Won't Load
```bash
# 1. Wait longer (30 seconds for initial startup)
# 2. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
# 3. Try different URL:
   - http://localhost:8000/docs (Swagger)
   - http://localhost:8000/redoc (ReDoc)
   - http://127.0.0.1:8000/docs (localhost IP)

# 4. Check API is running
curl http://localhost:8000/health
```

### Authorization Fails
```bash
# 1. Make sure you registered first
   POST /auth/register with valid credentials

# 2. Get fresh token
   POST /auth/login

# 3. Copy token correctly
   Don't include quotes or extra spaces

# 4. Format correctly in Authorize button
   "Bearer eyJhbGc..." (include "Bearer " prefix)
```

### Database Connection Error
```bash
# 1. Check PostgreSQL is running
make health

# 2. Reset database
make db-reset

# 3. Seed database
make seed

# 4. Restart everything
make restart
```

---

## 🎯 Testing Checklist

Mark off as you test each:

### Basic Endpoints
- [ ] GET /health returns healthy
- [ ] GET /docs (Swagger loads)
- [ ] GET /redoc (ReDoc loads)
- [ ] GET /openapi.json (JSON loads)

### Authentication
- [ ] POST /auth/register works
- [ ] POST /auth/login returns token
- [ ] Token works in Authorize button
- [ ] Protected endpoints work with token
- [ ] Protected endpoints fail without token

### Voice Notes
- [ ] POST /voice-notes creates note
- [ ] GET /voice-notes lists notes
- [ ] GET /voice-notes/{id} gets one
- [ ] PUT /voice-notes/{id} updates
- [ ] DELETE /voice-notes/{id} deletes

### Admin Features (if available)
- [ ] GET /admin/stats shows stats
- [ ] GET /admin/users lists users
- [ ] Admin endpoints require admin role

### Monitoring
- [ ] Logs appear in `make logs-api`
- [ ] Response times are reasonable
- [ ] No errors in logs during testing
- [ ] Database queries work

---

## 📈 Performance Expectations

| Action | Expected Time | Indicator |
|--------|----------------|-----------|
| Start services | 30 sec | "Services started!" |
| Load Swagger | 5 sec | Page fully rendered |
| Simple endpoint | 100ms | < 1 sec |
| File upload | 2-5 sec | Progress bar |
| AI processing | 10-30 sec | Processing indicator |

---

## 🚀 Advanced Testing

### Test with Different Data
```
Try these in Swagger:
1. Empty/null values
2. Very long strings
3. Special characters
4. Large files
5. Concurrent requests
```

### Test Error Handling
```
Try these in Swagger:
1. Invalid token
2. Wrong credentials
3. Non-existent resource (404)
4. Missing required field (400)
5. Duplicate data (409)
```

### Load Testing (Optional)
```bash
# Light load test
make test-load

# Or use Swagger to:
# 1. Create multiple notes
# 2. Query list multiple times
# 3. Delete and recreate
# 4. Watch performance in logs
```

---

## 📚 Common API Patterns

### Create Resource (POST)
```
1. Find POST endpoint
2. Click "Try it out"
3. Fill request body
4. Click "Execute"
5. See 201 Created response
6. Copy resource ID
```

### Get Resources (GET)
```
1. Find GET endpoint
2. Click "Try it out"
3. Set filters/pagination if needed
4. Click "Execute"
5. See 200 OK with data
```

### Update Resource (PUT/PATCH)
```
1. Find PUT endpoint
2. Enter resource ID
3. Click "Try it out"
4. Fill updated fields
5. Click "Execute"
6. See 200 OK with updated data
```

### Delete Resource (DELETE)
```
1. Find DELETE endpoint
2. Enter resource ID
3. Click "Try it out"
4. Click "Execute"
5. See 204 No Content
```

---

## 🎓 Learning Swagger

### Swagger UI Sections
```
Top: Servers & Authorize buttons
Left: Endpoint list by tags
Center: Endpoint details
Right: Response schemas

Each endpoint shows:
- Method (GET, POST, etc.)
- Path (/voice-notes)
- Description
- Parameters
- Request body schema
- Response examples
```

### Swagger Features
```
🔍 Search: Find endpoints quickly
📌 Try it out: Test without code
📋 Copy: Get curl/code samples
📊 Examples: See request/response
🔐 Authorize: Add auth token
```

---

## ✨ Pro Tips

1. **Keep browser open** - Don't close Swagger while developing
2. **Watch logs side-by-side** - Terminal with logs + Swagger in browser
3. **Copy curl commands** - Use generated curl for automation
4. **Test error cases** - Try invalid data to see error messages
5. **Save auth token** - Keep token somewhere while testing
6. **Use ReDoc** - Better for reading documentation
7. **Use Swagger** - Better for testing endpoints

---

## 🎉 You're Ready!

Now you can:
✅ Start all services with one command  
✅ Access interactive API documentation  
✅ Test all endpoints without code  
✅ See logs in real-time  
✅ Understand your API structure  
✅ Verify everything works  

**Enjoy your testing!** 🚀

---

## 🔗 Quick Links

After `make dev`:
- 🎨 **Swagger UI:** http://localhost:8000/docs
- 📚 **ReDoc:** http://localhost:8000/redoc
- 📄 **OpenAPI:** http://localhost:8000/openapi.json
- 📊 **API Status:** http://localhost:8000/health

---

**Last Updated:** Feb 6, 2026  
**For Issues:** Check logs with `make logs-api`  
**For More Help:** Read `docs/CI_CD_TESTING_GUIDE.md`
