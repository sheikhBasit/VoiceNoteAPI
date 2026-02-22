import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.auth_service import get_current_user_ws
from app.utils.json_logger import JLogger

router = APIRouter()

@router.websocket("/logs/stream")
async def stream_logs(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket endpoint for streaming live JLogger output to admins.
    
    The token must be provided as a query parameter.
    """
    if not token:
        token = websocket.cookies.get("access_token")

    if not token:
        await websocket.close(code=4001)  # Policy Violation
        return

    # Create a transient DB session for WS auth
    db = SessionLocal()
    try:
        user = await get_current_user_ws(token, db)
        if not user or not user.is_admin:
            await websocket.close(code=4003)  # Forbidden
            return
    except Exception:
        await websocket.close(code=4001)
        return
    finally:
        db.close()

    await websocket.accept()
    
    # Queue to buffer logs for this specific connection
    log_queue = asyncio.Queue(maxsize=100)

    def log_listener(log_entry: dict):
        """Callback for JLogger to push entries into the async queue."""
        try:
            # Note: put_nowait is safe here as long as we are in the same event loop 
            # or the caller doesn't mind if the queue is full.
            if log_queue.full():
                log_queue.get_nowait() # Drop oldest if full
            log_queue.put_nowait(log_entry)
        except Exception:
            pass

    # Subscribe to JLogger
    JLogger.add_listener(log_listener)
    
    try:
        JLogger.info("Admin connected to log stream", user_id=user.id)
        while True:
            # Wait for next log entry
            log_entry = await log_queue.get()
            await websocket.send_json(log_entry)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        JLogger.error("WebSocket log stream error", error=str(e))
    finally:
        JLogger.remove_listener(log_listener)
        try:
            await websocket.close()
        except Exception:
            pass
