import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def user_auth():
    unique_id = str(uuid.uuid4())
    payload = {
        "name": f"Folder User {unique_id[:8]}",
        "email": f"folder_{unique_id}@example.com",
        "password": "testpass123",
        "timezone": "UTC",
    }
    resp = client.post("/api/v1/users/register", json=payload)
    data = resp.json()
    return {"token": data["access_token"], "email": payload["email"], "id": data["user"]["id"]}

@pytest.fixture
def headers(user_auth):
    return {"Authorization": f"Bearer {user_auth['token']}"}

class TestFolderLifecycle:
    def test_folder_crud_flow(self, headers):
        # 1. Create
        create_resp = client.post(
            "/api/v1/folders",
            headers=headers,
            json={"name": "Work Projects", "color": "#0000FF", "icon": "briefcase"}
        )
        assert create_resp.status_code == 201
        folder = create_resp.json()
        folder_id = folder["id"]
        assert folder["name"] == "Work Projects"

        # 2. List
        list_resp = client.get("/api/v1/folders", headers=headers)
        assert list_resp.status_code == 200
        assert any(f["id"] == folder_id for f in list_resp.json())

        # 3. Update
        update_resp = client.patch(
            f"/api/v1/folders/{folder_id}",
            headers=headers,
            json={"name": "Work Projects Updated", "color": "#FF00FF"}
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Work Projects Updated"

        # 4. Delete
        delete_resp = client.delete(f"/api/v1/folders/{folder_id}", headers=headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["message"] == "Folder deleted successfully"

        # 5. Verify Deleted
        list_again_resp = client.get("/api/v1/folders", headers=headers)
        assert not any(f["id"] == folder_id for f in list_again_resp.json())

class TestFolderParticipantsDetailed:
    def test_participant_management(self, headers, user_auth):
        # Create a folder to test participants
        folder_resp = client.post(
            "/api/v1/folders",
            headers=headers,
            json={"name": "Team Folder"}
        )
        folder_id = folder_resp.json()["id"]

        # Register another user to add as participant
        other_id = str(uuid.uuid4())
        other_email = f"other_{other_id}@example.com"
        client.post("/api/v1/users/register", json={
            "name": "Other User",
            "email": other_email,
            "password": "testpass123",
            "timezone": "UTC"
        })

        # Add participant
        add_resp = client.post(
            f"/api/v1/folders/{folder_id}/participants",
            headers=headers,
            params={"user_email": other_email, "role": "ADMIN"}
        )
        assert add_resp.status_code == 200
        
        # List participants
        list_resp = client.get(f"/api/v1/folders/{folder_id}/participants", headers=headers)
        assert list_resp.status_code == 200
        parts = list_resp.json()
        assert any(p["email"] == other_email and p["role"] == "ADMIN" for p in parts)

    def test_add_non_existent_user(self, headers):
        folder_resp = client.post("/api/v1/folders", headers=headers, json={"name": "Ghost Folder"})
        folder_id = folder_resp.json()["id"]

        resp = client.post(
            f"/api/v1/folders/{folder_id}/participants",
            headers=headers,
            params={"user_email": "doesnotexist@example.com"}
        )
        assert resp.status_code == 404
        assert "User not found" in resp.json()["error"]
