import hmac
import json
import time

import pytest
from httpx import AsyncClient

from app.main import app
from app.utils.security import DEVICE_SECRET_KEY


def generate_test_signature(
    method: str, path: str, timestamp: str, query: str = "", body: bytes = b""
):
    import hashlib

    body_hash = hashlib.sha256(body).hexdigest() if body else ""
    message = f"{method}{path}{query}{timestamp}{body_hash}".encode()
    return hmac.new(DEVICE_SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


@pytest.fixture(scope="module", autouse=True)
def override_auth():
    from app.db import models
    from app.db.session import SessionLocal
    from app.services.auth_service import get_current_user
    
    # Create test user in DB if not exists
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.id == "test_user").first()
    if not user:
        user = models.User(
            id="test_user",
            email="test_niche@example.com",
            name="Niche Test User",
            is_admin=True,
            usage_stats={"last_analytics_refresh": 0},
        )
        db.add(user)
        db.commit()
    db.close()

    def mock_get_current_user():
        from unittest.mock import MagicMock
        from app.db import models

        user = MagicMock()
        user.id = "test_user"
        user.is_admin = True
        user.tier = models.SubscriptionTier.PREMIUM
        return user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_dashboard_endpoint(client):
    # Test unauthorized access (if we had auth, but dashboard is open for now or takes user_id)
    path = "/api/v1/notes/dashboard"
    query = "user_id=test_user"
    timestamp = str(int(time.time()))
    signature = generate_test_signature("GET", path, timestamp, query=query)
    headers = {
        "X-Device-Signature": signature,
        "X-Device-Timestamp": timestamp,
        "Authorization": "Bearer mock-admin-token",
    }

    response = client.get(f"{path}?{query}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "task_velocity" in data
    assert "topic_heatmap" in data
    assert "meeting_roi_hours" in data


def test_search_endpoint(client):
    # Mock search query
    search_query = {"query": "What did I say about cricket?", "user_id": "test_user"}
    path = "/api/v1/notes/search"
    timestamp = str(int(time.time()))
    body = json.dumps(search_query).encode()
    signature = generate_test_signature("POST", path, timestamp, body=body)
    headers = {
        "X-Device-Signature": signature,
        "X-Device-Timestamp": timestamp,
        "Authorization": "Bearer mock-admin-token",
    }

    # Ensure mock is clean for this test
    from app.services.ai_service import AIService
    AIService._groq_client = None

    response = client.post(path, json=search_query, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "answer" in data
    assert "source" in data


def test_security_signature_verification(client):
    # Use the search endpoint for signature verification instead of process
    # because multipart signature generation is complex in tests
    path = "/api/v1/notes/search"
    method = "POST"
    timestamp = str(int(time.time()))
    search_query = {"query": "test signature"}
    body = json.dumps(search_query).encode()
    signature = generate_test_signature(method, path, timestamp, body=body)

    headers = {
        "X-Device-Signature": signature,
        "X-Device-Timestamp": timestamp,
        "X-Force-Signature-Check": "true",
        # Do NOT include Admin token here if we want to test the signature logic itself
    }

    response = client.post(path, json=search_query, headers=headers)
    assert response.status_code == 200


def test_security_invalid_signature(client):
    path = "/api/v1/notes/process"
    timestamp = str(int(time.time()))

    headers = {
        "X-Device-Signature": "invalid_sig", 
        "X-Device-Timestamp": timestamp,
        "X-Force-Signature-Check": "true"
    }

    response = client.post(path, data={"user_id": "test"}, headers=headers)
    assert response.status_code == 401
    assert "Invalid device signature" in response.json()["detail"]


def test_whatsapp_draft_endpoint(client):
    # Note: This requires a note to exist. Since we are using an empty test DB,
    # it might return 404. Let's check if it handles 404 correctly.
    path = "/api/v1/notes/fake_note/whatsapp"
    query = "user_id=test_user"
    timestamp = str(int(time.time()))
    signature = generate_test_signature("GET", path, timestamp, query=query)
    headers = {
        "X-Device-Signature": signature,
        "X-Device-Timestamp": timestamp,
        "Authorization": "Bearer mock-admin-token",
    }

    response = client.get(f"{path}?{query}", headers=headers)
    assert response.status_code == 404


def test_conflict_detection_logic():
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
