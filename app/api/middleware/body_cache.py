"""
Request Body Cache Middleware (Pure ASGI)

Caches the request body so it can be read multiple times.
Required for device signature verification which needs to hash the body.

Uses pure ASGI instead of BaseHTTPMiddleware to avoid known
compatibility issues with CORSMiddleware (starlette#1315).
"""

from starlette.types import ASGIApp, Receive, Scope, Send


class RequestBodyCacheMiddleware:
    """
    Pure ASGI middleware to cache request body for signature verification.

    The body is stored in scope['cached_body'] and can be accessed
    by downstream dependencies like verify_device_signature.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["method"] in ("POST", "PUT", "PATCH", "DELETE"):
            body_chunks: list[bytes] = []
            body_complete = False

            async def caching_receive():
                nonlocal body_complete
                message = await receive()
                if message["type"] == "http.request":
                    chunk = message.get("body", b"")
                    if chunk:
                        body_chunks.append(chunk)
                    if not message.get("more_body", False):
                        body_complete = True
                        scope["cached_body"] = b"".join(body_chunks)
                return message

            # First, consume and cache the full body
            chunks: list[bytes] = []
            while not body_complete:
                msg = await caching_receive()
                chunks.append(msg.get("body", b""))

            cached = scope.get("cached_body", b"".join(chunks))
            scope["cached_body"] = cached

            # Provide a replayed receive for downstream
            sent = False

            async def replay_receive():
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": cached, "more_body": False}
                return {"type": "http.disconnect"}

            await self.app(scope, replay_receive, send)
        else:
            scope["cached_body"] = b""
            await self.app(scope, receive, send)
