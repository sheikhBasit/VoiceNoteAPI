import logging
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal, get_db
from app.services.auth_service import get_current_user
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/api/v1", tags=["Meetings"])
logger = logging.getLogger("VoiceNote.MeetingsAPI")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class JoinMeetingRequest(BaseModel):
    meeting_url: HttpUrl
    bot_name: str = "VoiceNote Assistant"


@router.post("/meetings/join")
async def join_meeting(
    req_body: JoinMeetingRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Dispatch a bot to join a Zoom/Teams/Meet call.
    """
    user_id = current_user.id

    service = MeetingService(db)
    try:
        # Check balance first? (Optional, but good practice)
        # For now, just create bot
        result = service.create_bot(
            str(req_body.meeting_url), req_body.bot_name, user_id
        )
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/recall")
async def recall_webhook(
    payload: dict,
    background_tasks: BackgroundTasks,
    x_recall_signature: Optional[str] = Header(None),
):
    """
    Receives events from Recall.ai bots.
    Requirement: "Securing endpoints"
    """
    # Validation
    webhook_secret = os.getenv("RECALL_WEBHOOK_SECRET")
    if webhook_secret and x_recall_signature != webhook_secret:
        raise HTTPException(
            status_code=401, detail="Unauthorized: Invalid webhook signature"
        )

    # Create a new session for background task
    db = SessionLocal()
    service = MeetingService(db)

    # Process in background
    # Note: Passing db to background task might be risky if session is closed early.
    # Better to pass a factory or handle session inside method.
    # But for MVP, we let the service handle it if we redesign.
    # Actually, let's keep it simple: pass payload, service creates session internally?
    # Current design: Service takes db in init.
    # We should define a wrapper for background task.

    background_tasks.add_task(handle_start_background, payload)
    return {"status": "received"}


def handle_start_background(payload):
    db = SessionLocal()
    try:
        service = MeetingService(db)
        service.handle_webhook_event(payload)
    finally:
        db.close()
