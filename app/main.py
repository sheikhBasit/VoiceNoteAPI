from app.utils.json_logger import JLogger
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.api import users, notes, tasks, ai, admin, testing, meetings, webhooks, websocket
import logging
import os

from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.staticfiles import StaticFiles

# Suppress excessive health/metrics logs
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health") == -1 and record.getMessage().find("/metrics") == -1

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

app = FastAPI(
    title="VoiceNote AI API",
    description="AI-powered voice note taking and task management",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

# Add security scheme for Swagger UI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Define BearerAuth security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token from /api/v1/users/sync"
        }
    }
    
    # Replace all HTTPBearer references with BearerAuth
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict) and "security" in operation:
                # Replace HTTPBearer with BearerAuth
                operation["security"] = [
                    {"BearerAuth": []} if "HTTPBearer" in sec else sec
                    for sec in operation["security"]
                ]
    
    # Apply security globally to all endpoints (fallback)
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"}
    )
    dark_css = """
    <style>
        body { background-color: #202020 !important; color: #e0e0e0 !important; }
        .swagger-ui .opblock .opblock-summary-operation-id, .swagger-ui .opblock .opblock-summary-path, .swagger-ui .opblock .opblock-summary-path__deprecated { color: #e0e0e0 !important; }
        .swagger-ui .opblock.opblock-post { background: rgba(73, 204, 144, 0.1); border-color: #49cc90; }
        .swagger-ui .opblock.opblock-post .opblock-summary { border-color: #49cc90; }
        .swagger-ui .opblock.opblock-get { background: rgba(97, 175, 254, 0.1); border-color: #61affe; }
        .swagger-ui .opblock.opblock-get .opblock-summary { border-color: #61affe; }
        .swagger-ui .opblock.opblock-put { background: rgba(252, 161, 48, 0.1); border-color: #fca130; }
        .swagger-ui .opblock.opblock-put .opblock-summary { border-color: #fca130; }
        .swagger-ui .opblock.opblock-delete { background: rgba(249, 62, 62, 0.1); border-color: #f93e3e; }
        .swagger-ui .opblock.opblock-delete .opblock-summary { border-color: #f93e3e; }
        .swagger-ui .scheme-container { background-color: #262626 !important; box-shadow: none !important; }
        .swagger-ui .models { color: #e0e0e0 !important; }
        .swagger-ui section.models h4 { color: #e0e0e0 !important; }
        .swagger-ui .model-title { color: #e0e0e0 !important; }
        .swagger-ui .model { color: #e0e0e0 !important; }
        .swagger-ui table thead tr th, .swagger-ui table thead tr td, .swagger-ui table tbody tr td { color: #e0e0e0 !important; }
        .swagger-ui .dialog-ux .modal-ux { background-color: #262626 !important; border: 1px solid #333 !important; color: #e0e0e0 !important; }
        .swagger-ui .dialog-ux .modal-ux-header h3 { color: #e0e0e0 !important; }
        .swagger-ui .dialog-ux .modal-ux-content h4 { color: #e0e0e0 !important; }
        .swagger-ui label { color: #e0e0e0 !important; }
        .swagger-ui input { background-color: #2d2d2d !important; color: #e0e0e0 !important; }
        .swagger-ui select { background-color: #2d2d2d !important; color: #e0e0e0 !important; }
        .swagger-ui textarea { background-color: #2d2d2d !important; color: #e0e0e0 !important; }
        .swagger-ui .btn { color: #e0e0e0 !important; border-color: #e0e0e0 !important; }
        .swagger-ui .topbar { background-color: #1a1a1a !important; }
    </style>
    """
    return HTMLResponse(response.body.decode("utf-8").replace("</head>", dark_css + "</head>"))

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
    <title>VoiceNote AI API - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; }
    </style>
    </head>
    <body>
    <div id="redoc-container"></div>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
    <script>
        Redoc.init(
            "openapi.json",
            {
                theme: {
                    colors: {
                        primary: { main: '#00E5FF' },
                        success: { main: '#00E5FF' },
                        text: { primary: '#E0E0E0', secondary: '#B0B0B0' },
                        http: {
                            get: '#61affe',
                            post: '#49cc90',
                            put: '#fca130',
                            delete: '#f93e3e',
                        }
                    },
                    typography: {
                        code: { color: '#ff5f85', backgroundColor: '#2d2d2d' },
                        headings: { fontFamily: 'Inter, sans-serif', fontWeight: 'bold', color: '#E0E0E0' }
                    },
                    sidebar: {
                        backgroundColor: '#202020',
                        textColor: '#E0E0E0'
                    },
                    rightPanel: {
                        backgroundColor: '#262626',
                        textColor: '#E0E0E0'
                    }
                }
            },
            document.getElementById('redoc-container')
        );
    </script>
    </body>
    </html>
    """)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the full traceback for engineers
    JLogger.exception("Unhandled exception caught by global handler", 
                      path=request.url.path, 
                      method=request.method)
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

# Testing endpoints - only in non-production environments
if os.getenv("ENVIRONMENT", "development") != "production":
    app.include_router(testing.test_router)  # NEW: Test endpoints
    JLogger.info("Testing endpoints enabled (non-production environment)")
else:
    JLogger.info("Testing endpoints disabled (production environment)")

from app.api import webhooks, meetings, websocket # NEW
app.include_router(webhooks.router)
app.include_router(meetings.router)
app.include_router(websocket.router)

# Mount static files for local storage access
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from prometheus_fastapi_instrumentator import Instrumentator
from app.api.middleware.usage import UsageTrackingMiddleware # NEW

Instrumentator().instrument(app).expose(app)
app.add_middleware(UsageTrackingMiddleware) # NEW: Usage Metering

from starlette.types import Message

class RequestBodyCacheMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Cache the body only for mutating methods
        if scope["method"] in ("POST", "PUT", "PATCH"):
            body = b""
            more_body = True
            while more_body:
                message = await receive()
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

            # Re-emit the body as a single message for downstream consumers
            async def receive_cached():
                return {"type": "http.request", "body": body, "more_body": False}

            # Set the cached body on scope for easy access in dependencies
            scope["cached_body"] = body
            await self.app(scope, receive_cached, send)
        else:
            await self.app(scope, receive, send)

@app.on_event("startup")
async def startup_event():
    pass

app.add_middleware(RequestBodyCacheMiddleware)

@app.get("/")
def read_root():
    return {
        "status": "VoiceNote AI Online",
        "version": "1.0.1",
        "endpoints": {
            "users": "/api/v1/users",
            "notes": "/api/v1/notes",
            "tasks": "/api/v1/tasks",
            "ai": "/api/v1/ai",
            "admin": "/api/v1/admin"
        }
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Check DB connectivity
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "service": "VoiceNote"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
