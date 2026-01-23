import pytest
import hmac
import hashlib
import time
import json
from httpx import AsyncClient
from app.main import app
from app.utils.security import DEVICE_SECRET_KEY

def generate_test_signature(method: str, path: str, timestamp: str):
    message = f"{method}{path}{timestamp}".encode()
    return hmac.new(
        DEVICE_SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()

@pytest.mark.asyncio
async def test_dashboard_endpoint(client: AsyncClient):
    # Test unauthorized access (if we had auth, but dashboard is open for now or takes user_id)
    response = await client.get("/api/v1/notes/dashboard?user_id=test_user")
    assert response.status_code == 200
    data = response.json()
    assert "task_velocity" in data
    assert "topic_heatmap" in data
    assert "meeting_roi_hours" in data

@pytest.mark.asyncio
async def test_search_endpoint(client: AsyncClient):
    # Mock search query
    search_query = {
        "query": "What did I say about cricket?",
        "user_id": "test_user"
    }
    response = await client.post("/api/v1/notes/search", json=search_query)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "answer" in data
    assert "source" in data

@pytest.mark.asyncio
async def test_security_signature_verification(client: AsyncClient):
    path = "/api/v1/notes/process"
    method = "POST"
    timestamp = str(int(time.time()))
    signature = generate_test_signature(method, path, timestamp)
    
    # Test with valid signature (should fail on file/user validation but pass security)
    headers = {
        "X-Device-Signature": signature,
        "X-Device-Timestamp": timestamp
    }
    payload = {
        "user_id": "non_existent_user",
        "mode": "GENERIC"
    }
    # Using files parameter for multipart/form-data
    files = {"file": ("test.mp3", b"fake audio content", "audio/mpeg")}
    
    response = await client.post(path, data=payload, files=files, headers=headers)
    
    # It should pass security but fail on user not found (404)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

@pytest.mark.asyncio
async def test_security_invalid_signature(client: AsyncClient):
    path = "/api/v1/notes/process"
    timestamp = str(int(time.time()))
    
    headers = {
        "X-Device-Signature": "invalid_sig",
        "X-Device-Timestamp": timestamp
    }
    
    response = await client.post(path, data={"user_id": "test"}, headers=headers)
    assert response.status_code == 401
    assert "Invalid device signature" in response.json()["detail"]

@pytest.mark.asyncio
async def test_whatsapp_draft_endpoint(client: AsyncClient):
    # Note: This requires a note to exist. Since we are using an empty test DB,
    # it might return 404. Let's check if it handles 404 correctly.
    response = await client.get("/api/v1/notes/fake_note/whatsapp?user_id=test_user")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_conflict_detection_logic():
    from app.services.calendar_service import CalendarService
    
    tasks = [{"description": "Meeting", "deadline": 1000}]
    events = [{"title": "Gym", "start_time": 500, "end_time": 1500}]
    
    conflicts = CalendarService.detect_conflicts(tasks, events)
    assert len(conflicts) == 1
    assert conflicts[0]["conflicting_event"] == "Gym"

    # No conflict
    tasks = [{"description": "Meeting", "deadline": 2000}]
    conflicts = CalendarService.detect_conflicts(tasks, events)
    assert len(conflicts) == 0
