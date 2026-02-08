import logging
import time
import math
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import location_config
from app.db import models
from app.db.session import SessionLocal
from app.services.billing_service import BillingService
from app.utils.json_logger import JLogger
from starlette.background import BackgroundTask

logger = logging.getLogger("VoiceNote.Usage")


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine formula to calculate the distance between two points on Earth in meters.
    """
    R = 6371000  # radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        from app.db import models
        start_time = time.time()

        # Pass through check for health/metrics endpoints
        if request.url.path in ["/", "/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        # 1. Capture User ID and Geolocation
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            user_id = request.headers.get("X-User-ID", "anonymous")

        gps_header = request.headers.get("x-gps-coords") or request.headers.get("X-GPS-Coords")
        
        corporate_wallet_id = None
        
        # Token extraction for early auth
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                from app.services.auth_service import SECRET_KEY, ALGORITHM
                import jwt
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
                request.state.user_id = user_id 
            except Exception as e:
                JLogger.debug("Middleware: Token decode failed", error=str(e))

        # COST ESTIMATION
        cost_map = {
            "/api/v1/notes": 1,
            "/api/v1/transcribe": 10,
            "/api/v1/ai/analyze": 5,
        }
        estimated_cost = 0
        for path, cost in cost_map.items():
            if path in request.url.path:
                estimated_cost = cost
                break

        db = None
        try:
            if user_id != "anonymous" and (gps_header or estimated_cost > 0):
                db = SessionLocal()
                user = db.query(models.User).filter(models.User.id == user_id).first()
                request.state.user = user

                if user and user.org_id and gps_header:
                    try:
                        lat_str, lon_str = gps_header.split(",")
                        user_lat, user_lon = float(lat_str), float(lon_str)
                        locations = (
                            db.query(models.WorkLocation)
                            .filter(models.WorkLocation.org_id == user.org_id)
                            .all()
                        )
                        for loc in locations:
                            dist = calculate_distance(user_lat, user_lon, loc.latitude, loc.longitude)
                            # Use config minimum radius if loc.radius is too small (GPS Drift)
                            effective_radius = max(loc.radius, location_config.DEFAULT_GEOFENCE_RADIUS)
                            if dist <= effective_radius:
                                org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
                                if org: 
                                    corporate_wallet_id = org.corporate_wallet_id
                                    JLogger.info("Middleware: Within geofence, corporate wallet selected", wallet=corporate_wallet_id)
                                break
                    except Exception as e: 
                        JLogger.error("Middleware: Geofence error", error=str(e))

                if estimated_cost > 0:
                    # Premium users get free notes processing
                    if user and user.tier == models.SubscriptionTier.PREMIUM and "/api/v1/notes" in request.url.path:
                        estimated_cost = 0

                    if estimated_cost > 0:
                        billing = BillingService(db)
                        target_wallet = corporate_wallet_id or user_id
                        if not billing.check_balance(target_wallet, estimated_cost, for_update=True):
                            return JSONResponse(
                                status_code=402,
                                content={"detail": f"Payment Required: balance depleted."},
                            )

            response = await call_next(request)
        finally:
            if db:
                db.close()

        process_time = time.time() - start_time
        response.background = BackgroundTask(
            self.log_usage,
            request,
            response,
            process_time,
            user_id,
            estimated_cost,
            corporate_wallet_id,
        )

        return response

    def log_usage(
        self,
        request: Request,
        response: Response,
        duration: float,
        user_id: str,
        estimated_cost: int,
        corporate_wallet_id: Optional[str] = None,
    ):
        try:
            from app.db import models
            from app.db.session import SessionLocal
            from app.services.billing_service import BillingService
            
            if not request.url.path.startswith("/api/v1"):
                return

            db = SessionLocal()
            try:
                if response.status_code < 400 and estimated_cost > 0 and user_id != "anonymous":
                    billing = BillingService(db)
                    billing.charge_usage(
                        user_id,
                        estimated_cost,
                        f"API Call: {request.url.path}",
                        override_wallet_id=corporate_wallet_id,
                    )

                log_entry = models.UsageLog(
                    user_id=user_id if user_id != "anonymous" else None,
                    endpoint=request.url.path,
                    duration_seconds=int(duration),
                    status=response.status_code,
                )
                db.add(log_entry)
                db.commit()
            except Exception as e:
                JLogger.warning(f"Usage logging internal error: {e}")
            finally:
                db.close()
        except Exception as outer_e:
            import logging
            logging.error(f"Usage logging critical failure: {outer_e}")
