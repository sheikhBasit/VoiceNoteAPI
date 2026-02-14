import os
import uuid
import time
import pytest
from fastapi.testclient import TestClient
from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.services.auth_service import get_current_user

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
        id=user_id, email=f"test_{user_id}@example.com", name="Test User",
        primary_role=models.UserRole.GENERIC
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_task(test_user, db_session):
    task_id = str(uuid.uuid4())
    task = models.Task(
        id=task_id, 
        user_id=test_user.id, 
        description="Test Task", 
        is_done=False,
        status=models.TaskStatus.TODO
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task

def test_task_complete_endpoint(test_user, test_task, db_session):
    """
    TDD: Test the new /tasks/{task_id}/complete endpoint.
    Expectation: Sets is_done=True and status=DONE.
    """
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    response = client.patch(f"/api/v1/tasks/{test_task.id}/complete")
    
    app.dependency_overrides.clear()
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_task.id
    assert data["is_done"] is True
    # In NoteStatus/TaskStatus enum, DONE should be represented
    assert data["status"] == "DONE"

    # Verify in DB
    db_session.refresh(test_task)
    assert test_task.is_done is True
    assert test_task.status.name == "DONE"

def test_task_statistics_alias(test_user):
    """
    TDD: Test the /tasks/statistics alias.
    Expectation: Returns 200 OK and valid statistics structure.
    """
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    response = client.get("/api/v1/tasks/statistics")
    
    app.dependency_overrides.clear()
    
    assert response.status_code == 200
    data = response.json()
    assert "total_tasks" in data
    assert "completed_tasks" in data

def test_user_login_alias():
    """
    TDD: Test the /users/login alias.
    Expectation: Returns 200 OK and valid sync response.
    """
    payload = {
        "name": "Login Test",
        "email": f"login_{uuid.uuid4()}@example.com",
        "token": "test_token",
        "device_id": "device_123",
        "device_model": "Android SDK",
        "primary_role": "GENERIC"
    }
    
    response = client.post("/api/v1/users/login", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["name"] == "Login Test"

def test_sync_user_with_password(db_session):
    """
    TDD: Test syncing a user with a password.
    Expectation: Password should be hashed and verified if provided in future syncs.
    """
    email = f"pass_{uuid.uuid4()}@example.com"
    payload = {
        "name": "Password User",
        "email": email,
        "password": "secure_password",
        "token": "test_token",
        "device_id": "device_456",
        "device_model": "Android SDK",
        "primary_role": "GENERIC"
    }
    
    # 1. First sync (Initial creation with password)
    response = client.post("/api/v1/users/sync", json=payload)
    assert response.status_code == 200
    
    # Verify in DB that password hash is set
    db_user = db_session.query(models.User).filter(models.User.email == email).first()
    assert db_user.password_hash is not None
    assert db_user.password_hash != "secure_password"
    
    # 2. Second sync with correct password (Success)
    response = client.post("/api/v1/users/sync", json=payload)
    assert response.status_code == 200
    
    # 3. Third sync with WRONG password (Failure)
    wrong_payload = payload.copy()
    wrong_payload["password"] = "wrong_password"
    response = client.post("/api/v1/users/sync", json=wrong_payload)
    assert response.status_code == 401
    assert "Incorrect password" in response.json()["detail"]

@pytest.fixture
def test_note(test_user, db_session):
    note_id = str(uuid.uuid4())
    note = models.Note(
        id=note_id,
        user_id=test_user.id,
        title="Comparison Note",
        summary="Summary",
        transcript_groq="Groq Transcript",
        transcript_deepgram="Deepgram Transcript",
        transcript_android="Android Transcript",
        timestamp=int(time.time() * 1000)
    )
    db_session.add(note)
    db_session.commit()
    db_session.refresh(note)
    return note

def test_get_note_verbose_transcripts(test_user, test_note):
    """
    TDD: Test retrieving a note with verbose transcripts.
    Expectation: transcript_groq etc. should be present ONLY if verbose=true.
    """
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # 1. Non-verbose check
    response = client.get(f"/api/v1/notes/{test_note.id}")
    assert response.status_code == 200
    data = response.json()
    assert "transcript_groq" not in data or data["transcript_groq"] is None
    
    # 2. Verbose check
    response = client.get(f"/api/v1/notes/{test_note.id}?verbose=true")
    assert response.status_code == 200
    data = response.json()
    assert data["transcript_groq"] == "Groq Transcript"
    assert data["transcript_deepgram"] == "Deepgram Transcript"
    assert data["transcript_android"] == "Android Transcript"
    
    app.dependency_overrides.clear()
