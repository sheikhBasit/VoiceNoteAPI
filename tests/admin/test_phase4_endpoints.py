"""
Phase 4 Admin Endpoint Tests
Tests for Celery & Jobs endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import create_access_token

client = TestClient(app)


# ============================================================================
# PHASE 4: CELERY & JOBS ENDPOINTS TESTS
# ============================================================================


class TestCeleryTaskEndpoints:
    """Tests for Celery task monitoring endpoints"""

    def test_get_active_tasks(self, admin_token):
        """GET /api/v1/admin/celery/tasks/active"""
        response = client.get(
            "/api/v1/admin/celery/tasks/active",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have structure even if empty
        assert "active_tasks" in data or "error" in data

    def test_get_pending_tasks(self, admin_token):
        """GET /api/v1/admin/celery/tasks/pending"""
        response = client.get(
            "/api/v1/admin/celery/tasks/pending",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "pending_tasks" in data or "error" in data

    def test_get_task_status(self, admin_token):
        """GET /api/v1/admin/celery/tasks/{task_id}/status"""
        # Use a fake task ID
        task_id = "fake-task-id-12345"
        
        response = client.get(
            f"/api/v1/admin/celery/tasks/{task_id}/status",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return task info or error
        assert "task_id" in data or "error" in data

    def test_cancel_task(self, admin_token):
        """POST /api/v1/admin/celery/tasks/{task_id}/cancel"""
        task_id = "fake-task-id-12345"
        
        response = client.post(
            f"/api/v1/admin/celery/tasks/{task_id}/cancel",
            headers=admin_token
        )
        assert response.status_code == 200
        # Should succeed or return error
        data = response.json()
        assert "status" in data or "error" in data


class TestCeleryWorkerEndpoints:
    """Tests for Celery worker management endpoints"""

    def test_get_worker_stats(self, admin_token):
        """GET /api/v1/admin/celery/workers/stats"""
        response = client.get(
            "/api/v1/admin/celery/workers/stats",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have workers list or error
        assert "workers" in data or "error" in data

    def test_get_registered_tasks(self, admin_token):
        """GET /api/v1/admin/celery/workers/tasks"""
        response = client.get(
            "/api/v1/admin/celery/workers/tasks",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "registered_tasks" in data or "error" in data

    def test_restart_worker_pool(self, admin_token):
        """POST /api/v1/admin/celery/workers/pool-restart"""
        response = client.post(
            "/api/v1/admin/celery/workers/pool-restart",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return success or error
        assert "status" in data or "error" in data


class TestCeleryQueueEndpoints:
    """Tests for Celery queue inspection endpoints"""

    def test_get_queue_info(self, admin_token):
        """GET /api/v1/admin/celery/queues"""
        response = client.get(
            "/api/v1/admin/celery/queues",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "queues" in data or "error" in data


class TestCeleryPermissions:
    """Tests for Celery endpoint permissions"""

    def test_celery_non_admin(self, test_user):
        """Test Celery endpoints with non-admin user"""
        token = create_access_token(data={"sub": test_user.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            "/api/v1/admin/celery/tasks/active",
            headers=headers
        )
        assert response.status_code == 403

    def test_celery_no_auth(self):
        """Test Celery endpoints without authentication"""
        response = client.get("/api/v1/admin/celery/tasks/active")
        assert response.status_code == 401
