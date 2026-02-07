#!/usr/bin/env python3
"""
Complete User Endpoints Test Suite
Tests all user management endpoints (old + new)
- Users endpoints (public + admin features)
- Admin user management endpoints
"""

import time
from datetime import datetime
from typing import Tuple

import requests

BASE_URL = "http://localhost:8000/api/v1"

# Test credentials
TEST_USERS = {
    "user_1": {
        "name": "Test User One",
        "email": f"user1_{int(time.time())}@test.com",
        "device_id": "test_device_001",
        "device_model": "TestDevice_1.0",
        "token": "test_biometric_001",
        "timezone": "UTC",
    },
    "user_2": {
        "name": "Test User Two",
        "email": f"user2_{int(time.time())}@test.com",
        "device_id": "test_device_002",
        "device_model": "TestDevice_2.0",
        "token": "test_biometric_002",
        "timezone": "UTC",
    },
    "admin": {
        "name": "Test Admin User",
        "email": f"admin_{int(time.time())}@test.com",
        "device_id": "test_device_admin",
        "device_model": "TestDevice_Admin",
        "token": "test_biometric_admin",
        "timezone": "UTC",
    },
}

# Store authenticated users
authenticated_users = {}
results = []


def log_test(test_name: str, passed: bool, message: str, duration: float = 0):
    """Log test result"""
    status = "✅" if passed else "❌"
    duration_str = f" ({duration:.2f}s)" if duration > 0 else ""
    result_msg = f"{status} {test_name}: {message}{duration_str}"
    results.append({"test": test_name, "passed": passed, "message": message})
    print(result_msg)


def authenticate_user(user_key: str, make_admin: bool = False) -> Tuple[str, str]:
    """Authenticate user and optionally make them admin"""
    if user_key in authenticated_users:
        return authenticated_users[user_key]

    user_data = TEST_USERS[user_key]
    start = time.time()

    try:
        # Step 1: Sync user
        response = requests.post(f"{BASE_URL}/users/sync", json=user_data, timeout=10)

        if response.status_code != 200:
            log_test("auth", False, f"Sync failed: {response.text}")
            return None, None

        user_info = response.json()
        user_id = user_info["user"]["id"]
        token = user_info["access_token"]
        duration = time.time() - start

        log_test("auth", True, f"User {user_key} authenticated", duration)

        # Step 2: Make admin if requested
        if make_admin:
            headers = {"Authorization": f"Bearer {token}"}
            admin_response = requests.post(
                f"{BASE_URL}/admin/users/{user_id}/make-admin?level=full",
                headers=headers,
                timeout=10,
            )

            if admin_response.status_code == 200:
                log_test("auth", True, f"User {user_key} promoted to admin")
            else:
                log_test(
                    "auth", False, f"Admin promotion failed: {admin_response.text}"
                )

        authenticated_users[user_key] = (user_id, token)
        return user_id, token

    except Exception as e:
        log_test("auth", False, f"Authentication error: {str(e)}")
        return None, None


# ============================================================
# TEST SUITE
# ============================================================


def test_1_user_authentication():
    """Test user authentication and admin promotion"""
    print("\n" + "=" * 60)
    print("TEST SUITE 1: USER AUTHENTICATION & ADMIN SETUP")
    print("=" * 60)

    # Authenticate regular users
    authenticate_user("user_1")
    authenticate_user("user_2")

    # Authenticate and make admin
    authenticate_user("admin", make_admin=True)


def test_2_get_user_by_id():
    """Test GET /users/{user_id} - Get user profile by ID"""
    print("\n" + "=" * 60)
    print("TEST SUITE 2: GET USER BY ID ENDPOINT")
    print("=" * 60)

    user_id, token = authenticated_users.get("user_1", (None, None))
    if not user_id:
        log_test("get_user_by_id", False, "No authenticated user")
        return

    start = time.time()
    try:
        # Get own profile (public)
        response = requests.get(f"{BASE_URL}/users/{user_id}", timeout=10)

        duration = time.time() - start

        if response.status_code == 200:
            user = response.json()
            log_test("get_user_by_id", True, f"Retrieved user {user_id}", duration)

            # Verify public fields are present
            required_fields = ["id", "name", "email", "created_at"]
            has_all = all(field in user for field in required_fields)
            log_test("get_user_by_id_fields", has_all, "All required fields present")
        else:
            log_test("get_user_by_id", False, f"Request failed: {response.status_code}")

    except Exception as e:
        log_test("get_user_by_id", False, f"Error: {str(e)}")


def test_3_search_users():
    """Test GET /users/search - Search users"""
    print("\n" + "=" * 60)
    print("TEST SUITE 3: USER SEARCH ENDPOINT")
    print("=" * 60)

    start = time.time()
    try:
        # Search by name
        response = requests.get(f"{BASE_URL}/users/search?query=Test", timeout=10)

        duration = time.time() - start

        if response.status_code == 200:
            results_data = response.json()
            count = len(results_data)
            log_test(
                "search_users", True, f"Found {count} users matching 'Test'", duration
            )
        else:
            log_test("search_users", False, f"Request failed: {response.status_code}")

    except Exception as e:
        log_test("search_users", False, f"Error: {str(e)}")


def test_4_update_user_settings():
    """Test PATCH /me - Update user settings"""
    print("\n" + "=" * 60)
    print("TEST SUITE 4: UPDATE USER SETTINGS")
    print("=" * 60)

    user_id, token = authenticated_users.get("user_1", (None, None))
    if not user_id:
        log_test("update_user", False, "No authenticated user")
        return

    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()

    try:
        update_data = {
            "name": f"Updated User {int(time.time())}",
            "timezone": "Asia/Karachi",
        }

        response = requests.patch(
            f"{BASE_URL}/users/me", json=update_data, headers=headers, timeout=10
        )

        duration = time.time() - start

        if response.status_code == 200:
            user = response.json()
            log_test("update_user", True, f"Updated user profile", duration)
        else:
            log_test("update_user", False, f"Request failed: {response.status_code}")

    except Exception as e:
        log_test("update_user", False, f"Error: {str(e)}")


def test_5_delete_user_me():
    """Test DELETE /me - Delete own account (soft delete)"""
    print("\n" + "=" * 60)
    print("TEST SUITE 5: DELETE USER ACCOUNT (SOFT DELETE)")
    print("=" * 60)

    user_id, token = authenticated_users.get("user_2", (None, None))
    if not user_id:
        log_test("delete_user_me", False, "No authenticated user")
        return

    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()

    try:
        response = requests.delete(f"{BASE_URL}/users/me", headers=headers, timeout=10)

        duration = time.time() - start

        if response.status_code == 200:
            result = response.json()
            is_deleted = result.get("is_deleted", False)
            log_test("delete_user_me", is_deleted, f"User soft-deleted", duration)
        else:
            log_test("delete_user_me", False, f"Request failed: {response.status_code}")

    except Exception as e:
        log_test("delete_user_me", False, f"Error: {str(e)}")


def test_6_admin_get_user_details():
    """Test GET /admin/users/{user_id} - Admin view user details"""
    print("\n" + "=" * 60)
    print("TEST SUITE 6: ADMIN VIEW USER DETAILS")
    print("=" * 60)

    admin_id, admin_token = authenticated_users.get("admin", (None, None))
    user_id, _ = authenticated_users.get("user_1", (None, None))

    if not admin_id or not user_id:
        log_test("admin_get_user_details", False, "No admin or user authenticated")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    start = time.time()

    try:
        response = requests.get(
            f"{BASE_URL}/admin/users/{user_id}", headers=headers, timeout=10
        )

        duration = time.time() - start

        if response.status_code == 200:
            details = response.json()
            log_test(
                "admin_get_user_details",
                True,
                f"Retrieved detailed user info",
                duration,
            )

            # Verify structure
            has_user = "user" in details
            has_subscription = "subscription" in details
            has_devices = "devices" in details
            has_content = "content" in details

            structure_ok = all([has_user, has_subscription, has_devices, has_content])
            log_test(
                "admin_user_details_structure",
                structure_ok,
                "All detail sections present",
            )
        else:
            log_test(
                "admin_get_user_details",
                False,
                f"Request failed: {response.status_code}",
            )

    except Exception as e:
        log_test("admin_get_user_details", False, f"Error: {str(e)}")


def test_7_admin_list_users():
    """Test GET /admin/users - List all users"""
    print("\n" + "=" * 60)
    print("TEST SUITE 7: ADMIN LIST ALL USERS")
    print("=" * 60)

    admin_id, admin_token = authenticated_users.get("admin", (None, None))
    if not admin_id:
        log_test("admin_list_users", False, "No admin authenticated")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    start = time.time()

    try:
        response = requests.get(
            f"{BASE_URL}/admin/users?skip=0&limit=20", headers=headers, timeout=10
        )

        duration = time.time() - start

        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            users_count = len(data.get("users", []))
            log_test(
                "admin_list_users",
                True,
                f"Retrieved {users_count} users (total: {total})",
                duration,
            )
        else:
            log_test(
                "admin_list_users", False, f"Request failed: {response.status_code}"
            )

    except Exception as e:
        log_test("admin_list_users", False, f"Error: {str(e)}")


def test_8_admin_user_statistics():
    """Test GET /admin/users/stats - Get user statistics"""
    print("\n" + "=" * 60)
    print("TEST SUITE 8: ADMIN USER STATISTICS")
    print("=" * 60)

    admin_id, admin_token = authenticated_users.get("admin", (None, None))
    if not admin_id:
        log_test("admin_user_stats", False, "No admin authenticated")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    start = time.time()

    try:
        response = requests.get(
            f"{BASE_URL}/admin/users/stats", headers=headers, timeout=10
        )

        duration = time.time() - start

        if response.status_code == 200:
            stats = response.json()
            log_test("admin_user_stats", True, f"Retrieved user statistics", duration)

            # Verify stats fields
            has_total = "total_users" in stats
            has_admins = "admin_count" in stats
            has_active = "active_users" in stats

            stats_ok = all([has_total, has_admins, has_active])
            log_test("admin_stats_fields", stats_ok, "All stats fields present")
        else:
            log_test(
                "admin_user_stats", False, f"Request failed: {response.status_code}"
            )

    except Exception as e:
        log_test("admin_user_stats", False, f"Error: {str(e)}")


def test_9_admin_get_user_devices():
    """Test GET /admin/users/{user_id}/devices - Get user devices"""
    print("\n" + "=" * 60)
    print("TEST SUITE 9: ADMIN VIEW USER DEVICES")
    print("=" * 60)

    admin_id, admin_token = authenticated_users.get("admin", (None, None))
    user_id, _ = authenticated_users.get("user_1", (None, None))

    if not admin_id or not user_id:
        log_test("admin_get_user_devices", False, "No admin or user authenticated")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    start = time.time()

    try:
        response = requests.get(
            f"{BASE_URL}/admin/users/{user_id}/devices", headers=headers, timeout=10
        )

        duration = time.time() - start

        if response.status_code == 200:
            data = response.json()
            devices_count = data.get("total_devices", 0)
            log_test(
                "admin_get_user_devices",
                True,
                f"Retrieved {devices_count} devices",
                duration,
            )
        else:
            log_test(
                "admin_get_user_devices",
                False,
                f"Request failed: {response.status_code}",
            )

    except Exception as e:
        log_test("admin_get_user_devices", False, f"Error: {str(e)}")


def test_10_admin_restore_user():
    """Test PATCH /admin/users/{user_id}/restore - Restore soft-deleted user"""
    print("\n" + "=" * 60)
    print("TEST SUITE 10: ADMIN RESTORE USER")
    print("=" * 60)

    admin_id, admin_token = authenticated_users.get("admin", (None, None))
    user_id, _ = authenticated_users.get("user_2", (None, None))  # The one we deleted

    if not admin_id or not user_id:
        log_test("admin_restore_user", False, "No admin or user available")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    start = time.time()

    try:
        response = requests.patch(
            f"{BASE_URL}/admin/users/{user_id}/restore?reason=test_restore",
            headers=headers,
            timeout=10,
        )

        duration = time.time() - start

        if response.status_code == 200:
            result = response.json()
            log_test(
                "admin_restore_user", True, f"User restored successfully", duration
            )
        else:
            log_test(
                "admin_restore_user", False, f"Request failed: {response.status_code}"
            )

    except Exception as e:
        log_test("admin_restore_user", False, f"Error: {str(e)}")


def test_11_admin_hard_delete_user():
    """Test DELETE /admin/users/{user_id}/hard - Hard delete user"""
    print("\n" + "=" * 60)
    print("TEST SUITE 11: ADMIN HARD DELETE USER")
    print("=" * 60)

    admin_id, admin_token = authenticated_users.get("admin", (None, None))
    user_id, _ = authenticated_users.get("user_2", (None, None))  # The one we restored

    if not admin_id or not user_id:
        log_test("admin_hard_delete_user", False, "No admin or user available")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    start = time.time()

    try:
        response = requests.delete(
            f"{BASE_URL}/admin/users/{user_id}/hard?confirmation={user_id}&reason=test_hard_delete",
            headers=headers,
            timeout=10,
        )

        duration = time.time() - start

        if response.status_code == 200:
            result = response.json()
            log_test(
                "admin_hard_delete_user", True, f"User permanently deleted", duration
            )

            deleted_items = result.get("deleted_items", {})
            log_test(
                "admin_hard_delete_items",
                True,
                f"Deleted items: {deleted_items.get('notes', 0)} notes, {deleted_items.get('tasks', 0)} tasks",
            )
        else:
            log_test(
                "admin_hard_delete_user",
                False,
                f"Request failed: {response.status_code}",
            )

    except Exception as e:
        log_test("admin_hard_delete_user", False, f"Error: {str(e)}")


def test_12_list_all_admins():
    """Test GET /admin/admins - List all admin users"""
    print("\n" + "=" * 60)
    print("TEST SUITE 12: LIST ALL ADMIN USERS")
    print("=" * 60)

    admin_id, admin_token = authenticated_users.get("admin", (None, None))
    if not admin_id:
        log_test("list_admins", False, "No admin authenticated")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    start = time.time()

    try:
        response = requests.get(f"{BASE_URL}/admin/admins", headers=headers, timeout=10)

        duration = time.time() - start

        if response.status_code == 200:
            data = response.json()
            admin_count = len(data.get("admins", []))
            log_test(
                "list_admins", True, f"Retrieved {admin_count} admin users", duration
            )
        else:
            log_test("list_admins", False, f"Request failed: {response.status_code}")

    except Exception as e:
        log_test("list_admins", False, f"Error: {str(e)}")


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {100 * passed / total:.1f}%\n")

    if failed > 0:
        print("FAILED TESTS:")
        for r in results:
            if not r["passed"]:
                print(f"  ❌ {r['test']}: {r['message']}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("COMPREHENSIVE USER ENDPOINTS TEST SUITE")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}\n")

    try:
        test_1_user_authentication()
        test_2_get_user_by_id()
        test_3_search_users()
        test_4_update_user_settings()
        test_5_delete_user_me()
        test_6_admin_get_user_details()
        test_7_admin_list_users()
        test_8_admin_user_statistics()
        test_9_admin_get_user_devices()
        test_10_admin_restore_user()
        test_11_admin_hard_delete_user()
        test_12_list_all_admins()

        print_summary()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
