#!/usr/bin/env python3
"""Comprehensive API Test Suite for VoiceNoteAPI"""
import httpx
import json
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

class ComprehensiveAPITester:
    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
        self.user_token = None
        self.admin_token = None
        self.test_user_id = "test_runner_" + str(uuid.uuid4())[:8]
        self.test_note_id = None
        self.test_task_id = None
        self.results = []
        self.category = ""

    def log(self, endpoint, method, status, success, detail=""):
        self.results.append({
            "category": self.category,
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "success": success,
            "detail": detail
        })
        icon = "✅" if success else "❌"
        print(f"{icon} [{method:6}] {endpoint:50} - {status}")

    # ==================== AUTHENTICATION ====================
    def test_user_sync(self):
        self.category = "Authentication"
        url = f"{BASE_URL}/users/sync"
        payload = {
            "id": self.test_user_id,
            "name": "Test Runner",
            "email": f"{self.test_user_id}@test.com",
            "token": "test_device_token",
            "device_id": "test_device_id",
            "device_model": "TestBot",
            "primary_role": "DEVELOPER"
        }
        res = self.client.post(url, json=payload)
        if res.status_code == 200:
            self.user_token = res.json().get("access_token")
        self.log("/users/sync", "POST", res.status_code, res.status_code == 200)

    def test_admin_sync(self):
        url = f"{BASE_URL}/users/sync"
        payload = {
            "id": "admin_user_001",
            "name": "System Admin",
            "email": "admin@voicenote.app",
            "token": "admin_token_001",
            "device_id": "admin_device_001",
            "device_model": "Server",
            "primary_role": "GENERIC"
        }
        res = self.client.post(url, json=payload)
        if res.status_code == 200:
            self.admin_token = res.json().get("access_token")
        self.log("/users/sync (Admin)", "POST", res.status_code, res.status_code == 200)

    # ==================== USERS ====================
    def test_users_module(self):
        self.category = "Users"
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # GET /me
        res = self.client.get(f"{BASE_URL}/users/me", headers=headers)
        self.log("/users/me", "GET", res.status_code, res.status_code == 200)
        
        # PATCH /me
        res = self.client.patch(f"{BASE_URL}/users/me", 
            json={"name": "Updated Test Runner"}, headers=headers)
        self.log("/users/me", "PATCH", res.status_code, res.status_code == 200)
        
        # GET /search
        res = self.client.get(f"{BASE_URL}/users/search?query=Test", headers=headers)
        self.log("/users/search", "GET", res.status_code, res.status_code == 200)

    # ==================== NOTES ====================
    def test_notes_module(self):
        self.category = "Notes"
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # GET /notes (list)
        res = self.client.get(f"{BASE_URL}/notes", headers=headers)
        self.log("/notes", "GET", res.status_code, res.status_code == 200)
        
        # Try to get first note for semantic analysis test
        if res.status_code == 200:
            notes = res.json()
            if notes and len(notes) > 0:
                self.test_note_id = notes[0].get("id")
        
        # GET /dashboard
        res = self.client.get(f"{BASE_URL}/notes/dashboard", headers=headers)
        self.log("/notes/dashboard", "GET", res.status_code, res.status_code == 200)
        
        # POST /search
        res = self.client.post(f"{BASE_URL}/notes/search", 
            json={"query": "test"}, headers=headers)
        self.log("/notes/search", "POST", res.status_code, res.status_code == 200)
        
        # Test semantic analysis if we have a note
        if self.test_note_id:
            res = self.client.post(
                f"{BASE_URL}/notes/{self.test_note_id}/semantic-analysis",
                headers=headers
            )
            self.log(f"/notes/{{id}}/semantic-analysis", "POST", 
                res.status_code, res.status_code in [200, 400])

    # ==================== TASKS ====================
    def test_tasks_module(self):
        self.category = "Tasks"
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # GET /tasks
        res = self.client.get(f"{BASE_URL}/tasks", headers=headers)
        self.log("/tasks", "GET", res.status_code, res.status_code == 200)

    # ==================== ADMIN ====================
    def test_admin_module(self):
        self.category = "Admin"
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # GET /status
        res = self.client.get(f"{BASE_URL}/admin/status", headers=headers)
        self.log("/admin/status", "GET", res.status_code, res.status_code == 200)
        
        # GET /settings/ai
        res = self.client.get(f"{BASE_URL}/admin/settings/ai", headers=headers)
        self.log("/admin/settings/ai", "GET", res.status_code, res.status_code == 200)
        
        # PATCH /settings/ai (NEW FEATURE TEST)
        res = self.client.patch(f"{BASE_URL}/admin/settings/ai",
            json={"temperature": 5, "llm_model": "llama-3.1-8b-instant"},
            headers=headers)
        self.log("/admin/settings/ai", "PATCH", res.status_code, res.status_code == 200)
        
        # GET /users (admin user list)
        res = self.client.get(f"{BASE_URL}/admin/users", headers=headers)
        self.log("/admin/users", "GET", res.status_code, res.status_code == 200)

    # ==================== REPORT ====================
    def generate_report(self):
        report = f"# Comprehensive API Test Report\n"
        report += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        
        report += f"## Summary\n"
        report += f"- **Total Tests**: {total}\n"
        report += f"- **Passed**: {passed} ✅\n"
        report += f"- **Failed**: {failed} ❌\n"
        report += f"- **Success Rate**: {(passed/total*100):.1f}%\n\n"
        
        # Group by category
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)
        
        for cat, tests in categories.items():
            report += f"## {cat}\n\n"
            report += "| Endpoint | Method | Status | Result | Detail |\n"
            report += "|----------|--------|--------|--------|--------|\n"
            for t in tests:
                icon = "✅" if t["success"] else "❌"
                report += f"| {t['endpoint']} | {t['method']} | {t['status']} | {icon} | {t['detail']} |\n"
            report += "\n"
        
        with open("test_results.md", "w") as f:
            f.write(report)
        
        print(f"\n{'='*60}")
        print(f"Report saved to test_results.md")
        print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
        print(f"{'='*60}")

    def run_all(self):
        print("Starting Comprehensive API Tests...\n")
        self.test_user_sync()
        self.test_admin_sync()
        
        if self.user_token:
            self.test_users_module()
            self.test_notes_module()
            self.test_tasks_module()
        
        if self.admin_token:
            self.test_admin_module()
        
        self.generate_report()

if __name__ == "__main__":
    tester = ComprehensiveAPITester()
    tester.run_all()
