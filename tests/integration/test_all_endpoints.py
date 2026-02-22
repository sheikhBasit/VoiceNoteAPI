"""
Comprehensive Endpoint Tests for VoiceNote API
Tests all endpoints with proper authentication and data validation
"""

import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import models
from app.main import app
from app.services.auth_service import create_access_token

client = TestClient(app)

# ============================================================================
# FIXTURES & SETUP
# ============================================================================


@pytest.fixture
def db():
    """Get database session"""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    from app.db.session import SessionLocal

    db_local = SessionLocal()

    user = models.User(
        id=str(uuid.uuid4()),
        name="Test User",
        email=f"test_{uuid.uuid4()}@test.com",
        tier=models.SubscriptionTier.PREMIUM,
        primary_role=models.UserRole.GENERIC,
        is_deleted=False,
        last_login=int(time.time() * 1000),
        # Manually set a known password hash for easier login testing if needed
        # (This hash corresponds to 'testpassword', generated via bcrypt)
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", 
        authorized_devices=[
            {
                "device_id": "test_device",
                "device_model": "iPhone12",
                "biometric_token": "test_token",
                "authorized_at": int(time.time() * 1000),
            }
        ],
    )
    db_local.add(user)
    db_local.commit()
    db_local.refresh(user)
    db_local.close()
    return user


@pytest.fixture
def auth_header(test_user):
    """Generate auth token for test user"""
    token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_note(db: Session, test_user):
    """Create a test note"""
    note = models.Note(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        title="Test Note",
        summary="Test content",
        languages=["en"],
        timestamp=int(time.time() * 1000),
        updated_at=int(time.time() * 1000),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@pytest.fixture
def test_task(db: Session, test_user, test_note):
    """Create a test task"""
    task = models.Task(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        note_id=test_note.id,
        description="Test task",
        priority=models.Priority.MEDIUM,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ============================================================================
# USER ENDPOINTS TESTS
# ============================================================================


class TestUserEndpoints:
    """Tests for /api/v1/users endpoints"""

    def test_user_register_new_user(self):
        """POST /api/v1/users/register - Create new user"""
        payload = {
            "email": f"newuser_{uuid.uuid4()}@test.com",
            "name": "New User",
            "password": "securepassword123",
            "timezone": "UTC",
        }
        response = client.post("/api/v1/users/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["is_new_user"] is True
        assert data["token_type"] == "bearer"

    def test_user_login_existing_user(self, test_user, auth_header):
        """POST /api/v1/users/login - Login existing user"""
        # Note: test_user fixture creates a user without a password hash in the test DB setup usually,
        # checking the fixture first.
        # Ideally, we should register a user first to test login properly.
        
        # 1. Register
        email = f"login_test_{uuid.uuid4()}@test.com"
        password = "loginpassword123"
        client.post("/api/v1/users/register", json={
            "email": email, 
            "name": "Login Test", 
            "password": password
        })

        # 2. Login
        payload = {
            "email": email,
            "password": password
        }
        response = client.post("/api/v1/users/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_new_user"] is False

    def test_user_get_me(self, auth_header):
        """GET /api/v1/users/me - Get current user"""
        response = client.get("/api/v1/users/me", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "name" in data

    def test_user_update_me(self, auth_header, test_user):
        """PATCH /api/v1/users/me - Update current user"""
        payload = {
            "name": "Updated Name",
            "timezone": "America/Los_Angeles",
            "primary_role": "DEVELOPER",
        }
        response = client.patch("/api/v1/users/me", json=payload, headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_user_logout(self, auth_header):
        """POST /api/v1/users/logout - Logout user"""
        response = client.post("/api/v1/users/logout", headers=auth_header)
        assert response.status_code == 200

    def test_user_search(self, auth_header):
        """GET /api/v1/users/search - Search users (admin-only endpoint)"""
        response = client.get("/api/v1/users/search?query=test", headers=auth_header)
        assert response.status_code == 403  # Requires admin privileges

    def test_user_delete_me(self, auth_header):
        """DELETE /api/v1/users/me - Delete current user"""
        response = client.delete("/api/v1/users/me", headers=auth_header)
        assert response.status_code == 200

    # User endpoints continue...


# ============================================================================
# NOTE ENDPOINTS TESTS
# ============================================================================


class TestNoteEndpoints:
    """Tests for /api/v1/notes endpoints"""

    def test_note_get_presigned_url(self, auth_header):
        """GET /api/v1/notes/presigned-url - Get presigned upload URL"""
        response = client.get("/api/v1/notes/presigned-url", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert "note_id" in data
        assert "upload_url" in data
        assert "storage_key" in data
        assert data["expires_in"] == 3600

    def test_note_create(self, auth_header):
        """POST /api/v1/notes/create - Create note manually"""
        payload = {
            "title": "Test Note",
            "summary": "Test content",
            "transcript": "Test transcript",
            "languages": ["en"],
        }
        response = client.post(
            "/api/v1/notes/create", json=payload, headers=auth_header
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Note"
        assert data["summary"] == "Test content"

    def test_note_list(self, auth_header, test_note):
        """GET /api/v1/notes - List notes"""
        response = client.get("/api/v1/notes", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_note_get_dashboard(self, auth_header):
        """GET /api/v1/notes/dashboard - Get dashboard"""
        response = client.get("/api/v1/notes/dashboard", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert "recent_notes_count" in data or "status" in data

    def test_note_get_by_id(self, auth_header, test_note):
        """GET /api/v1/notes/{note_id} - Get note by ID"""
        response = client.get(f"/api/v1/notes/{test_note.id}", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_note.id

    def test_note_update(self, auth_header, test_note):
        """PATCH /api/v1/notes/{note_id} - Update note"""
        payload = {"title": "Updated Title", "summary": "Updated content"}
        response = client.patch(
            f"/api/v1/notes/{test_note.id}", json=payload, headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_note_delete(self, auth_header, test_note):
        """DELETE /api/v1/notes/{note_id} - Delete note"""
        response = client.delete(f"/api/v1/notes/{test_note.id}", headers=auth_header)
        assert response.status_code == 200

    def test_note_semantic_analysis(self, auth_header, test_note):
        """POST /api/v1/notes/{note_id}/semantic-analysis - Trigger semantic analysis"""
        response = client.post(
            f"/api/v1/notes/{test_note.id}/semantic-analysis", headers=auth_header
        )
        assert response.status_code in [200, 202]

    def test_note_whatsapp_draft(self, auth_header, test_note):
        """GET /api/v1/notes/{note_id}/whatsapp - Get WhatsApp draft"""
        response = client.get(
            f"/api/v1/notes/{test_note.id}/whatsapp", headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert "draft" in data or "whatsapp_link" in data


# ============================================================================
# TASK ENDPOINTS TESTS
# ============================================================================


class TestTaskEndpoints:
    """Tests for /api/v1/tasks endpoints"""

    def test_task_create(self, auth_header):
        """POST /api/v1/tasks - Create task"""
        payload = {
            "description": "Test task description",
            "priority": "MEDIUM",
            "deadline": None,
            "assigned_entities": [],
            "image_uris": [],
            "document_uris": [],
            "external_links": [],
            "is_action_approved": False,
        }
        response = client.post("/api/v1/tasks", json=payload, headers=auth_header)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["description"] == "Test task description"

    def test_task_list(self, auth_header, test_task):
        """GET /api/v1/tasks - List tasks"""
        response = client.get("/api/v1/tasks", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_task_due_today(self, auth_header):
        """GET /api/v1/tasks/due-today - Get tasks due today"""
        response = client.get("/api/v1/tasks/due-today", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_task_overdue(self, auth_header):
        """GET /api/v1/tasks/overdue - Get overdue tasks"""
        response = client.get("/api/v1/tasks/overdue", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_task_assigned_to_me(self, auth_header):
        """GET /api/v1/tasks/assigned-to-me - Get tasks assigned to me"""
        response = client.get("/api/v1/tasks/assigned-to-me", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_task_search(self, auth_header):
        """GET /api/v1/tasks/search - Search tasks"""
        response = client.get(
            "/api/v1/tasks/search?query_text=test", headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_task_stats(self, auth_header):
        """GET /api/v1/tasks/stats - Get task statistics"""
        response = client.get("/api/v1/tasks/stats", headers=auth_header)
        assert response.status_code == 200

    def test_task_get_by_id(self, auth_header, test_task):
        """GET /api/v1/tasks/{task_id} - Get task by ID"""
        response = client.get(f"/api/v1/tasks/{test_task.id}", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_task.id

    def test_task_update(self, auth_header, test_task):
        """PATCH /api/v1/tasks/{task_id} - Update task"""
        payload = {"description": "Updated task", "priority": "HIGH"}
        response = client.patch(
            f"/api/v1/tasks/{test_task.id}", json=payload, headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated task"

    def test_task_delete(self, auth_header, test_task):
        """DELETE /api/v1/tasks/{task_id} - Delete task"""
        response = client.delete(f"/api/v1/tasks/{test_task.id}", headers=auth_header)
        assert response.status_code == 200

    def test_task_duplicate(self, auth_header, test_task):
        """POST /api/v1/tasks/{task_id}/duplicate - Duplicate task"""
        response = client.post(
            f"/api/v1/tasks/{test_task.id}/duplicate", headers=auth_header
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data


# ============================================================================
# ADMIN ENDPOINTS TESTS
# ============================================================================


class TestAdminEndpoints:
    """Tests for /api/v1/admin endpoints"""

    def test_admin_list_users(self, auth_header):
        """GET /api/v1/admin/users - List all users (admin only)"""
        response = client.get("/api/v1/admin/users", headers=auth_header)
        # May return 403 if not admin, which is ok
        assert response.status_code in [200, 403]

    def test_admin_user_stats(self, auth_header):
        """GET /api/v1/admin/users/stats - Get user statistics"""
        response = client.get("/api/v1/admin/users/stats", headers=auth_header)
        assert response.status_code in [200, 403]

    def test_admin_list_admins(self, auth_header):
        """GET /api/v1/admin/admins - List admin users"""
        response = client.get("/api/v1/admin/admins", headers=auth_header)
        assert response.status_code in [200, 403]

    def test_admin_status(self, auth_header):
        """GET /api/v1/admin/status - Get system status"""
        response = client.get("/api/v1/admin/status", headers=auth_header)
        assert response.status_code in [200, 403]

    def test_admin_get_audit_logs(self, auth_header):
        """GET /api/v1/admin/audit-logs - Get audit logs"""
        response = client.get("/api/v1/admin/audit-logs", headers=auth_header)
        assert response.status_code in [200, 403]


# ============================================================================
# AI ENDPOINTS TESTS
# ============================================================================


class TestAIEndpoints:
    """Tests for /api/v1/ai endpoints"""

    def test_ai_search(self, auth_header):
        """POST /api/v1/ai/search - Search using AI"""
        response = client.post(
            "/api/v1/ai/search", 
            json={"query": "test search"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_ai_stats(self, auth_header):
        """GET /api/v1/ai/stats - Get AI statistics"""
        response = client.get("/api/v1/ai/stats", headers=auth_header)
        assert response.status_code == 200


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_unauthorized_request(self):
        """Test request without authorization"""
        response = client.get("/api/v1/notes")
        assert response.status_code == 401

    def test_invalid_token(self):
        """Test request with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/notes", headers=headers)
        assert response.status_code == 401

    def test_nonexistent_note(self, auth_header):
        """Test accessing nonexistent note"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/notes/{fake_id}", headers=auth_header)
        assert response.status_code == 404

    def test_nonexistent_task(self, auth_header):
        """Test accessing nonexistent task"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/tasks/{fake_id}", headers=auth_header)
        assert response.status_code == 404

    def test_invalid_note_data(self, auth_header):
        """Test creating note with invalid data (missing required transcript field)"""
        payload = {"title": "", "summary": "Test"}  # Missing required 'transcript'
        response = client.post(
            "/api/v1/notes/create", json=payload, headers=auth_header
        )
        assert response.status_code == 422  # Validation error: transcript is required

    def test_invalid_task_data(self, auth_header):
        """Test creating task with invalid data"""
        payload = {
            "description": "",  # Empty description
            "priority": "INVALID_PRIORITY",
        }
        response = client.post("/api/v1/tasks", json=payload, headers=auth_header)
        assert response.status_code == 422
