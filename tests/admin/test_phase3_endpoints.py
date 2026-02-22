"""
Phase 3 Admin Endpoint Tests
Tests for analytics endpoints
"""

import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import models
from app.main import app
from app.services.auth_service import create_access_token

client = TestClient(app)


# ============================================================================
# PHASE 3: ANALYTICS ENDPOINTS TESTS
# ============================================================================


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints"""

    def test_usage_analytics(self, admin_token):
        """GET /api/v1/admin/analytics/usage"""
        # Last 30 days
        end_date = int(time.time() * 1000)
        start_date = int((time.time() - 30 * 24 * 60 * 60) * 1000)
        
        response = client.get(
            f"/api/v1/admin/analytics/usage?start_date={start_date}&end_date={end_date}&group_by=day",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_audio_minutes" in data
        assert "total_api_calls" in data
        assert "notes_created" in data
        assert "tasks_created" in data
        assert "active_users" in data
        assert "usage_by_period" in data

    def test_usage_analytics_invalid_group_by(self, admin_token):
        """GET /api/v1/admin/analytics/usage with invalid group_by"""
        end_date = int(time.time() * 1000)
        start_date = int((time.time() - 30 * 24 * 60 * 60) * 1000)
        
        response = client.get(
            f"/api/v1/admin/analytics/usage?start_date={start_date}&end_date={end_date}&group_by=invalid",
            headers=admin_token
        )
        assert response.status_code == 422  # FastAPI validation error for invalid pattern

    def test_growth_analytics(self, admin_token):
        """GET /api/v1/admin/analytics/growth"""
        response = client.get(
            "/api/v1/admin/analytics/growth",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "signups_by_month" in data
        assert "tier_distribution" in data
        assert "retention" in data
        assert "churn" in data

    def test_revenue_report(self, admin_token):
        """GET /api/v1/admin/reports/revenue"""
        end_date = int(time.time() * 1000)
        start_date = int((time.time() - 30 * 24 * 60 * 60) * 1000)
        
        response = client.get(
            f"/api/v1/admin/reports/revenue?start_date={start_date}&end_date={end_date}",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_revenue" in data
        assert "total_expenses" in data
        assert "net_revenue" in data
        assert "revenue_by_tier" in data
        assert "arpu" in data

    def test_user_behavior_analytics(self, admin_token):
        """GET /api/v1/admin/analytics/user-behavior"""
        response = client.get(
            "/api/v1/admin/analytics/user-behavior",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "top_users_by_notes" in data
        assert "averages" in data
        assert "peak_usage_hours" in data
        assert "feature_usage" in data

    def test_system_metrics(self, admin_token):
        """GET /api/v1/admin/analytics/system-metrics"""
        response = client.get(
            "/api/v1/admin/analytics/system-metrics",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "storage" in data
        assert "database" in data


class TestAnalyticsPermissions:
    """Tests for analytics permission enforcement"""

    def test_analytics_non_admin(self, test_user):
        """Test analytics with non-admin user"""
        token = create_access_token(data={"sub": test_user.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            "/api/v1/admin/analytics/growth",
            headers=headers
        )
        assert response.status_code == 403

    def test_analytics_no_auth(self):
        """Test analytics without authentication"""
        response = client.get("/api/v1/admin/analytics/growth")
        assert response.status_code == 401
