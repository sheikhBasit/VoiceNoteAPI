"""
Regression tests verifying all critical/high audit fixes remain intact.

Each test class maps to a specific audit finding (C02, C03, C04, C05, C11/C12, H05).
Uses the same fixture patterns as tests/admin/conftest.py.
"""

import pytest
from sqlalchemy.orm import Session

from app.db import models
from app.services.auth_service import create_access_token


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture()
def admin_user_and_token(db: Session):
    """Create admin user and return (user, headers)."""
    user = models.User(
        id="reg_admin_001",
        email="reg_admin@test.com",
        name="Regression Admin",
        is_admin=True,
        admin_permissions={
            "can_view_analytics": True,
            "can_delete_tasks": True,
            "can_restore_tasks": True,
            "can_create_test_notes": True,
            "can_manage_api_keys": True,
            "can_manage_wallets": True,
            "can_modify_system_settings": True,
        },
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": user.id})
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.fixture()
def regular_user_and_token(db: Session):
    """Create regular (non-admin) user and return (user, headers)."""
    user = models.User(
        id="reg_user_001",
        email="reg_user@test.com",
        name="Regression User",
        is_admin=False,
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": user.id})
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.fixture()
def wallet_for_user(db: Session, regular_user_and_token):
    """Create a wallet for the regular test user."""
    user, _ = regular_user_and_token
    wallet = models.Wallet(user_id=user.id, balance=1000)
    db.add(wallet)
    db.commit()
    return wallet


# ──────────────────────────────────────────────────────────────────────
# C02: toggle_wallet_freeze uses get_current_active_admin
# ──────────────────────────────────────────────────────────────────────


class TestC02ToggleWalletFreeze:
    """Audit C02: toggle_wallet_freeze must require admin auth (no NameError)."""

    def test_toggle_freeze_requires_admin(self, client, regular_user_and_token, wallet_for_user):
        """Non-admin users must get 403 when toggling wallet freeze."""
        _, headers = regular_user_and_token
        resp = client.post(
            f"/api/v1/admin/wallets/{regular_user_and_token[0].id}/toggle-freeze",
            headers=headers,
        )
        assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"

    def test_toggle_freeze_works_for_admin(self, client, admin_user_and_token, db: Session):
        """Admin can toggle wallet freeze without NameError."""
        admin_user, headers = admin_user_and_token
        # Create a wallet for the admin user to toggle
        wallet = models.Wallet(user_id=admin_user.id, balance=500)
        db.add(wallet)
        db.commit()

        resp = client.post(
            f"/api/v1/admin/wallets/{admin_user.id}/toggle-freeze",
            headers=headers,
        )
        # Should not be 500 (NameError) — any 2xx or 4xx is acceptable
        assert resp.status_code != 500, "toggle_wallet_freeze raised a server error (likely NameError)"


# ──────────────────────────────────────────────────────────────────────
# C03: /reports/revenue endpoint exists
# ──────────────────────────────────────────────────────────────────────


class TestC03RevenueReport:
    """Audit C03: /reports/revenue must be a valid endpoint (not 404/405)."""

    def test_revenue_endpoint_exists(self, client, admin_user_and_token):
        _, headers = admin_user_and_token
        import time

        now_ms = int(time.time() * 1000)
        week_ago_ms = now_ms - (7 * 24 * 60 * 60 * 1000)
        resp = client.get(
            f"/api/v1/admin/reports/revenue?start_date={week_ago_ms}&end_date={now_ms}",
            headers=headers,
        )
        assert resp.status_code not in (404, 405), (
            f"Revenue endpoint missing: got {resp.status_code}"
        )

    def test_revenue_rejects_non_admin(self, client, regular_user_and_token):
        _, headers = regular_user_and_token
        import time

        now_ms = int(time.time() * 1000)
        week_ago_ms = now_ms - (7 * 24 * 60 * 60 * 1000)
        resp = client.get(
            f"/api/v1/admin/reports/revenue?start_date={week_ago_ms}&end_date={now_ms}",
            headers=headers,
        )
        assert resp.status_code in (401, 403)


# ──────────────────────────────────────────────────────────────────────
# C04: Sync module imports and endpoint works
# ──────────────────────────────────────────────────────────────────────


class TestC04SyncModule:
    """Audit C04: sync module must import without error; endpoint must not 500."""

    def test_sync_module_imports(self):
        """from app.api import sync must not raise ImportError."""
        try:
            from app.api import sync  # noqa: F401
        except ImportError as exc:
            pytest.fail(f"Sync module import failed: {exc}")

    def test_upload_batch_responds(self, client, admin_user_and_token):
        """POST /sync/upload-batch must not return 500."""
        _, headers = admin_user_and_token
        resp = client.post(
            "/api/v1/sync/upload-batch",
            json={"notes": []},
            headers=headers,
        )
        assert resp.status_code != 500, f"Sync upload-batch returned 500: {resp.text}"


# ──────────────────────────────────────────────────────────────────────
# C05: BillingService.charge_usage creates Transaction + UsageLog
# ──────────────────────────────────────────────────────────────────────


class TestC05BillingChargeUsage:
    """Audit C05: charge_usage must create Transaction and UsageLog records."""

    def test_charge_creates_records(self, db: Session, regular_user_and_token, wallet_for_user):
        """Calling charge_usage should create both a Transaction and a UsageLog."""
        user, _ = regular_user_and_token
        from app.services.billing_service import BillingService

        svc = BillingService(db)

        # Count records before (Transaction uses wallet_id which maps to user_id)
        tx_before = db.query(models.Transaction).filter(
            models.Transaction.wallet_id == user.id
        ).count()

        result = svc.charge_usage(
            user_id=user.id,
            cost=10,
            description="regression test charge",
            ref_id="test_ref_001",
            audio_duration=30.0,
        )
        assert result is True, "charge_usage returned False (insufficient balance?)"

        # Verify Transaction was created
        tx_after = db.query(models.Transaction).filter(
            models.Transaction.wallet_id == user.id
        ).count()
        assert tx_after > tx_before, "No Transaction record was created by charge_usage"

        # Verify UsageLog was created
        usage_count = db.query(models.UsageLog).filter(
            models.UsageLog.user_id == user.id
        ).count()
        assert usage_count > 0, "No UsageLog record was created by charge_usage"


# ──────────────────────────────────────────────────────────────────────
# C11/C12: Pydantic validation on organizations and locations
# ──────────────────────────────────────────────────────────────────────


class TestC11C12PydanticValidation:
    """Audit C11/C12: organizations and locations must validate request bodies."""

    def test_create_organization_rejects_empty_body(self, client, admin_user_and_token):
        """POST /organizations with empty body must return 400 or 422 (validation error)."""
        _, headers = admin_user_and_token
        resp = client.post("/api/v1/admin/organizations", json={}, headers=headers)
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for empty org body, got {resp.status_code}"
        )

    def test_create_location_rejects_empty_body(self, client, admin_user_and_token):
        """POST /locations with empty body must return 400 or 422 (validation error)."""
        _, headers = admin_user_and_token
        resp = client.post("/api/v1/admin/locations", json={}, headers=headers)
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for empty location body, got {resp.status_code}"
        )

    def test_location_radius_ge_1(self, client, admin_user_and_token):
        """Location radius must be >= 1 (Pydantic Field(ge=1))."""
        _, headers = admin_user_and_token
        resp = client.post(
            "/api/v1/admin/locations",
            json={
                "org_id": "org_test",
                "name": "Test Location",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "radius": 0,  # Invalid: must be >= 1
            },
            headers=headers,
        )
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for radius=0, got {resp.status_code}"
        )


# ──────────────────────────────────────────────────────────────────────
# H05: Bulk delete/restore reject >100 IDs
# ──────────────────────────────────────────────────────────────────────


class TestH05BulkLimits:
    """Audit H05: Bulk operations must reject more than 100 IDs."""

    def test_bulk_delete_rejects_over_100(self, client, admin_user_and_token):
        """POST /bulk/delete with >100 IDs must return 400."""
        _, headers = admin_user_and_token
        ids_str = ",".join([f"id_{i}" for i in range(101)])
        resp = client.post(
            f"/api/v1/admin/bulk/delete?item_type=notes&ids={ids_str}&reason=test",
            headers=headers,
        )
        assert resp.status_code == 400, f"Expected 400 for >100 IDs, got {resp.status_code}"

    def test_bulk_restore_rejects_over_100(self, client, admin_user_and_token):
        """POST /bulk/restore with >100 IDs must return 400."""
        _, headers = admin_user_and_token
        ids_str = ",".join([f"id_{i}" for i in range(101)])
        resp = client.post(
            f"/api/v1/admin/bulk/restore?item_type=notes&ids={ids_str}",
            headers=headers,
        )
        assert resp.status_code == 400, f"Expected 400 for >100 IDs, got {resp.status_code}"

    def test_bulk_delete_accepts_100(self, client, admin_user_and_token):
        """POST /bulk/delete with exactly 100 IDs must NOT return 400."""
        _, headers = admin_user_and_token
        ids_str = ",".join([f"id_{i}" for i in range(100)])
        resp = client.post(
            f"/api/v1/admin/bulk/delete?item_type=notes&ids={ids_str}&reason=test",
            headers=headers,
        )
        # 400 only for >100, so this should pass the limit check
        # Might fail for other reasons (items don't exist) but NOT for the limit
        assert resp.status_code != 400 or "100" not in resp.text, (
            "Bulk delete rejected exactly 100 IDs"
        )
