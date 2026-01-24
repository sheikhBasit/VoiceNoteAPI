import requests
from app.core.config import ai_config
import logging
from typing import Dict, Any

logger = logging.getLogger("VoiceNote.MeetingService")

class MeetingService:
    BASE_URL = "https://api.recall.ai/api/v1"
    
    def __init__(self):
        self.api_key = ai_config.RECALL_AI_API_KEY
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_bot(self, meeting_url: str, bot_name: str = "VoiceNote Assistant") -> Dict[str, Any]:
        """
        Dispatches a Recall.ai bot to the given meeting URL.
        """
        if not self.api_key:
            logger.warning("Recall.ai API Key missing")
            return {"error": "Meeting intelligence not configured"}

        payload = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            # Webhook for when the bot leaves or transcribes
            "transcription_options": {
                "provider": "recall" # Or "deepgram" if supported
            },
            # Real-time events if we want websocket support later
        }

        try:
            resp = requests.post(f"{self.BASE_URL}/bot", json=payload, headers=self.headers)
            resp.raise_for_status()
            logger.info(f"Bot dispatched to {meeting_url}")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to create bot: {e}")
            raise

    def handle_webhook_event(self, event_data: Dict[str, Any]):
        """
        Processes webhook events from Recall.ai (bot.joined, bot.transcription, bot.leave).
        """
        event_type = event_data.get("event")
        bot_id = event_data.get("data", {}).get("bot_id")
        
        logger.info(f"Received meeting event: {event_type} for bot {bot_id}")
        
        if event_type == "bot.transcription":
            transcript = event_data.get("data", {}).get("transcript")
            # Logic to save transcript to Note would go here
            # save_transcript_to_note(transcript)
            pass
            
        elif event_type == "bot.video_recording.done":
             # Logic to download video
             pass
