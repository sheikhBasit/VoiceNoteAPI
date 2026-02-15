import logging
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.exceptions import VoiceNoteError
from app.api import (
    admin,
    ai,
    folders,
    integrations,
    notes,
    tasks,
    testing,
    users,
    sync,
    webhooks,
    websocket,
    sse,
    teams,
)
from app.api.middleware.usage import UsageTrackingMiddleware  # NEW
from app.db.session import get_db
from app.utils.json_logger import JLogger


# Suppress excessive health/metrics logs
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return (
            record.getMessage().find("/health") == -1
            and record.getMessage().find("/metrics") == -1
        )


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# Initialize Celery app to ensure config (e.g. eager mode) is applied to current_app
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event("startup").
    """
    # Startup: Warm up AI services
    JLogger.info("Application starting up: Warming up AI models...")
    try:
        from app.services.ai_service import AIService
        service = AIService()
        # Pre-load local embedding model (SentenceTransformer)
        service._get_local_embedding_model()
        JLogger.info("Model warmup complete.")
    except Exception as e:
        JLogger.error(f"Startup warmup failed: {e}")
    
    yield
    
    # Shutdown: Clean up resources if needed
    JLogger.info("Application shutting down...")

app = FastAPI(
    title="VoiceNote AI API",
    description="AI-powered voice note taking and task management",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

# Apply Compression (Speeds up large JSON responses like notes lists)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.exception_handler(VoiceNoteError)
async def voicenote_exception_handler(request: Request, exc: VoiceNoteError):
    """Handler for custom application-level exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code,
            "detail": exc.detail
        },
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Standardize FastAPI/Starlette HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(exc.detail),
            "code": "HTTP_ERROR",
            "detail": None
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardize Pydantic validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation failed",
            "code": "VALIDATION_ERROR",
            "detail": exc.errors()
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    JLogger.critical(f"Unhandled exception: {str(exc)}", traceback=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred",
            "code": "INTERNAL_SERVER_ERROR",
            "detail": str(exc) if os.getenv("ENVIRONMENT") != "production" else None
        },
    )

# Add security scheme for Swagger UI


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
            "description": "Enter your JWT token from /api/v1/users/register or /api/v1/users/login",
        }
    }

    # Endpoints that do NOT require authentication
    public_endpoints = {
        "/api/v1/users/register": ["post"],
        "/api/v1/users/login": ["post"],
        "/api/v1/users/verify-device": ["get"],
        "/api/v1/users/request-device-auth": ["post"],
    }

    # Replace all HTTPBearer references with BearerAuth
    # And remove security from public endpoints
    for path, operations in openapi_schema.get("paths", {}).items():
        for method, operation in operations.items():
            if isinstance(operation, dict):
                # Check if this is a public endpoint
                is_public = False
                for public_path, public_methods in public_endpoints.items():
                    if (
                        path.lower() == public_path.lower()
                        and method.lower() in public_methods
                    ):
                        is_public = True
                        break

                if is_public:
                    # Remove security requirement from public endpoints
                    if "security" in operation:
                        del operation["security"]
                elif "security" in operation:
                    # Replace HTTPBearer with BearerAuth for protected endpoints
                    operation["security"] = [
                        {"BearerAuth": []} if "HTTPBearer" in sec else sec
                        for sec in operation["security"]
                    ]
                else:
                    # Add security to endpoints that have dependencies but no explicit security
                    if method.lower() not in ["options", "head"]:
                        operation["security"] = [{"BearerAuth": []}]

    # Do NOT apply security globally - let endpoints define their own
    # openapi_schema["security"] = [{"BearerAuth": []}]

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
        swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"},
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
    return HTMLResponse(
        response.body.decode("utf-8").replace("</head>", dark_css + "</head>")
    )


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


# Register routers
from app.core.limiter import limiter
app.state.limiter = limiter

app.include_router(users.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(sync.router)
app.include_router(ai.router)
app.include_router(admin.router)  # NEW: Admin endpoints
app.include_router(folders.router)  # NEW: Folders management
app.include_router(integrations.router)
app.include_router(webhooks.router)
app.include_router(websocket.router)
app.include_router(sse.router)
app.include_router(teams.router)

# Testing endpoints - only in non-production environments
if os.getenv("ENVIRONMENT", "development") != "production":
    app.include_router(testing.test_router)  # NEW: Test endpoints
    JLogger.info("Testing endpoints enabled (non-production environment)")
else:
    JLogger.info("Testing endpoints disabled (production environment)")

# Mount static files for local storage access
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


Instrumentator().instrument(app).expose(app)
app.add_middleware(UsageTrackingMiddleware)  # NEW: Usage Metering





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
            "admin": "/api/v1/admin",
        },
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
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )
