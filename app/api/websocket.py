from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.websocket_manager import manager
from app.services.auth_service import get_current_user_ws # We need a WS-specific auth
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ws", tags=["Real-time Sync"])

@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: str, 
    token: str = None,
    db: Session = Depends(get_db)
):
    """
    Main WebSocket handle.
    Verifies JWT for secure real-time broadcasts.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = await get_current_user_ws(token, db)
        if user.id != user_id:
             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
             return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive and listen for optional client pings
            data = await websocket.receive_text()
            # Simple heartbeat / echo
            await websocket.send_text(f"ACK: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id, websocket)
