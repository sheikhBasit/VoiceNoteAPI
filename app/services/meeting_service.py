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
        
        logger.info(f"Received meeting event: {event_type} for bot {bot_id}")
        
        if event_type == "bot.transcription":
            transcript = data.get("transcript")
            # Retrieve metadata to find user
            metadata = data.get("bot", {}).get("metadata", {})
            user_id = metadata.get("user_id")

            if user_id and transcript and self.db:
                self._save_transcript_to_note(user_id, transcript, bot_id)
            
        elif event_type == "bot.video_recording.done":
             # Logic to download video
             pass

    def _save_transcript_to_note(self, user_id: str, transcript: str, bot_id: str):
        try:
            note_title = f"Meeting Transcript {time.strftime('%Y-%m-%d %H:%M')}"
            new_note = Note(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=note_title,
                transcript_deepgram=str(transcript), # Store as external transcript
                status=NoteStatus.DONE, # Or PROCESSING if we want AI analysis
                priority=Priority.MEDIUM,
                is_liked=False,
                # tags not supported yet
            )
            self.db.add(new_note)
            self.db.commit()
            logger.info(f"Saved meeting transcript for user {user_id} (Note ID: {new_note.id})")
        except Exception as e:
            logger.error(f"Failed to save meeting note: {e}")
            self.db.rollback()
