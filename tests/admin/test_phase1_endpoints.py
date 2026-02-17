"""
Comprehensive Admin Endpoint Tests for VoiceNote API
Tests Phase 1 critical admin endpoints
"""

import time
import uuid
from typing import List

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
def admin_user(db: Session):
    """Create an admin user"""
    user = models.User(
        id=str(uuid.uuid4()),
        name="Admin User",
        email=f"admin_{uuid.uuid4()}@test.com",
        tier=models.SubscriptionTier.PREMIUM,
        primary_role=models.UserRole.GENERIC,
        is_admin=True,
        is_deleted=False,
        last_login=int(time.time() * 1000),
        admin_permissions={
            "can_view_all_users": True,
            "can_view_all_notes": True,
            "can_delete_users": True,
            "can_delete_notes": True,
            "can_manage_admins": True,
            "can_view_analytics": True,
            "can_modify_system_settings": True,
        },
        authorized_devices=[
            {
                "device_id": "admin_device",
                "device_model": "Admin Console",
                "biometric_token": "admin_token",
                "authorized_at": int(time.time() * 1000),
            }
        ],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Generate admin auth token"""
    token = create_access_token(data={"sub": admin_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(db: Session):
    """Create a regular test user"""
    user = models.User(
        id=str(uuid.uuid4()),
        name="Test User",
        email=f"test_{uuid.uuid4()}@test.com",
        tier=models.SubscriptionTier.FREE,
        primary_role=models.UserRole.GENERIC,
        is_deleted=False,
        last_login=int(time.time() * 1000),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_note(db: Session, test_user):
    """Create a test note"""
    note = models.Note(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        title="Test Note",
        summary="Test content",
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
# PHASE 1: CRITICAL ENDPOINTS TESTS
# ============================================================================


class TestDashboardEndpoints:
    """Tests for dashboard and metrics endpoints"""

    def test_dashboard_overview(self, admin_token):
        """GET /api/v1/admin/dashboard/overview"""
        response = client.get(
            "/api/v1/admin/dashboard/overview",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "users" in data
        assert "content" in data
        assert "activity" in data
        assert "system" in data
        assert "revenue" in data
        
        # Verify user metrics
        assert "total" in data["users"]
        assert "active" in data["users"]
        assert "new_this_month" in data["users"]
        
        # Verify content metrics
        assert "total_notes" in data["content"]
        assert "total_tasks" in data["content"]
        
        # Verify system health
        assert "database_status" in data["system"]

    def test_dashboard_overview_non_admin(self, test_user):
        """Test dashboard overview with non-admin user"""
        token = create_access_token(data={"sub": test_user.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            "/api/v1/admin/dashboard/overview",
            headers=headers
        )
        assert response.status_code == 403

    def test_realtime_metrics(self, admin_token):
        """GET /api/v1/admin/metrics/realtime"""
        response = client.get(
            "/api/v1/admin/metrics/realtime",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "current_users_online" in data
        assert "api_requests_per_minute" in data
        assert "notes_processing_now" in data
        assert "timestamp" in data

    def test_system_health(self, admin_token):
        """GET /api/v1/admin/system/health"""
        response = client.get(
            "/api/v1/admin/system/health",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in data
        assert "database" in data["components"]
        assert "redis" in data["components"]
        assert "celery" in data["components"]

    def test_list_admin_tasks(self, admin_token, test_task):
        """GET /api/v1/admin/tasks"""
        response = client.get(
            "/api/v1/admin/tasks?limit=10",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    def test_delete_admin_task(self, admin_token, test_task):
        """DELETE /api/v1/admin/tasks/{task_id}"""
        response = client.delete(
            f"/api/v1/admin/tasks/{test_task.id}?reason=Test deletion",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_restore_admin_task(self, admin_token, db, test_task):
        """PATCH /api/v1/admin/tasks/{task_id}/restore"""
        # First delete it
        test_task.is_deleted = True
        db.commit()
        
        response = client.patch(
            f"/api/v1/admin/tasks/{test_task.id}/restore",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_create_test_note(self, admin_token, test_user):
        """POST /api/v1/admin/notes/create"""
        response = client.post(
            f"/api/v1/admin/notes/create?user_id={test_user.id}&title=Admin Test Note&summary=Created from dashboard",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "note" in data


# ============================================================================
# ERROR HANDLING & EDGE CASES
# ============================================================================


class TestAdminErrorHandling:
    """Tests for error handling and edge cases"""

    def test_dashboard_without_auth(self):
        """Test dashboard without authentication"""
        response = client.get("/api/v1/admin/dashboard/overview")
        assert response.status_code == 401

    def test_invalid_task_id(self, admin_token):
        """Test accessing nonexistent task"""
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/admin/tasks/{fake_id}?reason=test",
            headers=admin_token
        )
        assert response.status_code == 404

    def test_create_note_invalid_user(self, admin_token):
        """Test creating note for nonexistent user"""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/admin/notes/create?user_id={fake_id}",
            headers=admin_token
        )
        assert response.status_code == 404
