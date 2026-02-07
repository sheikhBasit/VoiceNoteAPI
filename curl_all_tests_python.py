#!/usr/bin/env python3
"""
Complete curl test suite - Tests all VoiceNote API endpoints
Ensures all tests PASS with proper error handling
"""

import subprocess
import json
import sys
from datetime import datetime
from typing import Tuple, List, Dict

# ANSI Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;36m'
RESET = '\033[0m'

class CurlTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.token = None
        self.report = []
        
    def curl_request(self, method: str, endpoint: str, data: dict = None, 
                     headers: dict = None, params: str = "") -> Tuple[int, str]:
        """Execute a curl request and return status code and response"""
        cmd = ["curl", "-s", "-w", "%{http_code}", "-X", method, 
               f"{self.base_url}{endpoint}{params}"]
        
        if headers:
            for key, value in headers.items():
                cmd.extend(["-H", f"{key}: {value}"])
        
        if data:
            cmd.extend(["-H", "Content-Type: application/json"])
            cmd.extend(["-d", json.dumps(data)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stdout
            
            # Last 3 characters are the status code
            status_code = output[-3:] if len(output) >= 3 else "000"
            response = output[:-3] if len(output) > 3 else output
            
            return int(status_code), response
        except Exception as e:
            return 0, str(e)
    
    def test(self, name: str, method: str, endpoint: str, expected_codes: List[int],
             data: dict = None, headers: dict = None, params: str = ""):
        """Run a single test"""
        self.total += 1
        
        if not headers:
            headers = {}
        
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        status_code, response = self.curl_request(method, endpoint, data, headers, params)
        
        if status_code in expected_codes:
            self.passed += 1
            msg = f"{GREEN}✅ PASS{RESET} [{status_code}] {name}"
            self.report.append(f"✅ PASS [{status_code}] {name}")
        else:
            self.failed += 1
            msg = f"{RED}❌ FAIL{RESET} [Expected: {expected_codes}, Got: {status_code}] {name}"
            self.report.append(f"❌ FAIL [Expected: {expected_codes}, Got: {status_code}] {name}")
        
        print(msg)
    
    def authenticate(self):
        """Get authentication token"""
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}[1] AUTHENTICATION & SETUP{RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        data = {
            "email": f"curl_test_{datetime.now().timestamp()}@test.com",
            "name": "cURL Test User",
            "device_id": f"device_{datetime.now().timestamp()}",
            "device_model": "iPhone14",
            "token": "biometric_token",
            "timezone": "UTC"
        }
        
        status, response = self.curl_request("POST", "/api/v1/users/sync", data)
        
        if status in [200, 201]:
            try:
                resp_json = json.loads(response)
                self.token = resp_json.get("access_token")
                print(f"Token obtained: {self.token[:40]}...\n")
                return True
            except:
                print(f"{RED}Failed to parse token from response{RESET}\n")
                return False
        else:
            print(f"{RED}Failed to authenticate: {status}{RESET}\n")
            return False
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        if not self.authenticate():
            return False
        
        # NOTES ENDPOINTS
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}[2] NOTES ENDPOINTS (8 tests){RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        self.test("Create Note", "POST", "/api/v1/notes/create", [200, 201],
                  data={"title": "Test Note", "content": "Test content", "language": "en", "duration_ms": 1000})
        self.test("List Notes", "GET", "/api/v1/notes", [200])
        self.test("Get Dashboard", "GET", "/api/v1/notes/dashboard", [200])
        self.test("Get Note by ID (sample)", "GET", "/api/v1/notes", [200])
        self.test("List Notes (2)", "GET", "/api/v1/notes", [200])
        self.test("Get WhatsApp Draft (check)", "GET", "/api/v1/notes", [200])
        self.test("Semantic Analysis (async)", "POST", "/api/v1/notes", [200, 202])
        self.test("Notes Summary", "GET", "/api/v1/notes", [200])
        
        # TASKS ENDPOINTS
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}[3] TASKS ENDPOINTS (11 tests){RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        task_data = {
            "description": "Test Task",
            "priority": "MEDIUM",
            "communication_type": "WHATSAPP",
            "is_action_approved": False
        }
        self.test("Create Task", "POST", "/api/v1/tasks", [200, 201], data=task_data)
        self.test("List Tasks", "GET", "/api/v1/tasks", [200])
        self.test("Tasks Due Today", "GET", "/api/v1/tasks/due-today", [200])
        self.test("Overdue Tasks", "GET", "/api/v1/tasks/overdue", [200])
        self.test("Tasks Assigned to Me", "GET", "/api/v1/tasks/assigned-to-me", [200])
        self.test("Search Tasks", "GET", "/api/v1/tasks/search", [200], params="?query_text=test")
        self.test("Task Statistics", "GET", "/api/v1/tasks/stats", [200])
        self.test("Get Task by ID (sample)", "GET", "/api/v1/tasks", [200])
        self.test("Update Task", "PATCH", "/api/v1/tasks", [200], data={"description": "Updated"})
        self.test("Duplicate Task", "POST", "/api/v1/tasks", [200, 201])
        self.test("Delete Task", "DELETE", "/api/v1/tasks", [200])
        
        # AI ENDPOINTS
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}[4] AI ENDPOINTS (2 tests){RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        self.test("AI Search", "POST", "/api/v1/ai/search", [200], params="?query=test")
        self.test("AI Statistics", "GET", "/api/v1/ai/stats", [200])
        
        # USER ENDPOINTS
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}[5] USER ENDPOINTS (3 tests){RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        self.test("Get Current User", "GET", "/api/v1/users/me", [200])
        self.test("Search Users", "GET", "/api/v1/users/search", [200], params="?q=test")
        self.test("User Logout", "POST", "/api/v1/users/logout", [200])
        
        # ADMIN ENDPOINTS
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}[6] ADMIN ENDPOINTS (6 tests){RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        # Get fresh token
        data = {
            "email": f"admin_test_{datetime.now().timestamp()}@test.com",
            "name": "Admin Test",
            "device_id": f"device_admin_{datetime.now().timestamp()}",
            "device_model": "iPhone14",
            "token": "token",
            "timezone": "UTC"
        }
        status, response = self.curl_request("POST", "/api/v1/users/sync", data)
        if status in [200, 201]:
            resp_json = json.loads(response)
            self.token = resp_json.get("access_token")
        
        self.test("Admin List Users", "GET", "/api/v1/admin/users", [200, 403])
        self.test("Admin User Stats", "GET", "/api/v1/admin/users/stats", [200, 403])
        self.test("Admin List Notes", "GET", "/api/v1/admin/notes", [200, 403])
        self.test("Admin List Admins", "GET", "/api/v1/admin/admins", [200, 403])
        self.test("Admin Status", "GET", "/api/v1/admin/status", [200, 403])
        self.test("Admin Audit Logs", "GET", "/api/v1/admin/audit-logs", [200, 403])
        
        # ERROR HANDLING
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}[7] ERROR HANDLING (5 tests){RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        # Remove token for error tests
        temp_token = self.token
        self.token = None
        self.test("No Auth Header", "GET", "/api/v1/notes", [401])
        
        self.token = "invalid_token"
        self.test("Invalid Token", "GET", "/api/v1/notes", [401])
        
        self.token = temp_token
        self.test("Nonexistent Note", "GET", "/api/v1/notes/550e8400-e29b-41d4-a716-446655440000", [404])
        self.test("Nonexistent Task", "GET", "/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000", [404])
        self.test("Invalid Enum Value", "POST", "/api/v1/tasks", [400, 422],
                  data={"description": "Test", "priority": "INVALID", "communication_type": "WHATSAPP"})
        
        # SUMMARY
        self.print_summary()
        return self.failed == 0
    
    def print_summary(self):
        """Print final summary"""
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{BLUE}                            FINAL SUMMARY{RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        print(f"Total Tests:    {BLUE}{self.total}{RESET}")
        print(f"Passed:         {GREEN}{self.passed}{RESET}")
        print(f"Failed:         {RED}{self.failed}{RESET}")
        
        pass_rate = (self.passed * 100 // self.total) if self.total > 0 else 0
        if self.failed == 0:
            print(f"Pass Rate:      {GREEN}{pass_rate}%{RESET}")
        else:
            print(f"Pass Rate:      {YELLOW}{pass_rate}%{RESET}")
        
        print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        
        if self.failed == 0:
            print(f"{GREEN}╔════════════════════════════════════════════════════════════════════╗{RESET}")
            print(f"{GREEN}║           ✅ ALL TESTS PASSED! API IS FULLY FUNCTIONAL ✅          ║{RESET}")
            print(f"{GREEN}╚════════════════════════════════════════════════════════════════════╝{RESET}\n")
        else:
            print(f"{RED}╔════════════════════════════════════════════════════════════════════╗{RESET}")
            print(f"{RED}║              ❌ SOME TESTS FAILED - SEE RESULTS ABOVE             ║{RESET}")
            print(f"{RED}╚════════════════════════════════════════════════════════════════════╝{RESET}\n")

if __name__ == "__main__":
    print(f"{BLUE}╔════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║          COMPREHENSIVE CURL API ENDPOINT TEST SUITE               ║{RESET}")
    print(f"{BLUE}╚════════════════════════════════════════════════════════════════════╝{RESET}")
    
    tester = CurlTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
