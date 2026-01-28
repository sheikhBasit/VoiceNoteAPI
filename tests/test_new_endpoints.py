"""
Test suite for newly implemented API endpoints
Tests: Note Creation, WhatsApp Draft, Semantic Analysis, Task Creation
"""
import pytest
import requests
import time
from typing import Dict

BASE_URL = "http://localhost:8000/api/v1"

# Test credentials
TEST_USER = {
    "email": "test@example.com",
    "password": "testpass123"
}

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/users/login",
        json={"username": TEST_USER["email"], "password": TEST_USER["password"]}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    # If login fails, try sync
    sync_response = requests.post(
        f"{BASE_URL}/users/sync",
        json={
            "name": "Test User",
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
            "token": "test-token",
            "device_id": "test-device",
            "device_model": "Test Model",
            "primary_role": "GENERIC"
        }
    )
    return sync_response.json()["access_token"]

@pytest.fixture
def headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}

class TestNoteCreation:
    """Test manual note creation endpoint"""
    
    def test_create_note_success(self, headers):
        """Test successful note creation"""
        response = requests.post(
            f"{BASE_URL}/notes/create",
            headers=headers,
            json={
                "title": "Test Note",
                "summary": "This is a test note created manually",
                "priority": "HIGH"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Note"
        assert data["summary"] == "This is a test note created manually"
        assert data["priority"] == "HIGH"
        return data["id"]
    
    def test_create_note_minimal(self, headers):
        """Test note creation with minimal data"""
        response = requests.post(
            f"{BASE_URL}/notes/create",
            headers=headers,
            json={"title": "Minimal Note"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Minimal Note"
    
    def test_create_note_no_title(self, headers):
        """Test note creation without title (should use default)"""
        response = requests.post(
            f"{BASE_URL}/notes/create",
            headers=headers,
            json={"summary": "Note without title"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Untitled" in data["title"] or data["title"] != ""

class TestWhatsAppDraft:
    """Test WhatsApp draft generation endpoint"""
    
    @pytest.fixture
    def test_note_id(self, headers):
        """Create a test note for WhatsApp draft"""
        response = requests.post(
            f"{BASE_URL}/notes/create",
            headers=headers,
            json={
                "title": "Meeting Notes",
                "summary": "Discussed project timeline and deliverables",
                "priority": "MEDIUM"
            }
        )
        return response.json()["id"]
    
    def test_get_whatsapp_draft(self, headers, test_note_id):
        """Test WhatsApp draft generation"""
        response = requests.get(
            f"{BASE_URL}/notes/{test_note_id}/whatsapp",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "whatsapp_link" in data
        assert "draft" in data
        assert "Meeting Notes" in data["draft"]
        assert "wa.me" in data["whatsapp_link"]
    
    def test_whatsapp_draft_invalid_note(self, headers):
        """Test WhatsApp draft with invalid note ID"""
        response = requests.get(
            f"{BASE_URL}/notes/invalid-id/whatsapp",
            headers=headers
        )
        assert response.status_code in [404, 403]

class TestSemanticAnalysis:
    """Test semantic analysis trigger endpoint"""
    
    @pytest.fixture
    def test_note_id(self, headers):
        """Create a test note for semantic analysis"""
        response = requests.post(
            f"{BASE_URL}/notes/create",
            headers=headers,
            json={
                "title": "Product Launch Discussion",
                "summary": "Discussed marketing strategy, target audience, and launch timeline",
                "transcript": "We need to focus on digital marketing channels...",
                "priority": "HIGH"
            }
        )
        return response.json()["id"]
    
    def test_trigger_semantic_analysis(self, headers, test_note_id):
        """Test triggering semantic analysis"""
        response = requests.post(
            f"{BASE_URL}/notes/{test_note_id}/semantic-analysis",
            headers=headers
        )
        assert response.status_code == 202  # Accepted
        data = response.json()
        assert "message" in data
        assert "note_id" in data
        assert data["note_id"] == test_note_id
    
    def test_semantic_analysis_invalid_note(self, headers):
        """Test semantic analysis with invalid note ID"""
        response = requests.post(
            f"{BASE_URL}/notes/invalid-id/semantic-analysis",
            headers=headers
        )
        assert response.status_code in [404, 403]

class TestTaskCreation:
    """Test manual task creation endpoint"""
    
    @pytest.fixture
    def test_note_id(self, headers):
        """Create a test note for task creation"""
        response = requests.post(
            f"{BASE_URL}/notes/create",
            headers=headers,
            json={"title": "Project Planning"}
        )
        return response.json()["id"]
    
    def test_create_task_success(self, headers, test_note_id):
        """Test successful task creation"""
        response = requests.post(
            f"{BASE_URL}/tasks",
            headers=headers,
            json={
                "note_id": test_note_id,
                "description": "Complete project proposal",
                "priority": "HIGH",
                "deadline": int(time.time() * 1000) + 86400000  # Tomorrow
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Complete project proposal"
        assert data["priority"] == "HIGH"
    
    def test_create_task_minimal(self, headers, test_note_id):
        """Test task creation with minimal data"""
        response = requests.post(
            f"{BASE_URL}/tasks",
            headers=headers,
            json={
                "note_id": test_note_id,
                "description": "Simple task"
            }
        )
        assert response.status_code == 201
    
    def test_create_task_empty_description(self, headers, test_note_id):
        """Test task creation with empty description (should fail)"""
        response = requests.post(
            f"{BASE_URL}/tasks",
            headers=headers,
            json={
                "note_id": test_note_id,
                "description": ""
            }
        )
        assert response.status_code == 400

class TestTaskFiltering:
    """Test task filtering endpoints"""
    
    def test_get_tasks_due_today(self, headers):
        """Test getting tasks due today"""
        response = requests.get(
            f"{BASE_URL}/tasks/due-today",
            headers=headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_overdue_tasks(self, headers):
        """Test getting overdue tasks"""
        response = requests.get(
            f"{BASE_URL}/tasks/overdue",
            headers=headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_assigned_to_me(self, headers):
        """Test getting tasks assigned to me"""
        response = requests.get(
            f"{BASE_URL}/tasks/assigned-to-me",
            headers=headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

class TestTaskSearch:
    """Test task search endpoint"""
    
    def test_search_tasks(self, headers):
        """Test task search"""
        response = requests.get(
            f"{BASE_URL}/tasks/search",
            headers=headers,
            params={"query": "project"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_search_tasks_empty_query(self, headers):
        """Test task search with empty query"""
        response = requests.get(
            f"{BASE_URL}/tasks/search",
            headers=headers,
            params={"query": ""}
        )
        assert response.status_code == 200

class TestTaskStatistics:
    """Test task statistics endpoint"""
    
    def test_get_task_statistics(self, headers):
        """Test getting task statistics"""
        response = requests.get(
            f"{BASE_URL}/tasks/stats",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "pending_tasks" in data
        assert "by_priority" in data
        assert "completion_rate" in data

class TestTaskDuplication:
    """Test task duplication endpoint"""
    
    @pytest.fixture
    def test_task_id(self, headers):
        """Create a test task for duplication"""
        # First create a note
        note_response = requests.post(
            f"{BASE_URL}/notes/create",
            headers=headers,
            json={"title": "Test Note for Task"}
        )
        note_id = note_response.json()["id"]
        
        # Then create a task
        task_response = requests.post(
            f"{BASE_URL}/tasks",
            headers=headers,
            json={
                "note_id": note_id,
                "description": "Task to duplicate",
                "priority": "MEDIUM"
            }
        )
        return task_response.json()["id"]
    
    def test_duplicate_task(self, headers, test_task_id):
        """Test task duplication"""
        response = requests.post(
            f"{BASE_URL}/tasks/{test_task_id}/duplicate",
            headers=headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Task to duplicate"
        assert data["id"] != test_task_id  # Should be a new ID

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
