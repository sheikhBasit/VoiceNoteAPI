#!/usr/bin/env python3

"""
Comprehensive Test Suite for VoiceNote API
Tests all endpoints with both HTTP and pytest validation
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Tuple

import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "http://localhost:8000"
REPORT_FILE = "/tmp/voicenote_api_test_report.txt"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


# ============================================================================
# TEST RESULTS
# ============================================================================


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.tests = []

    def add(
        self,
        name: str,
        method: str,
        endpoint: str,
        expected_code: int,
        actual_code: int,
        passed: bool,
        response: str = "",
    ):
        self.total += 1
        if passed:
            self.passed += 1
            status = f"{Colors.GREEN}✅ PASS{Colors.END}"
        else:
            self.failed += 1
            status = f"{Colors.RED}❌ FAIL{Colors.END}"

        print(f"{status} [{actual_code}] {method} {endpoint}")

        self.tests.append(
            {
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "expected": expected_code,
                "actual": actual_code,
                "passed": passed,
                "response": response[:200] if response else "",
            }
        )

    def get_summary(self):
        total = self.total
        passed = self.passed
        failed = self.failed
        pass_rate = (passed * 100 // total) if total > 0 else 0

        return f"""
{'='*80}
                        TEST SUMMARY
{'='*80}
Total Tests:  {total}
Passed:       {Colors.GREEN}{passed}{Colors.END}
Failed:       {Colors.RED}{failed}{Colors.END}
Pass Rate:    {Colors.YELLOW}{pass_rate}%{Colors.END}
{'='*80}
"""


# ============================================================================
# TEST HELPER FUNCTIONS
# ============================================================================


def test_endpoint(
    result: TestResult,
    name: str,
    method: str,
    endpoint: str,
    expected_codes: List[int],
    data: dict = None,
    headers: dict = None,
    auth_token: str = None,
) -> Tuple[int, dict]:
    """Test an endpoint and record result"""

    url = f"{BASE_URL}{endpoint}"

    # Add auth header if token provided
    if headers is None:
        headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=5)
        elif method.upper() == "PATCH":
            response = requests.patch(url, json=data, headers=headers, timeout=5)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=5)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=5)
        else:
            raise ValueError(f"Unsupported method: {method}")

        status_code = response.status_code
        passed = status_code in expected_codes

        try:
            response_data = response.json()
        except:
            response_data = {"text": response.text[:200]}

        result.add(
            name,
            method,
            endpoint,
            expected_codes[0],
            status_code,
            passed,
            json.dumps(response_data),
        )

        return status_code, response_data

    except Exception as e:
        result.add(name, method, endpoint, expected_codes[0], 0, False, str(e))
        return 0, {"error": str(e)}


# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================


def main():
    print(f"\n{Colors.BLUE}{'='*80}")
    print("    COMPREHENSIVE VOICENOTE API TEST SUITE")
    print(f"{'='*80}{Colors.END}\n")

    result = TestResult()
    auth_token = None
    test_user_email = f"test_{int(time.time())}@test.com"
    device_id = f"device_{int(time.time())}"

    # ========================================================================
    # STEP 1: USER AUTHENTICATION & REGISTRATION
    # ========================================================================

    print(f"\n{Colors.BLUE}[STEP 1] USER AUTHENTICATION & REGISTRATION{Colors.END}\n")

    user_payload = {
        "email": test_user_email,
        "name": "cURL Test User",
        "device_id": device_id,
        "device_model": "iPhone12",
        "token": "biometric_token_123",
        "timezone": "UTC",
    }

    status, response = test_endpoint(
        result,
        "User Sync - New User",
        "POST",
        "/api/v1/users/sync",
        [200],
        user_payload,
    )

    if status == 200 and "access_token" in response:
        auth_token = response.get("access_token")
        print(f"   {Colors.BLUE}✓ Token obtained:{Colors.END} {auth_token[:30]}...\n")

    # ========================================================================
    # STEP 2: USER ENDPOINTS
    # ========================================================================

    if not auth_token:
        print(
            f"{Colors.RED}❌ Could not get auth token. Skipping remaining tests.{Colors.END}"
        )
        print(result.get_summary())
        return

    print(f"\n{Colors.BLUE}[STEP 2] USER ENDPOINTS{Colors.END}\n")

    test_endpoint(
        result,
        "Get Current User",
        "GET",
        "/api/v1/users/me",
        [200],
        auth_token=auth_token,
    )

    update_user = {"name": "Updated Name", "timezone": "PST"}
    test_endpoint(
        result,
        "Update User",
        "PATCH",
        "/api/v1/users/me",
        [200],
        update_user,
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Search Users",
        "GET",
        "/api/v1/users/search?q=test",
        [200],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Logout User",
        "POST",
        "/api/v1/users/logout",
        [200],
        auth_token=auth_token,
    )

    # ========================================================================
    # STEP 3: NOTE ENDPOINTS
    # ========================================================================

    print(f"\n{Colors.BLUE}[STEP 3] NOTE ENDPOINTS{Colors.END}\n")

    test_endpoint(
        result,
        "Get Presigned URL",
        "GET",
        "/api/v1/notes/presigned-url",
        [200],
        auth_token=auth_token,
    )

    create_note = {
        "title": "Test Note",
        "content": "Test Content",
        "language": "en",
        "duration_ms": 1000,
    }
    status, response = test_endpoint(
        result,
        "Create Note",
        "POST",
        "/api/v1/notes/create",
        [201, 200],
        create_note,
        auth_token=auth_token,
    )

    note_id = response.get("id") if response else None

    test_endpoint(
        result, "List Notes", "GET", "/api/v1/notes", [200], auth_token=auth_token
    )

    test_endpoint(
        result,
        "Get Dashboard",
        "GET",
        "/api/v1/notes/dashboard",
        [200],
        auth_token=auth_token,
    )

    if note_id:
        test_endpoint(
            result,
            "Get Note by ID",
            "GET",
            f"/api/v1/notes/{note_id}",
            [200],
            auth_token=auth_token,
        )

        update_note = {"title": "Updated Note", "content": "Updated Content"}
        test_endpoint(
            result,
            "Update Note",
            "PATCH",
            f"/api/v1/notes/{note_id}",
            [200],
            update_note,
            auth_token=auth_token,
        )

        test_endpoint(
            result,
            "Get WhatsApp Draft",
            "GET",
            f"/api/v1/notes/{note_id}/whatsapp",
            [200],
            auth_token=auth_token,
        )

        test_endpoint(
            result,
            "Semantic Analysis",
            "POST",
            f"/api/v1/notes/{note_id}/semantic-analysis",
            [200, 202],
            auth_token=auth_token,
        )

    # ========================================================================
    # STEP 4: TASK ENDPOINTS
    # ========================================================================

    print(f"\n{Colors.BLUE}[STEP 4] TASK ENDPOINTS{Colors.END}\n")

    create_task = {
        "description": "Test Task",
        "priority": "MEDIUM",
        "deadline": None,
        "assigned_entities": [],
        "image_uris": [],
        "document_uris": [],
        "external_links": [],
        "communication_type": "INTERNAL",
        "is_action_approved": False,
    }
    status, response = test_endpoint(
        result,
        "Create Task",
        "POST",
        "/api/v1/tasks",
        [201, 200],
        create_task,
        auth_token=auth_token,
    )

    task_id = response.get("id") if response else None

    test_endpoint(
        result, "List Tasks", "GET", "/api/v1/tasks", [200], auth_token=auth_token
    )

    test_endpoint(
        result,
        "Get Tasks Due Today",
        "GET",
        "/api/v1/tasks/due-today",
        [200],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Get Overdue Tasks",
        "GET",
        "/api/v1/tasks/overdue",
        [200],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Get Tasks Assigned to Me",
        "GET",
        "/api/v1/tasks/assigned-to-me",
        [200],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Search Tasks",
        "GET",
        "/api/v1/tasks/search?q=test",
        [200],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Get Task Statistics",
        "GET",
        "/api/v1/tasks/stats",
        [200],
        auth_token=auth_token,
    )

    if task_id:
        test_endpoint(
            result,
            "Get Task by ID",
            "GET",
            f"/api/v1/tasks/{task_id}",
            [200],
            auth_token=auth_token,
        )

        update_task = {"description": "Updated Task", "priority": "HIGH"}
        test_endpoint(
            result,
            "Update Task",
            "PATCH",
            f"/api/v1/tasks/{task_id}",
            [200],
            update_task,
            auth_token=auth_token,
        )

        test_endpoint(
            result,
            "Duplicate Task",
            "POST",
            f"/api/v1/tasks/{task_id}/duplicate",
            [201, 200],
            auth_token=auth_token,
        )

        test_endpoint(
            result,
            "Delete Task",
            "DELETE",
            f"/api/v1/tasks/{task_id}",
            [200],
            auth_token=auth_token,
        )

    # ========================================================================
    # STEP 5: AI ENDPOINTS
    # ========================================================================

    print(f"\n{Colors.BLUE}[STEP 5] AI ENDPOINTS{Colors.END}\n")

    ai_search = {"query": "test search"}
    test_endpoint(
        result,
        "AI Search",
        "POST",
        "/api/v1/ai/search",
        [200],
        ai_search,
        auth_token=auth_token,
    )

    test_endpoint(
        result, "AI Statistics", "GET", "/api/v1/ai/stats", [200], auth_token=auth_token
    )

    # ========================================================================
    # STEP 6: ADMIN ENDPOINTS
    # ========================================================================

    print(f"\n{Colors.BLUE}[STEP 6] ADMIN ENDPOINTS{Colors.END}\n")

    test_endpoint(
        result,
        "Admin List Users",
        "GET",
        "/api/v1/admin/users",
        [200, 403],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Admin User Statistics",
        "GET",
        "/api/v1/admin/users/stats",
        [200, 403],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Admin List Notes",
        "GET",
        "/api/v1/admin/notes",
        [200, 403],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Admin List Admins",
        "GET",
        "/api/v1/admin/admins",
        [200, 403],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Admin Status",
        "GET",
        "/api/v1/admin/status",
        [200, 403],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Admin Audit Logs",
        "GET",
        "/api/v1/admin/audit-logs",
        [200, 403],
        auth_token=auth_token,
    )

    # ========================================================================
    # STEP 7: ERROR HANDLING
    # ========================================================================

    print(f"\n{Colors.BLUE}[STEP 7] ERROR HANDLING{Colors.END}\n")

    test_endpoint(result, "Unauthorized Request", "GET", "/api/v1/notes", [401])

    test_endpoint(
        result,
        "Invalid Token",
        "GET",
        "/api/v1/notes",
        [401],
        headers={"Authorization": "Bearer invalid_token"},
    )

    fake_id = str(uuid.uuid4())
    test_endpoint(
        result,
        "Nonexistent Note",
        "GET",
        f"/api/v1/notes/{fake_id}",
        [404],
        auth_token=auth_token,
    )

    test_endpoint(
        result,
        "Nonexistent Task",
        "GET",
        f"/api/v1/tasks/{fake_id}",
        [404],
        auth_token=auth_token,
    )

    invalid_task = {"description": "", "priority": "INVALID"}
    test_endpoint(
        result,
        "Invalid Task Data",
        "POST",
        "/api/v1/tasks",
        [400],
        invalid_task,
        auth_token=auth_token,
    )

    # ========================================================================
    # SUMMARY & REPORT
    # ========================================================================

    print(result.get_summary())

    # Save report
    with open(REPORT_FILE, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("                    VOICENOTE API TEST REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Base URL: {BASE_URL}\n")
        f.write(f"Test User: {test_user_email}\n\n")

        for test in result.tests:
            status = "PASS" if test["passed"] else "FAIL"
            f.write(f"[{status}] {test['method']} {test['endpoint']}\n")
            f.write(f"      Expected: {test['expected']}, Got: {test['actual']}\n")
            if test["response"]:
                f.write(f"      Response: {test['response']}\n")
            f.write("\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("                         SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total: {result.total}\n")
        f.write(f"Passed: {result.passed}\n")
        f.write(f"Failed: {result.failed}\n")
        f.write(
            f"Pass Rate: {result.passed * 100 // result.total if result.total > 0 else 0}%\n"
        )

    print(f"\n{Colors.BLUE}Report saved to: {REPORT_FILE}{Colors.END}\n")

    # Return exit code based on failures
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    exit(main())
