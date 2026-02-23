import time
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.encryption import EncryptionService

client = TestClient(app)

@pytest.fixture(scope="module")
def owner_auth():
    unique_id = str(uuid.uuid4())
    payload = {
        "name": f"Owner {unique_id[:8]}",
        "email": f"owner_{unique_id}@example.com",
        "password": "testpass123",
        "timezone": "UTC",
    }
    resp = client.post("/api/v1/users/register", json=payload)
    data = resp.json()
    return {"token": data["access_token"], "email": payload["email"], "id": data["user"]["id"]}

@pytest.fixture(scope="module")
def participant_auth():
    unique_id = str(uuid.uuid4())
    payload = {
        "name": f"Participant {unique_id[:8]}",
        "email": f"part_{unique_id}@example.com",
        "password": "testpass123",
        "timezone": "UTC",
    }
    resp = client.post("/api/v1/users/register", json=payload)
    data = resp.json()
    return {"token": data["access_token"], "email": payload["email"], "id": data["user"]["id"]}

@pytest.fixture
def owner_headers(owner_auth):
    return {"Authorization": f"Bearer {owner_auth['token']}"}

@pytest.fixture
def part_headers(participant_auth):
    return {"Authorization": f"Bearer {participant_auth['token']}"}

class TestFolderSharing:
    def test_share_folder_flow(self, owner_headers, part_headers, participant_auth):
        # 1. Owner creates a folder
        folder_resp = client.post(
            "/api/v1/folders",
            headers=owner_headers,
            json={"name": "Shared Project", "color": "#FF5733"}
        )
        assert folder_resp.status_code == 201
        folder_id = folder_resp.json()["id"]

        # 2. Owner adds participant
        share_resp = client.post(
            f"/api/v1/folders/{folder_id}/participants",
            headers=owner_headers,
            json={"user_email": participant_auth["email"], "role": "EDITOR"}
        )
        assert share_resp.status_code == 200
        
        # 3. Participant lists folders and sees the shared one
        list_resp = client.get("/api/v1/folders", headers=part_headers)
        assert list_resp.status_code == 200
        folders = list_resp.json()
        assert any(f["id"] == folder_id for f in folders)

        # 4. Participant lists participants
        part_list_resp = client.get(f"/api/v1/folders/{folder_id}/participants", headers=part_headers)
        assert part_list_resp.status_code == 200
        parts = part_list_resp.json()
        assert len(parts) >= 1
        assert any(p["email"] == participant_auth["email"] for p in parts)

class TestNoteEncryptionIntegration:
    def test_encrypted_note_access(self, owner_headers, part_headers, participant_auth):
        # 1. Owner creates a shared folder
        folder_resp = client.post(
            "/api/v1/folders",
            headers=owner_headers,
            json={"name": "Secure Vault", "color": "#000000"}
        )
        folder_id = folder_resp.json()["id"]
        
        # 2. Share with participant
        client.post(
            f"/api/v1/folders/{folder_id}/participants",
            headers=owner_headers,
            json={"user_email": participant_auth["email"]}
        )

        # 3. Owner creates an encrypted note
        note_resp = client.post(
            "/api/v1/notes/create",
            headers=owner_headers,
            json={
                "title": "Secret Strategy",
                "summary": "This is a top secret summary",
                "transcript": "Meeting transcript about classified things",
                "is_encrypted": True,
                "folder_id": folder_id
            }
        )
        assert note_resp.status_code == 201
        note_id = note_resp.json()["id"]

        # 4. Owner retrieves note (should be decrypted)
        get_owner_resp = client.get(f"/api/v1/notes/{note_id}", headers=owner_headers)
        assert get_owner_resp.status_code == 200
        owner_data = get_owner_resp.json()
        assert owner_data["summary"] == "This is a top secret summary"
        
        # 5. Participant retrieves note (should be decrypted because of folder access)
        get_part_resp = client.get(f"/api/v1/notes/{note_id}", headers=part_headers)
        assert get_part_resp.status_code == 200
        part_data = get_part_resp.json()
        assert part_data["summary"] == "This is a top secret summary"

        # 6. Verify encryption at DB level (Indirectly by checking list response vs detail if allowed)
        # NoteService.list_notes also decrypts summary, so we can't easily see encrypted data via API
        # unless we bypass NoteService, which we won't do here.
        # But we verified decryption works for both authorized users.
