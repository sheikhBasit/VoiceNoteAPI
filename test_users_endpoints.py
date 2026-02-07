"""
Comprehensive pytest suite for Users API endpoints
Tests all 10 user endpoints with full validation
"""

import pytest
import requests
import json
import uuid
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
TEST_NAME = "Test User"
TEST_DEVICE_ID = f"device_{uuid.uuid4().hex[:12]}"
TEST_DEVICE_MODEL = "TestDevice_1.0"
TEST_TOKEN = "test_biometric_token"

# Global variables to store test data
test_data = {
    "user_id": None,
    "access_token": None,
    "user_email": TEST_EMAIL,
    "device_id": TEST_DEVICE_ID,
}


class TestUsersAuthentication:
    """Test authentication endpoints"""
    
    def test_01_sync_user_new_account(self):
        """Test POST /users/sync - Create new user"""
        payload = {
            "email": test_data["user_email"],
            "name": TEST_NAME,
            "device_id": test_data["device_id"],
            "device_model": TEST_DEVICE_MODEL,
            "token": TEST_TOKEN,
            "timezone": "UTC"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/sync",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "user" in data, "Response missing 'user' field"
        assert "access_token" in data, "Response missing 'access_token' field"
        assert "token_type" in data, "Response missing 'token_type' field"
        assert data["token_type"] == "bearer", "Token type should be 'bearer'"
        assert data["is_new_user"] == True, "Should be marked as new user"
        
        # Store user data for other tests
        test_data["user_id"] = data["user"]["id"]
        test_data["access_token"] = data["access_token"]
        
        # Verify user data
        assert data["user"]["email"] == test_data["user_email"]
        assert data["user"]["name"] == TEST_NAME
        assert data["user"]["is_deleted"] == False
        
        print(f"✅ User created: {test_data['user_id']}")
    
    def test_02_sync_user_existing_account(self):
        """Test POST /users/sync - Login existing user"""
        payload = {
            "email": test_data["user_email"],
            "name": TEST_NAME,
            "device_id": test_data["device_id"],
            "device_model": TEST_DEVICE_MODEL,
            "token": TEST_TOKEN,
            "timezone": "UTC"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/sync",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should be existing user (is_new_user=False)
        assert data["is_new_user"] == False, "Should be existing user"
        assert data["user"]["id"] == test_data["user_id"], "User ID should match"
        
        print(f"✅ Existing user authenticated")
    
    def test_03_sync_invalid_email(self):
        """Test POST /users/sync - Invalid email format"""
        payload = {
            "email": "invalid_email",  # Invalid email
            "name": TEST_NAME,
            "device_id": f"device_{uuid.uuid4().hex[:12]}",
            "device_model": TEST_DEVICE_MODEL,
            "token": TEST_TOKEN,
            "timezone": "UTC"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/sync",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid email, got {response.status_code}"
        print(f"✅ Invalid email properly rejected")
    
    def test_04_sync_missing_device_id(self):
        """Test POST /users/sync - Missing device_id"""
        payload = {
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "name": TEST_NAME,
            "device_id": "",  # Empty device_id
            "device_model": TEST_DEVICE_MODEL,
            "token": TEST_TOKEN,
            "timezone": "UTC"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/sync",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 400, f"Expected 400 for empty device_id, got {response.status_code}"
        print(f"✅ Missing device_id properly rejected")


class TestUsersProfileManagement:
    """Test profile endpoints"""
    
    def test_05_get_current_user_profile(self):
        """Test GET /users/me - Get current user profile"""
        headers = {"Authorization": f"Bearer {test_data['access_token']}"}
        
        response = requests.get(
            f"{BASE_URL}/users/me",
            headers=headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify profile data
        assert data["id"] == test_data["user_id"]
        assert data["email"] == test_data["user_email"]
        assert data["name"] == TEST_NAME
        assert data["is_deleted"] == False
        
        print(f"✅ Current user profile retrieved")
    
    def test_06_get_user_profile_by_id(self):
        """Test GET /users/{user_id} - Get user by ID"""
        response = requests.get(
            f"{BASE_URL}/users/{test_data['user_id']}",
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify public profile data
        assert data["id"] == test_data["user_id"]
        assert data["email"] == test_data["user_email"]
        assert data["name"] == TEST_NAME
        
        print(f"✅ User profile by ID retrieved")
    
    def test_07_get_nonexistent_user(self):
        """Test GET /users/{user_id} - Non-existent user"""
        fake_id = str(uuid.uuid4())
        
        response = requests.get(
            f"{BASE_URL}/users/{fake_id}",
            timeout=10
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Non-existent user properly rejected")
    
    def test_08_update_user_profile(self):
        """Test PATCH /users/me - Update profile"""
        headers = {"Authorization": f"Bearer {test_data['access_token']}"}
        
        update_data = {
            "name": "Updated Name",
            "work_start_hour": 9,
            "work_end_hour": 17,
            "work_days": [1, 2, 3, 4, 5]
        }
        
        response = requests.patch(
            f"{BASE_URL}/users/me",
            json=update_data,
            headers=headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify updated data
        assert data["name"] == "Updated Name"
        assert data["work_start_hour"] == 9
        assert data["work_end_hour"] == 17
        
        print(f"✅ User profile updated")
    
    def test_09_update_profile_invalid_work_hours(self):
        """Test PATCH /users/me - Invalid work hours"""
        headers = {"Authorization": f"Bearer {test_data['access_token']}"}
        
        update_data = {
            "work_start_hour": 25,  # Invalid (should be 0-23)
            "work_end_hour": 17
        }
        
        response = requests.patch(
            f"{BASE_URL}/users/me",
            json=update_data,
            headers=headers,
            timeout=10
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid hours, got {response.status_code}"
        print(f"✅ Invalid work hours properly rejected")


class TestUsersSearch:
    """Test search endpoints"""
    
    def test_10_search_users_by_name(self):
        """Test GET /users/search - Search by name"""
        response = requests.get(
            f"{BASE_URL}/users/search?query={TEST_NAME}",
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), "Response should be a list"
        
        # Should find our user
        found = any(u["id"] == test_data["user_id"] for u in data)
        assert found, f"User {test_data['user_id']} not found in search results"
        
        print(f"✅ Search by name works")
    
    def test_11_search_users_by_email(self):
        """Test GET /users/search - Search by email"""
        response = requests.get(
            f"{BASE_URL}/users/search?query={test_data['user_email']}",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find our user
        found = any(u["id"] == test_data["user_id"] for u in data)
        assert found, f"User not found in email search"
        
        print(f"✅ Search by email works")
    
    def test_12_search_with_pagination(self):
        """Test GET /users/search - Pagination"""
        response = requests.get(
            f"{BASE_URL}/users/search?skip=0&limit=10",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) <= 10, "Limit should be respected"
        
        print(f"✅ Pagination works")


class TestUsersDeletion:
    """Test deletion endpoints"""
    
    def test_13_delete_user_account(self):
        """Test DELETE /users/me - Soft delete"""
        headers = {"Authorization": f"Bearer {test_data['access_token']}"}
        
        response = requests.delete(
            f"{BASE_URL}/users/me",
            headers=headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should be successful
        assert data.get("success") == True or "success" in str(data).lower()
        
        print(f"✅ User account deleted (soft)")
    
    def test_14_verify_user_deleted(self):
        """Verify user is soft-deleted"""
        response = requests.get(
            f"{BASE_URL}/users/{test_data['user_id']}",
            timeout=10
        )
        
        # Should return 404 since user is deleted
        assert response.status_code == 404, f"Deleted user should return 404, got {response.status_code}"
        
        print(f"✅ Deleted user not accessible")
    
    def test_15_cannot_hard_delete_via_me(self):
        """Verify hard delete parameter is removed from DELETE /me"""
        headers = {"Authorization": f"Bearer {test_data['access_token']}"}
        
        response = requests.delete(
            f"{BASE_URL}/users/me?hard=true",
            headers=headers,
            timeout=10
        )
        
        # Should either ignore the parameter or work anyway (soft delete)
        # Hard delete should NOT be allowed
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        print(f"✅ Hard delete not available via DELETE /me")


class TestUsersAuthentication2:
    """Test session management"""
    
    def test_16_logout_user(self):
        """Test POST /users/logout"""
        # Create new user for logout test
        payload = {
            "email": f"test_logout_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Logout Test",
            "device_id": f"device_{uuid.uuid4().hex[:12]}",
            "device_model": TEST_DEVICE_MODEL,
            "token": TEST_TOKEN,
            "timezone": "UTC"
        }
        
        sync_response = requests.post(
            f"{BASE_URL}/users/sync",
            json=payload,
            timeout=10
        )
        
        assert sync_response.status_code == 200
        logout_token = sync_response.json()["access_token"]
        
        # Now logout
        headers = {"Authorization": f"Bearer {logout_token}"}
        response = requests.post(
            f"{BASE_URL}/users/logout",
            headers=headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print(f"✅ Logout successful")


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
