import time
import uuid
from sqlalchemy.orm import Session
from app.db import models
from app.utils.json_logger import JLogger

class MeetingService:
    """Service for handling meeting bot webhooks and processing transcripts."""

    def __init__(self, db: Session):
        self.db = db

    def handle_webhook_event(self, event_data: dict):
        """Processes meeting bot webhook events."""
        event_type = event_data.get("event")
        data = event_data.get("data", {})
        
        if event_type == "bot.leave":
            bot_metadata = data.get("bot", {}).get("metadata", {})
            user_id = bot_metadata.get("user_id")
            transcript = data.get("transcript", "")
            
            if user_id and transcript:
                self._create_note_from_meeting(user_id, transcript)

    def _create_note_from_meeting(self, user_id: str, transcript: str):
        """Creates a note from a meeting transcript."""
        note_id = str(uuid.uuid4())
        new_note = models.Note(
            id=note_id,
            user_id=user_id,
            title="Meeting Summary",
            transcript_groq=transcript,
            status=models.NoteStatus.DONE,
            timestamp=int(time.time() * 1000),
            updated_at=int(time.time() * 1000)
        )
        self.db.add(new_note)
        self.db.commit()
        JLogger.info(f"Created note {note_id} from meeting for user {user_id}")
