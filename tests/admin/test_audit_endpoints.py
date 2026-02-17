"""
Phase 6 Admin Endpoint Tests
Tests for audit and activity log endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import create_access_token

client = TestClient(app)


# ============================================================================
# AUDIT & ACTIVITY LOG TESTS
# ============================================================================


class TestAuditEndpoints:
    """Tests for audit and activity log endpoints"""

    def test_get_recent_activity(self, admin_token):
        """GET /api/v1/admin/activity/recent"""
        response = client.get(
            "/api/v1/admin/activity/recent?hours=24&limit=10",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "recent_activity" in data
        assert "period_hours" in data
        assert "count" in data

    def test_get_admin_action_stats(self, admin_token):
        """GET /api/v1/admin/activity/stats"""
        response = client.get(
            "/api/v1/admin/activity/stats?days=30",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_actions" in data
        assert "action_counts" in data
        assert "top_admins" in data
        assert "period_days" in data

    def test_get_activity_timeline(self, admin_token):
        """GET /api/v1/admin/activity/timeline"""
        response = client.get(
            "/api/v1/admin/activity/timeline?days=7",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "timeline" in data
        assert "period_days" in data

    def test_dashboard_includes_activity(self, admin_token):
        """GET /api/v1/admin/dashboard/overview includes recent activity"""
        response = client.get(
            "/api/v1/admin/dashboard/overview",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify recent activity is included
        assert "recent_activity" in data
        assert isinstance(data["recent_activity"], list)


class TestAuditPermissions:
    """Tests for audit endpoint permissions"""

    def test_activity_non_admin(self, test_user):
        """Test activity endpoints with non-admin user"""
        token = create_access_token(data={"sub": test_user.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            "/api/v1/admin/activity/recent",
            headers=headers
        )
        assert response.status_code == 403

    def test_activity_no_auth(self):
        """Test activity endpoints without authentication"""
        response = client.get("/api/v1/admin/activity/recent")
        assert response.status_code == 401
