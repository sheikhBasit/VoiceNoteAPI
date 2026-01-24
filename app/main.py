from fastapi import FastAPI
from app.api import users, notes, tasks, ai, admin, testing  # NEW: Import testing router

app = FastAPI(
    title="VoiceNote AI API",
    description="AI-powered voice note taking and task management",
    version="1.0.0"
)

# Register routers
app.include_router(users.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(ai.router)
app.include_router(admin.router)  # NEW: Admin endpoints
app.include_router(admin.router)  # NEW: Admin endpoints
app.include_router(testing.test_router) # NEW: Test endpoints
from app.api import webhooks, meetings # NEW: Commercial routers
app.include_router(webhooks.router)
app.include_router(meetings.router)

from prometheus_fastapi_instrumentator import Instrumentator
from app.api.middleware.usage import UsageTrackingMiddleware # NEW

Instrumentator().instrument(app).expose(app)
app.add_middleware(UsageTrackingMiddleware) # NEW: Usage Metering

@app.on_event("startup")
async def startup_event():
    pass

@app.get("/")
def read_root():
    return {
        "status": "VoiceNote AI Online",
        "version": "1.0.0",
        "endpoints": {
            "users": "/api/v1/users",
            "notes": "/api/v1/notes",
            "tasks": "/api/v1/tasks",
            "ai": "/api/v1/ai",
            "admin": "/api/v1/admin"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "VoiceNote"}
