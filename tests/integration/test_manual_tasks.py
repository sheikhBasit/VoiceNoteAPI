import os

from dotenv import load_dotenv

# Load .env BEFORE importing app modules to ensure DB URL is correct
load_dotenv(dotenv_path="/home/basitdev/Me/StudioProjects/VoiceNoteAPI/.env")
print(f"DEBUG: DATABASE_URL from os.getenv: {os.getenv('DATABASE_URL')}")

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app

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
        id=user_id, email=f"test_{user_id}@example.com", name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_task_no_note(client, test_user): # Use client fixture
    # Mocking get_current_user to return our test_user
    from app.services.auth_service import get_current_user

    app.dependency_overrides[get_current_user] = lambda: test_user

    try:
        payload = {
            "description": "Standalone manual task",
            "priority": "HIGH",
            "note_id": None,
        }

        response = client.post("/api/v1/tasks/", json=payload)
        if response.status_code != 201:
            print(f"DEBUG: POST /api/v1/tasks/ failed with {response.status_code}")
            print(f"DEBUG: Response body: {os.linesep}{response.text}")
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Standalone manual task"
        assert data["note_id"] is None
        assert "id" in data
    finally:
        # Clean up only this override
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


def test_list_standalone_tasks(client, test_user, db_session): # Use client fixture
    # Create a task
    task_id = str(uuid.uuid4())
    task = models.Task(
        id=task_id, user_id=test_user.id, description="Task 1", note_id=None
    )
    db_session.add(task)
    db_session.commit()

    from app.services.auth_service import get_current_user

    app.dependency_overrides[get_current_user] = lambda: test_user

    try:
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        data = response.json()
        # Filter for our task in case there are others
        found = any(t["id"] == task_id for t in data)
        assert found, f"Task {task_id} not found in response"
    finally:
        if get_current_user in app.dependency_overrides:
             del app.dependency_overrides[get_current_user]
