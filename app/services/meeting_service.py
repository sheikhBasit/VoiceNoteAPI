import requests
from app.core.config import ai_config
import logging
from typing import Dict, Any

logger = logging.getLogger("VoiceNote.MeetingService")

from sqlalchemy.orm import Session
from app.db.models import Note, NoteStatus, Priority
import uuid
import time

class MeetingService:
    BASE_URL = "https://api.recall.ai/api/v1"
    
    def __init__(self, db: Session = None):
        self.db = db
        self.api_key = ai_config.RECALL_AI_API_KEY
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_bot(self, meeting_url: str, bot_name: str, user_id: str) -> Dict[str, Any]:
        """
        Dispatches a Recall.ai bot to the given meeting URL.
        """
        if not self.api_key:
            logger.warning("Recall.ai API Key missing")
            return {"error": "Meeting intelligence not configured"}

        payload = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            # Pass user_id in metadata to link transcript later
            "metadata": {
                "user_id": user_id
            },
            "transcription_options": {
                "provider": "recall" 
            }
        }

        try:
            resp = requests.post(f"{self.BASE_URL}/bot", json=payload, headers=self.headers)
            resp.raise_for_status()
            logger.info(f"Bot dispatched to {meeting_url} for user {user_id}")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to create bot: {e}")
            raise

    def handle_webhook_event(self, event_data: Dict[str, Any]):
        """
        Processes webhook events from Recall.ai (bot.joined, bot.transcription, bot.leave).
        """
        event_type = event_data.get("event")
        data = event_data.get("data", {})
        bot_id = data.get("bot_id")
        metadata = data.get("bot", {}).get("metadata", {})
        user_id = metadata.get("user_id")
        
        logger.info(f"Received meeting event: {event_type} for bot {bot_id}")

        from app.worker.task import broadcast_ws_update

        if event_type == "bot.status_change":
            status = data.get("status")
            if user_id:
                broadcast_ws_update(user_id, "BOT_STATUS", {"bot_id": bot_id, "status": status})

        elif event_type == "bot.transcription":
            # For real-time updates (Phase 9 integration)
            transcript = data.get("transcript")
            if user_id and transcript:
                broadcast_ws_update(user_id, "LIVE_TRANSCRIPT", {"bot_id": bot_id, "text": transcript})
            
        elif event_type == "bot.leave":
            # Trigger full synthesis when meeting ends
            if user_id:
                # Retrieve final transcript from Recall API (omitted for brevity, assuming data has it)
                final_transcript = data.get("transcript", "")
                self._save_transcript_and_summarize(user_id, final_transcript, bot_id)

    def _save_transcript_and_summarize(self, user_id: str, transcript: str, bot_id: str):
        try:
            note_title = f"Meeting: {time.strftime('%Y-%m-%d %H:%M')}"
            new_note = Note(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=note_title,
                transcript_groq=str(transcript),
                status=NoteStatus.PROCESSING, # Set to PROCESSING to trigger worker flow
                priority=Priority.MEDIUM
            )
            self.db.add(new_note)
            self.db.commit()
            
            # Trigger Background AI Analysis (Phase 8 Synthesis)
            from app.worker.task import analyze_note_semantics_task
            analyze_note_semantics_task.delay(new_note.id)
            
            logger.info(f"Meeting ended. Automated synthesis triggered for user {user_id} (Note ID: {new_note.id})")
        except Exception as e:
            logger.error(f"Failed to synthesize meeting note: {e}")
            self.db.rollback()
