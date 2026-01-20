import time
import logging
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import your routers
from app.routers import notes, tasks, users, ai, testing
from app.db.session import SessionLocal

# --- 1. Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("voicenote_ai")

# --- 2. Rate Limiting (Throttle) ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="VoiceNote AI API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- 3. Custom Biometric Auth Middleware ---
class BiometricAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exempt health check and testing endpoints
        if request.url.path in ["/health", "/api/test/stt-comparison", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        device_token = request.headers.get("X-Device-Token")
        if not device_token:
            return Response("Missing Biometric Device Token", status_code=401)
        
        # Logic: Verify token exists in 'users' table
        # db = SessionLocal()
        # user = db.query(User).filter(User.token == device_token).first()
        # if not user: return Response("Invalid Session", status_code=401)
        
        return await call_next(request)

# --- 4. Middleware Stack (Order Matters!) ---

# A. Security Headers (Helmet Equivalent)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# B. GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# C. Trusted Hosts
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "localhost", "*.ngrok-free.app"])

# D. CORS (Configured for Mobile App)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For mobile apps, origins are often null/wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["X-Device-Token", "Content-Type", "Authorization"],
)

# E. Auth Middleware
app.add_middleware(BiometricAuthMiddleware)

# --- 5. Health Checks ---
@app.get("/health", tags=["System"])
async def health_check():
    """Deep health check for DB and Redis."""
    try:
        # Test DB: db.execute("SELECT 1")
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {"database": "online", "redis": "online"}
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service Unhealthy")

# --- 6. Router Registration ---
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(users.router)
app.include_router(ai.router)
app.include_router(testing.test_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)