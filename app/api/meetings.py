from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from app.services.meeting_service import MeetingService
import logging

router = APIRouter(tags=["Meetings"])
logger = logging.getLogger("VoiceNote.MeetingsAPI")

class JoinMeetingRequest(BaseModel):
    meeting_url: HttpUrl
    bot_name: str = "VoiceNote Assistant"

@router.post("/meetings/join")
async def join_meeting(request: JoinMeetingRequest):
    """
    Dispatch a bot to join a Zoom/Teams/Meet call.
    """
    service = MeetingService()
    try:
        # Convert HttpUrl to string
        result = service.create_bot(str(request.meeting_url), request.bot_name)
        if "error" in result:
             raise HTTPException(status_code=503, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/recall")
async def recall_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Receives events from Recall.ai bots.
    """
    service = MeetingService()
    # Process in background to return 200 OK quickly
    background_tasks.add_task(service.handle_webhook_event, payload)
    return {"status": "received"}
