import requests
import time
import json
import uuid
import os
import jwt
from datetime import UTC, datetime, timedelta

# Load .env
load_dotenv()

BASE_URL = "http://localhost:8001/api/v1"
TEST_USER_ID = "admin_main" 
SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "your-secret-key-keep-it-safe")
ALGORITHM = "HS256"

def create_test_token(user_id: str):
    expire = datetime.now(UTC) + timedelta(days=1)
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def log(msg):
    print(f"[*] {msg}")

def test_background_flow():
    # 1. Get Auth Headers
    token = create_test_token(TEST_USER_ID)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-ID": TEST_USER_ID
    }
    
    # 2. Find a note with a transcript
    log("Fetching notes...")
    res = requests.get(f"{BASE_URL}/notes", headers=headers)
    if res.status_code != 200:
        log(f"Error fetching notes: {res.status_code} - {res.text}")
        return
    notes = res.json()
    
    # Force fresh note creation for testing purity
    log("Creating a fresh test note...")
    res = requests.post(f"{BASE_URL}/notes/create", headers=headers, json={
        "title": f"Automated Test Note {uuid.uuid4().hex[:4]}",
        "summary": "This note was created for background task testing. We need a summary of the quarterly earnings and the future roadmap for AI features.",
        "transcript": "Okay everyone, let's look at the quarterly earnings. We've grown by 20%. For the future roadmap, we need to implement autonomous agents and better background processing using Celery. This is critical for VoiceNote AI."
    })
    if res.status_code != 200:
        log(f"Failed to create note: {res.status_code} - {res.text}")
        return
    note = res.json()
    note_id = note['id']
    
    log(f"Using Note ID: {note_id}")

    # 3. Test Semantic Analysis (Backgrounded)
    log("Triggering Semantic Analysis...")
    res = requests.post(f"{BASE_URL}/notes/{note_id}/semantic-analysis", headers=headers)
    print(f"Response: {res.status_code} - {res.json()}")
    assert res.status_code == 202 or res.status_code == 200
    
    # 4. Test Ask AI (Backgrounded)
    log("Triggering Ask AI...")
    res = requests.post(f"{BASE_URL}/notes/{note_id}/ask", 
                        headers=headers, 
                        json={"question": "What was the growth mentioned in the note?"})
    print(f"Response: {res.status_code} - {res.json()}")
    assert res.status_code == 202 or res.status_code == 200

    # 5. Test Embedding Update (Auto-triggered on PATCH)
    log("Updating note to trigger background embedding regeneration...")
    res = requests.get(f"{BASE_URL}/notes/{note_id}", headers=headers)
    old_version = res.json().get('embedding_version', 0)
    
    res = requests.patch(f"{BASE_URL}/notes/{note_id}", 
                         headers=headers, 
                         json={"title": f"Updated Title {uuid.uuid4().hex[:4]}"})
    print(f"Response: {res.status_code}")
    
    log("Waiting for background workers to finish (30s for LLM processing)...")
    time.sleep(30)

    # 6. Verify Results
    log("Verifying results in Note model...")
    res = requests.get(f"{BASE_URL}/notes/{note_id}", headers=headers)
    updated_note = res.json()
    
    # Check Semantic Analysis
    if updated_note.get('semantic_analysis'):
        log("SUCCESS: Semantic analysis cached in DB!")
        print(json.dumps(updated_note['semantic_analysis'], indent=2))
    else:
        log("FAILURE: Semantic analysis not found in DB.")

    # Check Ask AI
    if updated_note.get('ai_responses'):
        log(f"SUCCESS: AI Responses found ({len(updated_note['ai_responses'])} responses)!")
        print(json.dumps(updated_note['ai_responses'][-1], indent=2))
    else:
        log("FAILURE: AI Responses not found in DB.")

    # Check Embedding Version
    new_version = updated_note.get('embedding_version', 0)
    if new_version > old_version:
        log(f"SUCCESS: Embedding regenerated (Version {old_version} -> {new_version})!")
    else:
        log(f"FAILURE: Embedding version did not increase.")

if __name__ == "__main__":
    try:
        test_background_flow()
    except Exception as e:
        print(f"\n[!] Test Failed: {e}")
