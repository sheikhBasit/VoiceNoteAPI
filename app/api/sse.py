from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_current_user
from app.db import models
from app.services.broadcaster import broadcaster
import asyncio

router = APIRouter(prefix="/sse", tags=["sse"])

@router.get("/events")
async def sse_events(
    request: Request,
    current_user: models.User = Depends(get_current_user)
):
    """
    Server-Sent Events endpoint for real-time team and user notifications.
    Clients (Kotlin app) should connect here to receive live updates.
    """
    # Collect all team IDs the user belongs to
    team_ids = [team.id for team in current_user.teams]
    team_ids.extend([team.id for team in current_user.owned_teams])
    
    # Deduplicate
    team_ids = list(set(team_ids))

    async def event_generator():
        try:
            # Subscribe to team-wide and personal channels
            async for data in broadcaster.subscribe(team_ids, user_id=current_user.id):
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Format as SSE message
                # Kotlin app expects 'data: <json>\n\n'
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            # Clean up on cancellation
            pass
        except Exception as e:
            # Log error and close stream
            print(f"SSE Error: {e}")
            yield f"data: {{\"error\": \"Streaming interrupted: {str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Critical for Nginx proxying
        }
    )
