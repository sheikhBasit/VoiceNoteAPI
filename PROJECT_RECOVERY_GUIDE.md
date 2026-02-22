

# VoiceNote Project Recovery Guide

## Bugs Found & Fixed (Session Feb 22, 2026)

These bugs were discovered during live testing and fixed:

1. **New users registered as GUEST tier** - couldn't use any feature (needs FREE+)
   - File: `app/api/users.py` - Changed `tier=GUEST` → `tier=FREE`

2. **Task title not saved on creation** - `title` field was missing from the DB insert
   - File: `app/api/tasks.py` - Added `title=task_data.title` to Task constructor

3. **Refresh token sent as URL query param** - insecure (logged in access logs)
   - File: `app/api/users.py` - Changed from `Query(alias="token")` to JSON body `{"refresh_token": "..."}`

4. **Logout didn't clear httpOnly cookie** - session cookie survived logout
   - File: `app/api/users.py` - Added `response.delete_cookie("access_token")`

5. **Cookie max_age hardcoded to 3600** - would drift from token expiry
   - File: `app/api/users.py` - Changed to use `ACCESS_TOKEN_EXPIRE_MINUTES * 60`

6. **Device signature blocked dev testing** - only bypassed in `testing` env, not `development`
   - File: `app/utils/security.py` - Added `development` to bypass list

7. **Local API vs Docker Celery used different Redis DBs** - tasks queued but never processed
   - Local API → `redis://localhost:6380/2`, Docker worker → `redis://redis:6379/0`
   - Solution: Run local celery worker matching local API config, OR fix .env

## Current Status: CORE PIPELINE WORKS

Tested and verified on Feb 22, 2026:
- Register user → FREE tier (can use all features)
- Login → access_token + refresh_token
- Refresh token → new access_token
- Upload audio → note created, Celery processes it → DONE
- CRUD: Notes, Tasks, Folders - all working
- Device signature correctly enforced (bypassed in dev)

---

## The Honest Truth

You have a project that should be ~15 files serving 5-6 core features.
Instead, you have **100+ endpoints, 27 services, 17 models, 179 dependencies**.

This happened because:
1. You started with a clear, great idea: "Voice notes that auto-transcribe and create tasks"
2. You discussed with LLMs, and LLMs love suggesting features (RAG! Billing! Admin! Teams!)
3. Each feature pulled in 5 more dependencies and 10 more endpoints
4. Now nothing works because everything depends on everything else

**This is fixable.** But the fix is NOT "debug everything until it works." The fix is deciding what actually matters, making THAT work perfectly, and shelving the rest for later.

---

## What Your App Actually Is (The Core Value)

Your app solves ONE real problem:

> "I'm in a meeting/office and need to remember things. I record a voice note,
> and the app automatically gives me: a clean transcript, a summary, and
> actionable tasks with deadlines."

That's it. That's the product. That's what people will pay for.
Everything else (RAG, teams, integrations, admin dashboard, billing, organizations)
is infrastructure for a product that doesn't have its first paying user yet.

---

## What You Have vs What You Need

### PHASE 1: Working MVP (What makes the app usable)

| Feature | Status | Needed? |
|---------|--------|---------|
| Register/Login (email+password) | Built | YES |
| Upload voice note | Built | YES |
| Process: transcribe + summarize + extract tasks | Built | YES |
| List/view/edit/delete notes | Built | YES |
| List/view/edit/delete tasks | Built | YES |
| Folders | Built | YES |
| Basic search | Built | YES |
| Role personalization (student, doctor, etc.) | Built | YES - differentiator |

### PHASE 2: Growth Features (After you have real users)

| Feature | Status | When |
|---------|--------|------|
| Semantic/vector search | Built | After 100+ users have many notes |
| Multiple STT engines (Groq + Deepgram failover) | Built | Keep - good reliability |
| Push notifications for task deadlines | Built | After MVP launch |
| Soft delete + restore | Built | After MVP launch |
| Google Play Billing (NOT Stripe) | NOT built | When you're ready to monetize |

### PHASE 3: Scale Features (After you have paying users)

| Feature | Status | When |
|---------|--------|------|
| Admin dashboard | Built | When you have 1000+ users to manage |
| Teams/collaboration | Built | When businesses ask for it |
| RAG (chat with your notes) | Built | When users request it |
| Integrations (Google, Notion) | Partially built | When users request it |
| Organizations/B2B | Built | When companies approach you |
| WebSocket/SSE real-time | Built | When collaboration is live |
| Conflict detection | Built | Probably never needed |
| Geofencing/work locations | Built | Probably never needed |
| Stripe billing | Built | Web only; mobile uses Play Billing |
| Smart actions (email, whatsapp) | Built | After core is rock-solid |
| Productivity reports | Built | Nice-to-have, low priority |
| OpenTelemetry/Prometheus | Built | When you have real traffic |

---

## The Recovery Plan

### Step 0: Accept What Needs to Change

Your current architecture requires ALL of these running to start:
- PostgreSQL with pgvector
- Redis
- MinIO (S3 storage)
- Celery worker (long queue)
- Celery worker (short queue)
- Celery beat (scheduler)
- The FastAPI app itself

That's 7 processes for a pre-launch app. For Phase 1, you need:
- PostgreSQL with pgvector
- Redis (for Celery only)
- Celery worker (1 worker, all queues)
- The FastAPI app

MinIO can be replaced with local file storage for now.
Celery beat is optional (scheduled tasks can wait).
Multiple Celery workers/queues are unnecessary at your scale.

### Step 1: Make the Core Pipeline Work (Priority 1)

The #1 thing that must work perfectly:

```
User uploads audio → Celery processes it → User gets transcript + summary + tasks
```

This involves:
- app/api/notes.py (upload + process endpoints)
- app/worker/task.py (note_process_pipeline)
- app/services/ai_service.py (transcription + LLM analysis)
- app/services/note_service.py (save to DB)
- app/services/task_service.py (save extracted tasks)

Test this flow end-to-end. If this works, you have a product.

**How to test:**
1. Start PostgreSQL + Redis + Celery worker + FastAPI
2. Register a user via POST /api/v1/users/register
3. Login via POST /api/v1/users/login (get token)
4. Upload an audio file via POST /api/v1/notes/process
5. Poll GET /api/v1/notes/{id} until status = DONE
6. Verify: transcript exists, summary exists, tasks were created

### Step 2: Fix the Auth Flow for Mobile (Priority 2)

Your Kotlin app needs:
- Register → get access_token + refresh_token
- Login → get access_token + refresh_token
- Refresh token when access_token expires
- All other API calls use Bearer token

Current auth is mostly fine. Just make sure:
- Token refresh works (POST /api/v1/users/refresh)
- Device verification doesn't block mobile users unnecessarily

### Step 3: Simplify Storage (Priority 3)

For the Kotlin app, the simplest flow is:
1. App records audio
2. App uploads audio directly to your server (POST /api/v1/notes/process)
3. Server stores it locally in /uploads/ folder
4. Celery processes it

You do NOT need MinIO/presigned URLs for an MVP.
Presigned URL flow is an optimization for when you have many concurrent users.

### Step 4: Get CRUD Working (Priority 4)

Make sure these basic operations work from the Kotlin app:
- List my notes (GET /api/v1/notes)
- View a note (GET /api/v1/notes/{id})
- Edit a note (PATCH /api/v1/notes/{id})
- Delete a note (DELETE /api/v1/notes/{id})
- List my tasks (GET /api/v1/tasks)
- Update task status (PATCH /api/v1/tasks/{id})
- Create/list/delete folders (CRUD /api/v1/folders)

### Step 5: Role Personalization (Priority 5)

This is your differentiator. When a student records a lecture note vs when
an office worker records a meeting note, the AI should produce different
summaries and different types of tasks.

This is already built into your system prompts (app/core/config.py).
Make sure it actually produces different outputs for different roles.

---

## How to Make Money

### Revenue Model for a Solo Developer

**Google Play Billing** (NOT Stripe for mobile):
- Stripe is for web payments. Your Kotlin app MUST use Google Play Billing.
- Google takes 15% (first $1M/year) or 30%
- Implement subscription tiers in Google Play Console

**Pricing Strategy:**
```
Free Tier:
  - 5 voice notes per month
  - Basic transcription (1 STT engine)
  - 10 tasks max
  - No semantic search
  - Standard AI model

Pro Tier ($4.99/month):
  - Unlimited voice notes
  - Premium transcription (failover between engines)
  - Unlimited tasks
  - Semantic search across all notes
  - Better AI model for summaries
  - Role personalization
  - Push notification reminders

(That's it. Two tiers. Simple.)
```

**Implementation:**
- Track usage server-side (note count per month)
- Store subscription status from Google Play
- Google Play sends webhook → your server updates user tier
- Your server checks tier on each API call (you already have requires_tier())

**When to add Stripe:**
- Only if you build a web version
- Or for enterprise/B2B sales (which is Phase 3+)

### Marketing Strategy

1. **Launch on Google Play** with Free tier
2. **Reddit/Twitter**: Post in r/productivity, r/androidapps
3. **Product Hunt**: Launch when you have a polished app
4. **Target audience**: Office workers, students, doctors, lawyers
   - Anyone who takes a LOT of notes and is busy

---

## Concrete Next Steps (Your TODO List)

### This Week
- [ ] Strip docker-compose to: PostgreSQL + Redis + 1 Celery worker + API
- [ ] Test the core pipeline: upload audio → get transcript + summary + tasks
- [ ] Fix any errors in this pipeline (this is the ONLY priority)
- [ ] Test auth flow: register → login → refresh token → use API

### Next Week
- [ ] Start Kotlin app with 3 screens: Login, Notes List, Note Detail
- [ ] Implement audio recording in Kotlin
- [ ] Upload audio and display processing status
- [ ] Display transcript + summary + tasks

### Week 3
- [ ] Add Folders screen in Kotlin
- [ ] Add Tasks list screen in Kotlin
- [ ] Add role selection during onboarding
- [ ] Test with 3-4 real people (friends/colleagues)

### Week 4
- [ ] Fix bugs from user testing
- [ ] Add Google Play Billing (Free + Pro)
- [ ] Prepare Play Store listing
- [ ] Launch

### After Launch
- [ ] Monitor which features users actually use
- [ ] Only build what users request
- [ ] Never add a feature because an LLM suggested it

---

## What to Do With All the Extra Code

DON'T delete it. It's built and might be useful later. Instead:

1. **Admin dashboard**: Leave it. Use it yourself to monitor your app.
   Just don't spend time improving it until you have users.

2. **Teams/collaboration**: Leave the code. Turn it on when a business asks.

3. **RAG**: Leave the code. Enable it as a Pro feature when you have
   enough users with enough notes for it to be useful.

4. **Billing (Stripe)**: Leave it but don't use it for mobile.
   If you ever build a web app, it's ready.

5. **Integrations**: Leave it. Low priority. Users rarely use integrations.

6. **70+ admin endpoints**: Leave them. They don't hurt anything by existing.

The key insight: **existing code that doesn't run doesn't cause bugs.**
Code that runs but isn't tested causes bugs. Focus on testing what runs.

---

## Architecture for Sanity

```
What runs in production (Phase 1):

┌─────────────┐     ┌──────────────┐     ┌───────────┐
│  Kotlin App │────→│  FastAPI API  │────→│ PostgreSQL│
│  (Android)  │←────│  (8 routes)   │←────│ + pgvector│
└─────────────┘     └──────┬───────┘     └───────────┘
                           │
                    ┌──────▼───────┐     ┌───────────┐
                    │ Celery Worker │────→│   Redis    │
                    │ (audio proc)  │←────│  (broker)  │
                    └──────────────┘     └───────────┘

API Routes that matter:
  POST /users/register
  POST /users/login
  POST /users/refresh
  POST /notes/process          ← The magic endpoint
  GET  /notes
  GET  /notes/{id}
  PATCH /notes/{id}
  DELETE /notes/{id}
  GET  /tasks
  PATCH /tasks/{id}
  CRUD /folders

Everything else exists but doesn't need to be tested or maintained yet.
```

---

## Final Advice

1. **Stop adding features.** The app needs to DO one thing well before it does 50 things poorly.

2. **Ship ugly.** Your Kotlin app doesn't need to be beautiful on Day 1.
   It needs to record audio, show transcripts, and show tasks. That's it.

3. **Real users > LLM suggestions.** From now on, only add features that
   a real human user specifically requests. Not what Claude/GPT suggests.

4. **Test the pipeline, not the infrastructure.** If audio → transcript → tasks
   works reliably, you have a viable product. Everything else is polish.

5. **You are one person.** Google was 2 people. WhatsApp was 2 people.
   They didn't start with admin dashboards and billing systems.
   They started with one thing that worked.

Your idea is genuinely good. Voice notes → auto tasks is a real problem solver.
The project isn't ruined, it's just buried under features that don't matter yet.
Dig out the core, make it work, ship it.
