import time

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def override_db(db):
    """Override get_db dependency to use test session"""
    db.expire_on_commit = False  # FIX: Prevent ObjectDeletedError

    def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


@pytest.fixture
def auth_headers():
    timestamp = int(time.time())
    resp = client.post(
        "/api/v1/users/sync",
        json={
            "name": "Regular User",
            "email": f"user_{timestamp}@example.com",
            "token": "user-token",
            "device_id": f"user-device-{timestamp}",
            "device_model": "Test",
            "primary_role": "GENERIC",
        },
    )
    return {
        "Authorization": f"Bearer {resp.json()['access_token']}",
        "user_id": resp.json()["user"]["id"],
    }


@pytest.fixture
def admin_auth(db):
    """Create an admin user and return headers"""
    timestamp = int(time.time())
    email = f"admin_{timestamp}@example.com"

    # 1. Create user via public sync
    resp = client.post(
        "/api/v1/users/sync",
        json={
            "name": "Test Admin",
            "email": email,
            "token": "admin-token",
            "device_id": f"admin-device-{timestamp}",
            "device_model": "Test",
            "primary_role": "DEVELOPER",
        },
    )
    data = resp.json()
    user_id = data["user"]["id"]
    token = data["access_token"]

    # 2. Elevate to Admin using shared DB session
    user = db.query(models.User).filter(models.User.id == user_id).first()
    user.is_admin = True
    # Ensure usage of dict for SQLite compatibility handled by SQLAlchemy
    user.admin_permissions = {"can_delete_users": True, "can_view_all_users": True}
    db.commit()

    return {"Authorization": f"Bearer {token}", "user_id": user_id}


class TestAdminUpdates:
    def test_admin_update_user(self, db, admin_auth):
        """Test admin updating another user"""
        # Create user to be updated
        timestamp = int(time.time())
        target_resp = client.post(
            "/api/v1/users/sync",
            json={
                "name": "Target User",
                "email": f"target_{timestamp}@example.com",
                "token": "target-tok",
                "device_id": f"target-dev-{timestamp}",
                "device_model": "Test",
            },
        )
        target_id = target_resp.json()["user"]["id"]

        # Call Update Endpoint
        update_payload = {"name": "Updated By Admin"}
        patch_resp = client.patch(
            f"/api/v1/admin/users/{target_id}", json=update_payload, headers=admin_auth
        )

        assert patch_resp.status_code == 200
        assert patch_resp.json()["name"] == "Updated By Admin"

        # Verify in DB
        db.refresh(db.query(models.User).get(target_id))
        assert db.query(models.User).get(target_id).name == "Updated By Admin"


class TestNotesRestoration:
    def test_restore_note(self, db, auth_headers):
        # 1. Create Note
        note = client.post(
            "/api/v1/notes/create", headers=auth_headers, json={"title": "To Delete"}
        ).json()
        note_id = note["id"]

        # 2. Delete Note (Soft)
        del_resp = client.delete(f"/api/v1/notes/{note_id}", headers=auth_headers)
        assert del_resp.status_code == 200

        # FIX: Expire all to refresh session state and avoid ObjectDeletedError
        db.expire_all()

        # DEBUG: Check DB state
        # We need to refresh/query to see if hard deleted
        db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
        assert db_note is not None, "Note was HARD deleted!"
        assert db_note.is_deleted is True, "Note was not soft deleted!"

        # 3. Restore Note
        restore_resp = client.patch(
            f"/api/v1/notes/{note_id}/restore", headers=auth_headers
        )
        assert restore_resp.status_code == 200
        assert restore_resp.json()["is_deleted"] is False

    def test_bulk_delete_notes(self, db, auth_headers):
        n1 = client.post(
            "/api/v1/notes/create", headers=auth_headers, json={"title": "Bulk 1"}
        ).json()["id"]
        n2 = client.post(
            "/api/v1/notes/create", headers=auth_headers, json={"title": "Bulk 2"}
        ).json()["id"]

        # BULK DELETE with Body
        payload = {"note_ids": [n1, n2]}
        bulk_resp = client.request(
            "DELETE", "/api/v1/notes", headers=auth_headers, json=payload
        )

        assert bulk_resp.status_code == 200
        data = bulk_resp.json()
        assert data["deleted_count"] == 2

        db.expire_all()

        # Verify
        restore_resp = client.patch(f"/api/v1/notes/{n1}/restore", headers=auth_headers)
        assert restore_resp.status_code == 200


class TestTasksRestoration:
    def test_task_lifecycle_and_bulk(self, auth_headers):
        t1 = client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"description": "Task 1", "priority": "LOW"},
        ).json()["id"]
        t2 = client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"description": "Task 2", "priority": "LOW"},
        ).json()["id"]

        # Toggle Complete
        comp_resp = client.patch(
            f"/api/v1/tasks/{t1}/complete", headers=auth_headers, json={"is_done": True}
        )
        assert comp_resp.status_code == 200
        assert comp_resp.json()["is_done"] is True

        # Bulk Delete
        bulk_resp = client.request(
            "DELETE", "/api/v1/tasks", headers=auth_headers, json={"task_ids": [t1, t2]}
        )

        assert bulk_resp.status_code == 200
        assert bulk_resp.json()["deleted_count"] == 2

        # Restore
        rest_resp = client.patch(f"/api/v1/tasks/{t1}/restore", headers=auth_headers)
        assert rest_resp.status_code == 200
        assert rest_resp.json()["is_deleted"] is False
