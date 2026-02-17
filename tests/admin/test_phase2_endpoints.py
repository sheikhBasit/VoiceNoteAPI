"""
Phase 2 Admin Endpoint Tests
Tests for operations endpoints (API keys, bulk ops, wallets)
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
# PHASE 2: OPERATIONS ENDPOINTS TESTS
# ============================================================================


class TestAPIKeyEndpoints:
    """Tests for API key management endpoints"""

    def test_list_api_keys(self, admin_token):
        """GET /api/v1/admin/api-keys"""
        response = client.get(
            "/api/v1/admin/api-keys",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert "total" in data

    def test_create_api_key(self, admin_token):
        """POST /api/v1/admin/api-keys"""
        response = client.post(
            "/api/v1/admin/api-keys?service_name=groq&api_key=gsk_test_12345&priority=1&notes=Test key",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "key_id" in data

    def test_create_api_key_invalid_service(self, admin_token):
        """POST /api/v1/admin/api-keys with invalid service"""
        response = client.post(
            "/api/v1/admin/api-keys?service_name=invalid&api_key=test_key",
            headers=admin_token
        )
        assert response.status_code == 400

    def test_api_key_health(self, admin_token):
        """GET /api/v1/admin/api-keys/health"""
        response = client.get(
            "/api/v1/admin/api-keys/health",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert "health_report" in data


class TestBulkOperationsEndpoints:
    """Tests for bulk operations endpoints"""

    def test_bulk_delete_notes(self, admin_token, test_note):
        """POST /api/v1/admin/bulk/delete"""
        response = client.post(
            f"/api/v1/admin/bulk/delete?item_type=notes&ids={test_note.id}&reason=Test bulk delete&hard=false",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted_count" in data

    def test_bulk_delete_invalid_type(self, admin_token):
        """POST /api/v1/admin/bulk/delete with invalid type"""
        response = client.post(
            "/api/v1/admin/bulk/delete?item_type=invalid&ids=id1&reason=Test",
            headers=admin_token
        )
        assert response.status_code == 400

    def test_bulk_restore(self, admin_token, db, test_note):
        """POST /api/v1/admin/bulk/restore"""
        # First soft delete
        test_note.is_deleted = True
        db.commit()
        
        response = client.post(
            f"/api/v1/admin/bulk/restore?item_type=notes&ids={test_note.id}",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestWalletEndpoints:
    """Tests for wallet management endpoints"""

    def test_list_wallets(self, admin_token):
        """GET /api/v1/admin/wallets"""
        response = client.get(
            "/api/v1/admin/wallets?limit=10",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert "wallets" in data
        assert "total" in data

    def test_credit_wallet(self, admin_token, test_user):
        """POST /api/v1/admin/wallets/{user_id}/credit"""
        response = client.post(
            f"/api/v1/admin/wallets/{test_user.id}/credit?amount=500&reason=Test credit",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "new_balance" in data

    def test_debit_wallet(self, admin_token, test_user, db):
        """POST /api/v1/admin/wallets/{user_id}/debit"""
        # First create/credit wallet
        wallet = models.Wallet(
            user_id=test_user.id,
            balance=1000,
            currency="USD",
            is_frozen=False
        )
        db.add(wallet)
        db.commit()
        
        response = client.post(
            f"/api/v1/admin/wallets/{test_user.id}/debit?amount=200&reason=Test debit",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_freeze_wallet(self, admin_token, test_user, db):
        """POST /api/v1/admin/wallets/{user_id}/freeze"""
        # Ensure wallet exists
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == test_user.id).first()
        if not wallet:
            wallet = models.Wallet(
                user_id=test_user.id,
                balance=1000,
                currency="USD",
                is_frozen=False
            )
            db.add(wallet)
            db.commit()
        
        response = client.post(
            f"/api/v1/admin/wallets/{test_user.id}/freeze?reason=Test freeze",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["is_frozen"] == True

    def test_unfreeze_wallet(self, admin_token, test_user, db):
        """POST /api/v1/admin/wallets/{user_id}/unfreeze"""
        # Ensure wallet exists and is frozen
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == test_user.id).first()
        if not wallet:
            wallet = models.Wallet(
                user_id=test_user.id,
                balance=1000,
                currency="USD",
                is_frozen=True
            )
            db.add(wallet)
            db.commit()
        else:
            wallet.is_frozen = True
            db.commit()
        
        response = client.post(
            f"/api/v1/admin/wallets/{test_user.id}/unfreeze",
            headers=admin_token
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["is_frozen"] == False
