"""
Critical Fixes Verification Tests

Tests that verify all critical issues are properly fixed:
1. sync.py imports correctly
2. admin.py toggle_wallet_freeze is async
3. billing_service.py charge_usage completes full audit trail
4. Admin wallet endpoints (freeze, unfreeze, toggle-freeze)
5. Admin revenue report endpoint is routable
6. Admin create_organization uses Pydantic validation
"""

import inspect
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import models
from app.services.auth_service import create_access_token


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def admin_user(db_session: Session):
    """Create a full-privilege admin user."""
    user = models.User(
        id=str(uuid.uuid4()),
        name="Fix Test Admin",
        email=f"fixadmin_{uuid.uuid4().hex[:8]}@test.com",
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
            "can_manage_wallets": True,
        },
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user):
    """Generate admin auth headers."""
    token = create_access_token(data={"sub": admin_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regular_user(db_session: Session):
    """Create a regular (non-admin) user."""
    user = models.User(
        id=str(uuid.uuid4()),
        name="Regular User",
        email=f"regular_{uuid.uuid4().hex[:8]}@test.com",
        tier=models.SubscriptionTier.FREE,
        primary_role=models.UserRole.GENERIC,
        is_deleted=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_with_wallet(db_session: Session):
    """Create a user with an associated wallet."""
    user_id = str(uuid.uuid4())
    user = models.User(
        id=user_id,
        name="Wallet User",
        email=f"wallet_{uuid.uuid4().hex[:8]}@test.com",
        tier=models.SubscriptionTier.FREE,
        primary_role=models.UserRole.GENERIC,
        is_deleted=False,
    )
    db_session.add(user)
    db_session.flush()

    wallet = models.Wallet(
        user_id=user_id,
        balance=500,
        is_frozen=False,
    )
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# FIX 1: sync.py imports correctly
# ============================================================================


class TestSyncModuleImport:
    """Verify sync.py can be imported without errors."""

    def test_sync_module_imports(self):
        """sync.py should import without ImportError."""
        from app.api import sync

        assert hasattr(sync, "router")
        assert hasattr(sync, "upload_batch")

    def test_sync_uses_correct_auth_dependency(self):
        """sync.py should use get_current_user from auth_service."""
        from app.api.sync import upload_batch

        # Verify function signature includes current_user parameter
        sig = inspect.signature(upload_batch)
        assert "current_user" in sig.parameters

    def test_sync_router_has_upload_batch(self):
        """The sync router should have the upload-batch endpoint."""
        from app.api.sync import router

        routes = [r.path for r in router.routes]
        assert "/api/v1/sync/upload-batch" in routes


# ============================================================================
# FIX 2: admin.py toggle_wallet_freeze is async
# ============================================================================


class TestToggleWalletFreezeIsAsync:
    """Verify toggle_wallet_freeze is an async function."""

    def test_toggle_wallet_freeze_is_coroutine(self):
        """toggle_wallet_freeze should be an async function."""
        from app.api.admin import toggle_wallet_freeze

        assert inspect.iscoroutinefunction(toggle_wallet_freeze), (
            "toggle_wallet_freeze must be async def, not def"
        )

    def test_all_admin_route_handlers_are_async(self):
        """All admin route handlers should be async."""
        from app.api.admin import router

        for route in router.routes:
            if hasattr(route, "endpoint"):
                assert inspect.iscoroutinefunction(route.endpoint), (
                    f"Route handler {route.endpoint.__name__} should be async"
                )


# ============================================================================
# FIX 3: billing_service charge_usage completes full audit trail
# ============================================================================


class TestBillingServiceAuditTrail:
    """Verify billing service records full audit trail."""

    def test_charge_usage_creates_transaction(self, db_session: Session):
        """charge_usage should create a Transaction record."""
        from app.services.billing_service import BillingService

        # Create user with wallet
        user_id = str(uuid.uuid4())
        user = models.User(
            id=user_id,
            name="Billing Test User",
            email=f"billing_{uuid.uuid4().hex[:8]}@test.com",
            tier=models.SubscriptionTier.FREE,
            primary_role=models.UserRole.GENERIC,
        )
        db_session.add(user)
        db_session.flush()

        wallet = models.Wallet(user_id=user_id, balance=500)
        db_session.add(wallet)
        db_session.commit()

        billing = BillingService(db_session)
        result = billing.charge_usage(
            user_id=user_id,
            cost=10,
            description="test:charge",
            audio_duration=60.0,
        )

        assert result is True

        # Verify transaction was created
        tx = (
            db_session.query(models.Transaction)
            .filter(models.Transaction.wallet_id == user_id)
            .first()
        )
        assert tx is not None
        assert tx.amount == -10
        assert tx.type == "USAGE"

    def test_charge_usage_creates_usage_log(self, db_session: Session):
        """charge_usage should create a UsageLog record."""
        from app.services.billing_service import BillingService

        user_id = str(uuid.uuid4())
        user = models.User(
            id=user_id,
            name="Usage Log Test",
            email=f"usage_{uuid.uuid4().hex[:8]}@test.com",
            tier=models.SubscriptionTier.FREE,
            primary_role=models.UserRole.GENERIC,
        )
        db_session.add(user)
        db_session.flush()

        wallet = models.Wallet(user_id=user_id, balance=500)
        db_session.add(wallet)
        db_session.commit()

        billing = BillingService(db_session)
        billing.charge_usage(
            user_id=user_id,
            cost=15,
            description="transcription:test",
            audio_duration=120.0,
        )

        usage_log = (
            db_session.query(models.UsageLog)
            .filter(models.UsageLog.user_id == user_id)
            .first()
        )
        assert usage_log is not None
        assert usage_log.cost_estimated == 15
        assert usage_log.duration_seconds == 120

    def test_charge_usage_updates_user_stats(self, db_session: Session):
        """charge_usage should update user.usage_stats."""
        from app.services.billing_service import BillingService

        user_id = str(uuid.uuid4())
        user = models.User(
            id=user_id,
            name="Stats Test",
            email=f"stats_{uuid.uuid4().hex[:8]}@test.com",
            tier=models.SubscriptionTier.FREE,
            primary_role=models.UserRole.GENERIC,
        )
        db_session.add(user)
        db_session.flush()

        wallet = models.Wallet(user_id=user_id, balance=500)
        db_session.add(wallet)
        db_session.commit()

        billing = BillingService(db_session)
        billing.charge_usage(
            user_id=user_id,
            cost=5,
            description="test:stats",
            audio_duration=180.0,
        )

        db_session.refresh(user)
        assert user.usage_stats is not None
        assert user.usage_stats.get("total_audio_minutes", 0) > 0
        assert user.usage_stats.get("last_usage_at") is not None

    def test_charge_usage_deducts_balance(self, db_session: Session):
        """charge_usage should correctly deduct from wallet balance."""
        from app.services.billing_service import BillingService

        user_id = str(uuid.uuid4())
        user = models.User(
            id=user_id,
            name="Balance Test",
            email=f"balance_{uuid.uuid4().hex[:8]}@test.com",
            tier=models.SubscriptionTier.FREE,
            primary_role=models.UserRole.GENERIC,
        )
        db_session.add(user)
        db_session.flush()

        wallet = models.Wallet(user_id=user_id, balance=100)
        db_session.add(wallet)
        db_session.commit()

        billing = BillingService(db_session)
        billing.charge_usage(user_id=user_id, cost=30, description="test:deduct")

        db_session.refresh(wallet)
        assert wallet.balance == 70

    def test_charge_usage_insufficient_funds(self, db_session: Session):
        """charge_usage should return False if insufficient funds."""
        from app.services.billing_service import BillingService

        user_id = str(uuid.uuid4())
        user = models.User(
            id=user_id,
            name="Insufficient Test",
            email=f"insuff_{uuid.uuid4().hex[:8]}@test.com",
            tier=models.SubscriptionTier.FREE,
            primary_role=models.UserRole.GENERIC,
        )
        db_session.add(user)
        db_session.flush()

        wallet = models.Wallet(user_id=user_id, balance=5)
        db_session.add(wallet)
        db_session.commit()

        billing = BillingService(db_session)
        result = billing.charge_usage(user_id=user_id, cost=100, description="test:insuff")

        assert result is False


# ============================================================================
# FIX 4: Admin wallet endpoints
# ============================================================================


class TestAdminWalletEndpoints:
    """Test admin wallet freeze/unfreeze/toggle endpoints."""

    def test_toggle_freeze_wallet(self, client, admin_headers, user_with_wallet, db_session):
        """POST /admin/wallets/{user_id}/toggle-freeze should toggle wallet frozen state."""
        resp = client.post(
            f"/api/v1/admin/wallets/{user_with_wallet.id}/toggle-freeze",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "is_frozen" in data
        assert data["is_frozen"] is True  # Was False, now toggled to True

    def test_toggle_freeze_twice(self, client, admin_headers, user_with_wallet, db_session):
        """Toggling twice should return to original state."""
        # First toggle: False -> True
        resp1 = client.post(
            f"/api/v1/admin/wallets/{user_with_wallet.id}/toggle-freeze",
            headers=admin_headers,
        )
        assert resp1.json()["is_frozen"] is True

        # Second toggle: True -> False
        resp2 = client.post(
            f"/api/v1/admin/wallets/{user_with_wallet.id}/toggle-freeze",
            headers=admin_headers,
        )
        assert resp2.json()["is_frozen"] is False

    def test_toggle_freeze_nonexistent_wallet(self, client, admin_headers):
        """Toggle on nonexistent wallet should return 404."""
        resp = client.post(
            "/api/v1/admin/wallets/nonexistent-user-id/toggle-freeze",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_freeze_wallet(self, client, admin_headers, user_with_wallet):
        """POST /admin/wallets/{user_id}/freeze should freeze wallet."""
        resp = client.post(
            f"/api/v1/admin/wallets/{user_with_wallet.id}/freeze",
            headers=admin_headers,
            params={"reason": "Suspicious activity"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["is_frozen"] is True

    def test_unfreeze_wallet(self, client, admin_headers, user_with_wallet, db_session):
        """POST /admin/wallets/{user_id}/unfreeze should unfreeze wallet."""
        # First freeze
        wallet = db_session.query(models.Wallet).filter(
            models.Wallet.user_id == user_with_wallet.id
        ).first()
        wallet.is_frozen = True
        db_session.commit()

        resp = client.post(
            f"/api/v1/admin/wallets/{user_with_wallet.id}/unfreeze",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["is_frozen"] is False

    def test_freeze_nonexistent_wallet(self, client, admin_headers):
        """Freeze on nonexistent wallet should return 404."""
        resp = client.post(
            "/api/v1/admin/wallets/no-such-user/freeze",
            headers=admin_headers,
            params={"reason": "test"},
        )
        assert resp.status_code == 404

    def test_wallet_endpoints_require_admin(self, client, regular_user):
        """Wallet endpoints should reject non-admin users."""
        token = create_access_token(data={"sub": regular_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/v1/admin/wallets/some-user/toggle-freeze",
            headers=headers,
        )
        assert resp.status_code == 403


# ============================================================================
# FIX 5: Admin revenue report endpoint has route decorator
# ============================================================================


class TestRevenueReportEndpoint:
    """Test revenue report endpoint is reachable and functional."""

    def test_revenue_report_route_exists(self):
        """Revenue report route should be registered on the admin router."""
        from app.api.admin import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/admin/reports/revenue" in routes

    def test_revenue_report_endpoint(self, client, admin_headers):
        """GET /admin/reports/revenue should return data."""
        now = int(time.time() * 1000)
        thirty_days_ago = now - (30 * 24 * 60 * 60 * 1000)

        resp = client.get(
            "/api/v1/admin/reports/revenue",
            headers=admin_headers,
            params={"start_date": thirty_days_ago, "end_date": now},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should return a dict with revenue data
        assert isinstance(data, dict)

    def test_revenue_report_requires_admin(self, client, regular_user):
        """Revenue report should reject non-admin users."""
        token = create_access_token(data={"sub": regular_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        now = int(time.time() * 1000)
        resp = client.get(
            "/api/v1/admin/reports/revenue",
            headers=headers,
            params={"start_date": now - 86400000, "end_date": now},
        )
        assert resp.status_code == 403


# ============================================================================
# FIX 6: Admin create_organization uses Pydantic validation
# ============================================================================


class TestCreateOrganizationValidation:
    """Test organization creation uses proper Pydantic validation."""

    def test_create_organization_success(self, client, admin_headers, db_session):
        """POST /admin/organizations should create an org with valid data."""
        org_id = f"org_{uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/v1/admin/organizations",
            headers=admin_headers,
            json={"id": org_id, "name": "Test Organization"},
        )
        assert resp.status_code == 201

    def test_create_organization_missing_name(self, client, admin_headers):
        """Missing required 'name' field should return 422 validation error."""
        resp = client.post(
            "/api/v1/admin/organizations",
            headers=admin_headers,
            json={"id": "org_test"},
        )
        assert resp.status_code == 422

    def test_create_organization_missing_id(self, client, admin_headers):
        """Missing required 'id' field should return 422 validation error."""
        resp = client.post(
            "/api/v1/admin/organizations",
            headers=admin_headers,
            json={"name": "Test Org"},
        )
        assert resp.status_code == 422

    def test_create_organization_empty_body(self, client, admin_headers):
        """Empty JSON body should return 422 validation error."""
        resp = client.post(
            "/api/v1/admin/organizations",
            headers=admin_headers,
            json={},
        )
        assert resp.status_code == 422

    def test_create_organization_requires_admin(self, client, regular_user):
        """Organization creation should reject non-admin users."""
        token = create_access_token(data={"sub": regular_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/v1/admin/organizations",
            headers=headers,
            json={"id": "org_test", "name": "Unauthorized Org"},
        )
        assert resp.status_code == 403


# ============================================================================
# ADDITIONAL: Admin analytics endpoints
# ============================================================================


class TestAnalyticsEndpoints:
    """Test analytics endpoints are routable."""

    def test_usage_analytics_route_exists(self):
        """Usage analytics route should be registered."""
        from app.api.admin import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/admin/analytics/usage" in routes

    def test_growth_analytics_route_exists(self):
        """Growth analytics route should be registered."""
        from app.api.admin import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/admin/analytics/growth" in routes

    def test_usage_analytics_endpoint(self, client, admin_headers):
        """GET /admin/analytics/usage should return data."""
        now = int(time.time() * 1000)
        resp = client.get(
            "/api/v1/admin/analytics/usage",
            headers=admin_headers,
            params={
                "start_date": now - 86400000,
                "end_date": now,
                "group_by": "day",
            },
        )
        assert resp.status_code == 200

    def test_growth_analytics_endpoint(self, client, admin_headers):
        """GET /admin/analytics/growth should return data."""
        resp = client.get(
            "/api/v1/admin/analytics/growth",
            headers=admin_headers,
        )
        assert resp.status_code == 200


# ============================================================================
# ADDITIONAL: Dependencies module
# ============================================================================


class TestDependenciesModule:
    """Verify the dependencies module is correct."""

    def test_dependencies_module_imports(self):
        """app.api.dependencies should import without errors."""
        from app.api.dependencies import (
            require_admin,
            require_admin_management,
            require_analytics_access,
            require_moderation_access,
            require_permission,
            require_user_deletion,
            require_user_management,
        )

        assert callable(require_admin)
        assert callable(require_admin_management)
        assert callable(require_permission)

    def test_require_admin_rejects_non_admin(self, client, regular_user):
        """require_admin dependency should reject non-admin users."""
        token = create_access_token(data={"sub": regular_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        # Try to access admin-only endpoint
        resp = client.get("/api/v1/admin/analytics/growth", headers=headers)
        assert resp.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
