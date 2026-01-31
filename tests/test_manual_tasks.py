import os
from dotenv import load_dotenv
# Load .env BEFORE importing app modules to ensure DB URL is correct
load_dotenv(dotenv_path="/home/basitdev/Me/StudioProjects/VoiceNoteAPI/.env")
print(f"DEBUG: DATABASE_URL from os.getenv: {os.getenv('DATABASE_URL')}")

from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.db.session import sync_engine as engine, SessionLocal
from app.db import models
import uuid
import time

client = TestClient(app)

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def test_user(db_session):
    user_id = str(uuid.uuid4())
    user = models.User(
        id=user_id,
        email=f"test_{user_id}@example.com",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user

def get_auth_headers(user_id):
    # Simulated auth - depends on your auth implementation
    # Assuming the app has a way to bypass for tests or uses JWT
    # For now, let's assume get_current_user can be mocked or we use a real token
    # Since I cannot easily generate a JWT here without the secret, I will assume 
    # the environment allows some form of test auth or I can mock it in the test.
    pass

def test_create_task_no_note(test_user):
    # Mocking get_current_user to return our test_user
    from app.services.auth_service import get_current_user
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    payload = {
        "description": "Standalone manual task",
        "priority": "HIGH",
        "note_id": None
    }
    
    response = client.post("/api/v1/tasks/", json=payload)
    if response.status_code != 201:
        print(f"DEBUG: POST /api/v1/tasks/ failed with {response.status_code}")
        print(f"DEBUG: Response body: {os.linesep}{response.text}")
    app.dependency_overrides.clear()
    
    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Standalone manual task"
    assert data["note_id"] is None
    assert "id" in data

def test_list_standalone_tasks(test_user, db_session):
    # Create a task
    task_id = str(uuid.uuid4())
    task = models.Task(
        id=task_id,
        user_id=test_user.id,
        description="Task 1",
        note_id=None
    )
    db_session.add(task)
    db_session.commit()
    
    from app.services.auth_service import get_current_user
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    response = client.get("/api/v1/tasks")
    app.dependency_overrides.clear()
    
    assert response.status_code == 200
    data = response.json()
    assert any(t["id"] == task_id for t in data)
