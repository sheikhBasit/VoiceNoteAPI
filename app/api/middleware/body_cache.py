"""
Request Body Cache Middleware

This middleware caches the request body so it can be read multiple times.
This is necessary for device signature verification which needs to hash the body.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestBodyCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache request body for signature verification.
    
    The body is stored in request.scope['cached_body'] and can be accessed
    by downstream dependencies like verify_device_signature.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Only cache body for methods that typically have bodies
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            body = await request.body()
            # Store in scope so it's accessible to dependencies
            request.scope['cached_body'] = body
            
            # Create a new request with the cached body
            async def receive():
                return {'type': 'http.request', 'body': body}
            
            request._receive = receive
        else:
            # For GET/HEAD, set empty body
            request.scope['cached_body'] = b''
        
        response = await call_next(request)
        return response
