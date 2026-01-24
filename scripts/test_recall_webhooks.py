import requests
import json
import time
import sys
import os
import uuid
from dotenv import load_dotenv

# Load env
load_dotenv()
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.db.models import User, Note

BASE_URL = "http://localhost:8001"

def setup_user():
    db = SessionLocal()
    user_id = "test_meeting_user"
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, email="meeting@test.com", password_hash="pw")
        db.add(user)
        db.commit()
    db.close()
    return user_id

def test_transcription_webhook():
    print("=== Testing Recall.ai Transcription Webhook ===")
    user_id = setup_user()
    bot_id = str(uuid.uuid4())
    transcript_text = f"This is a test transcript from Recall.ai {bot_id}"
    
    payload = {
        "event": "bot.transcription",
        "data": {
            "bot_id": bot_id,
            "transcript": transcript_text,
            "bot": {
                "metadata": {
                    "user_id": user_id
                }
            }
        }
    }
    
    try:
        res = requests.post(f"{BASE_URL}/webhooks/recall", json=payload)
        print(f"Webhook Response: {res.status_code}")
        if res.status_code == 200:
            print("Webhook accepted.")
        else:
            print(f"Webhook failed: {res.text}")
            return
            
        # Wait for background task
        print("Waiting for background task...")
        time.sleep(2)
        
        db = SessionLocal()
        # Search for note content in transcript_deepgram
        note = db.query(Note).filter(Note.transcript_deepgram == transcript_text).first()
        
        if note:
            print(f"SUCCESS: Note created: {note.title} (ID: {note.id})")
            print(f"Content: {note.transcript_deepgram}")
            print(f"User: {note.user_id}")
        else:
            print("FAILURE: Note not found in DB.")
            
        db.close()

    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    test_transcription_webhook()
