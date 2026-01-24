from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api import users, notes, tasks, ai, admin, testing
from app.utils.json_logger import JLogger

app = FastAPI(
    title="VoiceNote AI API",
    description="AI-powered voice note taking and task management",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    JLogger.error("Unhandled exception caught by global handler", 
                  path=request.url.path, 
                  method=request.method, 
                  error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error: A critical failure occurred. Our engineers have been notified."},
    )

# Register routers
app.include_router(users.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(ai.router)
app.include_router(admin.router)  # NEW: Admin endpoints
app.include_router(testing.test_router) # NEW: Test endpoints
from app.api import webhooks, meetings, websocket # NEW
app.include_router(webhooks.router)
app.include_router(meetings.router)
app.include_router(websocket.router)

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
