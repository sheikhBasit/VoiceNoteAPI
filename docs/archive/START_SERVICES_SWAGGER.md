# 🚀 Start Services & Test on Swagger - Quick Reference

## ⚡ TL;DR (Just Run This!)

```bash
# Go to your project
cd /mnt/muaaz/VoiceNoteAPI

# Start ALL services with one command
make dev

# Wait ~30 seconds, then open in browser:
http://localhost:8000/docs
```

**That's it!** Your Swagger UI is now running! 🎉

---

## 📋 What This Command Does

When you run `make dev`, it automatically:

```
✅ Builds all Docker containers (if needed)
✅ Starts PostgreSQL database (port 5432)
✅ Starts Redis cache (port 6379)
✅ Starts Celery Worker (background tasks)
✅ Starts Celery Beat (scheduled tasks)
✅ Starts FastAPI (your API on port 8000)
✅ Runs health checks
✅ Shows you when everything is ready
```

---

## 🌐 Access Your API After Starting

| URL | What | Purpose |
|-----|------|---------|
| `http://localhost:8000/docs` | 🎨 **Swagger UI** | **Use this!** Interactive testing |
| `http://localhost:8000/redoc` | 📚 ReDoc | Alternative documentation |
| `http://localhost:8000/health` | 🏥 Health Check | Verify API is running |
| `http://localhost:8000/openapi.json` | 📄 Raw Spec | Machine-readable API spec |

---

## 🧪 Quick Testing Example

### Step 1: Start Services
```bash
cd /mnt/muaaz/VoiceNoteAPI
make dev
```

### Step 2: Wait for Output
```
🚀 Starting all services...
✅ Services started!
✅ API: RUNNING
✅ PostgreSQL: RUNNING
✅ Redis: RUNNING
✅ Celery Worker: RUNNING
✅ Celery Beat: RUNNING
```

### Step 3: Open Swagger in Browser
```
Click this link (or paste in browser):
http://localhost:8000/docs
```

### Step 4: Test an Endpoint
```
1. Find "Health Check" section
2. Click "GET /health"
3. Click "Try it out" button
4. Click "Execute" button
5. See response: {"status": "healthy"}
```

### Step 5: Done! ✨
```
You've successfully tested your API!
See SWAGGER_TESTING_GUIDE.md for more examples.
```

---

## 🛠️ Other Useful Commands

```bash
# View API logs in real-time
make logs-api

# Check if all services are healthy
make health

# Stop all services
make down

# Restart everything
make restart

# View database
make db-shell

# Run tests
make test-quick

# View all available commands
make help
```

---

## 🔍 Multiple Terminals Setup (Recommended)

For best experience, open **3 terminals**:

### Terminal 1: Start Services
```bash
cd /mnt/muaaz/VoiceNoteAPI
make dev
```
**Keep this running!**

### Terminal 2: Watch Logs
```bash
cd /mnt/muaaz/VoiceNoteAPI
make logs-api
```
**You'll see each API request here in real-time**

### Terminal 3: Run Tests/Commands
```bash
cd /mnt/muaaz/VoiceNoteAPI

# While Services Run:
make health
make test-quick
make db-shell
# etc.
```

---

## ⚠️ Troubleshooting

### "Port 8000 already in use"
```bash
# Kill whatever is using port 8000
lsof -i :8000
kill -9 <PID>

# Then try again
make dev
```

### "Services won't start"
```bash
# Make sure Docker is running
docker ps

# If Docker not running, start it:
# (depends on your system)

# Then clean and rebuild
make restart
make fresh-start
```

### "Swagger won't load"
```bash
# 1. Wait longer (first load takes 30 sec)
# 2. Hard refresh browser (Ctrl+Shift+R)
# 3. Try different URL:
   http://127.0.0.1:8000/docs
   
# 4. Check if API is running
curl http://localhost:8000/health
```

### "Database connection error"
```bash
# Reset and reseed
make db-reset
make seed

# Restart
make restart
```

---

## 📊 Expected Output

When you run `make dev`, you should see:

```bash
$ make dev
🚀 Starting all services...
```

Then after 5-10 seconds:

```bash
✅ Services started!

🔍 Health Check Status:
  ✅ API (Port 8000): RUNNING
  ✅ PostgreSQL (Port 5432): RUNNING  
  ✅ Redis (Port 6379): RUNNING
  ✅ Celery Worker: RUNNING
  ✅ Celery Beat: RUNNING

🎉 All services are ready!
🌐 API: http://localhost:8000
📖 Swagger: http://localhost:8000/docs
```

---

## 🎯 Testing Workflow

```
1. Terminal 1: make dev        → Starts services
   Wait for: "✅ All services are ready!"

2. Browser: Open Swagger UI    → http://localhost:8000/docs
   Wait for: Page loads (5 sec)

3. Terminal 2: make logs-api   → Watch requests
   Shows: Real-time API activity

4. Swagger: Test endpoints
   Try: GET /health → See response

5. Terminal 3: make health
   Check: All services running

Done! Everything works! 🎉
```

---

## 🔐 Testing Protected Endpoints

Some endpoints need authentication:

### 1. Get a Token
```
In Swagger:
1. Find: POST /auth/login (or /auth/register)
2. Click: "Try it out"
3. Fill: username & password
4. Click: "Execute"
5. Copy: access_token from response
```

### 2. Use Token in Swagger
```
1. Click green "Authorize" button (top right)
2. Paste token: Bearer YOUR_TOKEN_HERE
3. Click "Authorize"
4. Now all auth-required endpoints work!
```

### 3. Test Protected Endpoint
```
1. Find: POST /voice-notes (or other protected endpoint)
2. Click: "Try it out"
3. Fill: request body (title, content, etc)
4. Click: "Execute"
5. Success! You created a voice note!
```

---

## 📚 Available Endpoints to Test

After `make dev` and opening Swagger, you can test:

### No Auth Required:
- `GET /health` - Health check
- `POST /auth/register` - Create account
- `POST /auth/login` - Login & get token

### Auth Required:
- `GET /voice-notes` - List your notes
- `POST /voice-notes` - Create note
- `GET /voice-notes/{id}` - Get one note
- `PUT /voice-notes/{id}` - Update note
- `DELETE /voice-notes/{id}` - Delete note

### Admin Endpoints (if available):
- `GET /admin/stats` - Admin statistics
- `GET /admin/users` - List all users
- `GET /admin/system` - System status

---

## 🎓 Swagger Features

### "Try it out" Button
```
Every endpoint has this button
Lets you test without writing code
Just fill in parameters and click "Execute"
```

### Request Parameters
```
Some show in URL: /voice-notes/{id}
Some in body: {"title": "...", "content": "..."}
Some in headers: Authorization, Content-Type
```

### Response Examples
```
Swagger shows:
- Response status (200, 400, 404, etc)
- Response body (JSON)
- Response headers
- Curl command to reproduce
```

---

## 💾 Keeping Services Running

### Background Execution
```bash
# Services run in background
# You can close terminal without stopping them

# But to keep the terminal open and see logs:
make logs
```

### Persistent Services
```bash
# Services keep running until you stop them
make down

# Check if running
make health

# Restart if stopped
make up
```

---

## 🎉 Success Indicators

You'll know everything works when:

```
✅ make dev shows "All services are ready!"
✅ Browser loads http://localhost:8000/docs
✅ Swagger page fully renders
✅ GET /health returns {"status": "healthy"}
✅ All endpoints listed in Swagger
✅ make logs-api shows real-time requests
✅ make health shows all green ✓
```

---

## 🚀 Next Steps

1. **Start services:** `make dev`
2. **Open Swagger:** http://localhost:8000/docs
3. **Test endpoints:** Click "Try it out"
4. **Watch logs:** `make logs-api`
5. **Create account:** POST /auth/register
6. **Get token:** POST /auth/login
7. **Test protected endpoints:** POST /voice-notes
8. **See database:** `make db-shell`

---

## 📖 For More Details

See full guides:
- `docs/SWAGGER_TESTING_GUIDE.md` - Complete testing guide
- `docs/TESTING_CI_CD.md` - CI/CD testing
- `docs/CI_CD_QUICK_START.md` - Setup guide

---

## 🆘 Quick Help

```bash
# View all commands
make help

# Check service status
make health

# View logs
make logs

# Stop everything
make down

# Start fresh
make restart

# See database
make db-shell
```

---

**TL;DR: Run `make dev` → Open http://localhost:8000/docs → Test endpoints! 🎉**
