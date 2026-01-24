import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.db.session import SessionLocal
from app.services.billing_service import BillingService
from app.db.models import UsageLog
import logging

from fastapi.responses import JSONResponse

logger = logging.getLogger("VoiceNote.Usage")

class UsageTrackingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Pass through check for health/metrics endpoints
        if request.url.path in ["/", "/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        # 1. Capture User ID
        # For production, this MUST come from the Auth Middleware (request.state.user_id)
        # For this MVP, we will extract it or default to "anonymous"
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
             # Fallback for testing commercial flows without full Auth middleware
             # In headers or query param?
             user_id = request.headers.get("X-User-ID", "anonymous")

        # 2. COST ESTIMATION & LIMIT ENFORCEMENT
        from app.db.models import User, SubscriptionTier
        
        cost_map = {
            "/api/v1/notes": 1,
            "/api/v1/transcribe": 10,
            "/api/v1/ai/analyze": 5,
            "/api/v1/meetings/join": 20
        }
        
        estimated_cost = 0
        for path, cost in cost_map.items():
            if path in request.url.path:
                estimated_cost = cost
                break
        
        if user_id != "anonymous" and estimated_cost > 0:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user.tier == SubscriptionTier.PREMIUM:
                    # Premium users get unlimited basic notes access
                    if "/api/v1/notes" in request.url.path:
                        estimated_cost = 0 
                
                if estimated_cost > 0:
                    billing = BillingService(db)
                    has_funds = billing.check_balance(user_id, estimated_cost)
                    if not has_funds:
                        return JSONResponse(
                            status_code=402, 
                            content={"detail": "Payment Required: Your credit balance is depleted. Please upgrade to Premium for unlimited access."}
                        )
            except Exception as e:
                logger.error(f"Usage enforcement failed: {e}")
            finally:
                db.close()
        
        # 3. Proceed with request
        response = await call_next(request)
        
        # 4. Calculate Metrics & Charge (Post-Processing)
        process_time = time.time() - start_time
        
        try:
            self.log_usage(request, response, process_time, user_id, estimated_cost)
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            
        return response

    def log_usage(self, request: Request, response: Response, duration: float, user_id: str, estimated_cost: int):
        """
        Writes to UsageLog table and Charges Logic if successful.
        """
        # Filter only relevant API calls
        if not request.url.path.startswith("/api/v1"):
            return

        db = SessionLocal()
        try:
            # 1. Charge the user if response was successful (2xx)
            if response.status_code < 400 and estimated_cost > 0 and user_id != "anonymous":
                billing = BillingService(db)
                billing.charge_usage(
                    user_id, 
                    estimated_cost, 
                    f"API Call: {request.url.path}"
                )

            if user_id == "anonymous":
                # Optional: Skip logging for anonymous users to avoid FK issues
                # Or log with user_id = None if the schema allows it
                return

            # 2. Log metadata
            log_entry = UsageLog( # Changed from models.UsageLog to UsageLog as it's directly imported
                user_id=user_id,
                endpoint=request.url.path,
                duration_seconds=int(duration),
                status=response.status_code
            )
            db.add(log_entry) # Changed from log to log_entry
            db.commit()
        except Exception as e:
            # Don't break the request if logging fails
            logger.warning(f"Usage logging error: {e}")
        finally:
            db.close()
