
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_context():
    """Get authentication context (token and user info) for tests"""
    timestamp = int(time.time())
    test_user_payload = {
        "name": f"Test OAuth User {timestamp}",
        "email": f"test_oauth_{timestamp}@example.com",
        "token": "test-biometric-token",
        "device_id": f"test-device-{timestamp}",
        "device_model": "Pytest CI",
        "primary_role": "GENERIC",
        "timezone": "UTC",
    }

    sync_response = client.post("/api/v1/users/sync", json=test_user_payload)

    if sync_response.status_code == 200:
        data = sync_response.json()
        return {
            "access_token": data["access_token"],
            "email": test_user_payload["email"],
            "user_id": data["user"]["id"],
        }
    return None

@pytest.fixture
def headers(auth_context):
    """Get headers with auth token"""
    if not auth_context:
        pytest.fail("Could not obtain auth context")
    return {"Authorization": f"Bearer {auth_context['access_token']}"}

def test_list_integrations_empty(headers):
    response = client.get("/api/v1/integrations/list", headers=headers)
    assert response.status_code == 200
    assert response.json() == []

def test_connect_google(headers):
    payload = {"code": "auth_code_123"}
    response = client.post("/api/v1/integrations/google/connect", json=payload, headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"status": "connected", "provider": "google"}
    
    # Verify via List
    list_response = client.get("/api/v1/integrations/list", headers=headers)
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["provider"] == "google"

def test_connect_notion(headers):
    payload = {"code": "auth_code_notion"}
    response = client.post("/api/v1/integrations/notion/connect", json=payload, headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"status": "connected", "provider": "notion"}
    
    # Verify via List
    list_response = client.get("/api/v1/integrations/list", headers=headers)
    # Could be 1 or 2 depending on order, but let's check content
    providers = [i["provider"] for i in list_response.json()]
    assert "notion" in providers
    
    notion_integration = next(i for i in list_response.json() if i["provider"] == "notion")
    assert notion_integration["meta_data"]["workspace_name"] == "Demo Workspace"

def test_disconnect_integration(headers):
    # Ensure google is connected
    client.post("/api/v1/integrations/google/connect", json={"code": "123"}, headers=headers)
    
    response = client.delete("/api/v1/integrations/google/disconnect", headers=headers)
    assert response.status_code == 200
    
    # Verify removal
    list_response = client.get("/api/v1/integrations/list", headers=headers)
    providers = [i["provider"] for i in list_response.json()]
    assert "google" not in providers
