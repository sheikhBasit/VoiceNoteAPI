import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.db.session import SessionLocal
from app.services.billing_service import BillingService
from app.db.models import UsageLog
import logging

logger = logging.getLogger("VoiceNote.Usage")

class UsageTrackingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Pass through check for health/metrics endpoints
        if request.url.path in ["/", "/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        # 1. Capture User ID (Assuming Auth Middleware has run)
        # In a real app, this might come from request.state.user
        # For MVP, we'll try to extract from Authorization header or fallback
        user_id = "anonymous"
        if "Authorization" in request.headers:
             # Basic extraction - would connect to your specific Auth logic
             pass 
        
        # Proceed with request
        response = await call_next(request)
        
        # 2. Calculate Metrics
        process_time = time.time() - start_time
        
        # 3. Log Usage (Fire and Forget - ideally async task)
        # For MVP, we write to UsageLog table synchronously or via simple helper
        try:
            self.log_usage(request, response, process_time)
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            
        return response

    def log_usage(self, request: Request, response: Response, duration: float):
        """
        Writes to UsageLog table.
        """
        # Filter only relevant API calls
        if not request.url.path.startswith("/api/v1"):
            return

        db = SessionLocal()
        try:
            # Attempt to find user from request state if set by Auth middleware
            user_id = getattr(request.state, "user_id", None)
            
            log = UsageLog(
                user_id=user_id,
                endpoint=request.url.path,
                duration_seconds=int(duration),
                status=response.status_code
            )
            db.add(log)
            db.commit()
        except Exception as e:
            # Don't break the request if logging fails
            logger.warning(f"Usage logging error: {e}")
        finally:
            db.close()
