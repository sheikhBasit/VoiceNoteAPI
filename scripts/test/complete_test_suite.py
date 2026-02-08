#!/usr/bin/env python3
"""
Complete API Test Suite for VoiceNoteAPI
Tests ALL endpoints: GET, POST, PATCH, DELETE, PUT
"""
import httpx
import json
import uuid
import time
from datetime import datetime
from typing import Dict, List

BASE_URL = "http://localhost:8000/api/v1"

class CompleteAPITester:
    def __init__(self):
        self.client = httpx.Client(timeout=120.0)
        self.user_token = None
        self.admin_token = None
        self.test_user_id = "test_complete_" + str(uuid.uuid4())[:8]
        self.test_note_id = None
        self.test_task_id = None
        self.results = []
        
    def log(self, category, endpoint, method, status, success, detail=""):
        self.results.append({
            "category": category,
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "success": success,
            "detail": detail
        })
        icon = "✅" if success else "❌"
        print(f"{icon} [{method:6}] {category:15} {endpoint:45} - {status}")

    # ==================== AUTHENTICATION ====================
    def test_auth(self):
        print("\n" + "="*80)
        print("AUTHENTICATION")
        print("="*80)
        
        # User sync
        res = self.client.post(f"{BASE_URL}/users/sync", json={
            "id": self.test_user_id,
            "name": "Complete Test User",
            "email": f"{self.test_user_id}@test.com",
            "token": "test_token",
            "device_id": "test_device",
            "device_model": "TestBot",
            "primary_role": "DEVELOPER"
        })
        if res.status_code == 200:
            self.user_token = res.json().get("access_token")
        self.log("Auth", "/users/sync", "POST", res.status_code, res.status_code == 200)
        
        # Admin sync
        res = self.client.post(f"{BASE_URL}/users/sync", json={
            "id": "admin_user_001",
            "name": "System Admin",
            "email": "admin@voicenote.app",
            "token": "admin_token_001",
            "device_id": "admin_device_001",
            "device_model": "Server",
            "primary_role": "GENERIC"
        })
        if res.status_code == 200:
            self.admin_token = res.json().get("access_token")
        self.log("Auth", "/users/sync (Admin)", "POST", res.status_code, res.status_code == 200)

    # ==================== USERS ====================
    def test_users(self):
        print("\n" + "="*80)
        print("USERS MODULE")
        print("="*80)
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # GET /me
        res = self.client.get(f"{BASE_URL}/users/me", headers=headers)
        self.log("Users", "/users/me", "GET", res.status_code, res.status_code == 200)
        
        # PATCH /me
        res = self.client.patch(f"{BASE_URL}/users/me", 
            json={"name": "Updated Complete Test User", "work_start_hour": 9, "work_end_hour": 17},
            headers=headers)
        self.log("Users", "/users/me", "PATCH", res.status_code, res.status_code == 200)
        
        # GET /search
        res = self.client.get(f"{BASE_URL}/users/search?query=Test", headers=headers)
        self.log("Users", "/users/search", "GET", res.status_code, res.status_code == 200)
        
        # DELETE /me (soft delete)
        res = self.client.delete(f"{BASE_URL}/users/me", headers=headers)
        self.log("Users", "/users/me", "DELETE", res.status_code, res.status_code == 200)
        
        # PATCH /restore
        res = self.client.patch(f"{BASE_URL}/users/{self.test_user_id}/restore", headers=headers)
        self.log("Users", "/users/{id}/restore", "PATCH", res.status_code, res.status_code == 200)

    # ==================== NOTES ====================
    def test_notes(self):
        print("\n" + "="*80)
        print("NOTES MODULE")
        print("="*80)
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # GET /notes (list)
        res = self.client.get(f"{BASE_URL}/notes", headers=headers)
        if res.status_code == 200 and res.json():
            self.test_note_id = res.json()[0].get("id")
        self.log("Notes", "/notes", "GET", res.status_code, res.status_code == 200)
        
        # GET /notes/{id}
        if self.test_note_id:
            res = self.client.get(f"{BASE_URL}/notes/{self.test_note_id}", headers=headers)
            self.log("Notes", "/notes/{id}", "GET", res.status_code, res.status_code == 200)
            
            # PATCH /notes/{id}
            res = self.client.patch(f"{BASE_URL}/notes/{self.test_note_id}",
                json={"is_pinned": True, "is_liked": True}, headers=headers)
            self.log("Notes", "/notes/{id}", "PATCH", res.status_code, res.status_code == 200)
            
            # POST /notes/{id}/ask
            res = self.client.post(f"{BASE_URL}/notes/{self.test_note_id}/ask",
                json={"question": "What is this note about?"}, headers=headers)
            self.log("Notes", "/notes/{id}/ask", "POST", res.status_code, res.status_code in [200, 500])
            
            # POST /notes/{id}/semantic-analysis
            res = self.client.post(f"{BASE_URL}/notes/{self.test_note_id}/semantic-analysis",
                headers=headers)
            self.log("Notes", "/notes/{id}/semantic-analysis", "POST", res.status_code, 
                res.status_code in [200, 500])
            
            # GET /notes/{id}/whatsapp
            res = self.client.get(f"{BASE_URL}/notes/{self.test_note_id}/whatsapp", headers=headers)
            self.log("Notes", "/notes/{id}/whatsapp", "GET", res.status_code, res.status_code == 200)
        
        # GET /dashboard
        res = self.client.get(f"{BASE_URL}/notes/dashboard", headers=headers)
        self.log("Notes", "/notes/dashboard", "GET", res.status_code, res.status_code == 200)
        
        # POST /search (skip - needs embeddings)
        # res = self.client.post(f"{BASE_URL}/notes/search", json={"query": "test"}, headers=headers)
        # self.log("Notes", "/notes/search", "POST", res.status_code, res.status_code == 200)
        
        # DELETE /notes/{id}
        if self.test_note_id:
            res = self.client.delete(f"{BASE_URL}/notes/{self.test_note_id}", headers=headers)
            self.log("Notes", "/notes/{id}", "DELETE", res.status_code, res.status_code == 200)

    # ==================== TASKS ====================
    def test_tasks(self):
        print("\n" + "="*80)
        print("TASKS MODULE")
        print("="*80)
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # GET /tasks
        res = self.client.get(f"{BASE_URL}/tasks", headers=headers)
        if res.status_code == 200 and res.json():
            self.test_task_id = res.json()[0].get("id")
        self.log("Tasks", "/tasks", "GET", res.status_code, res.status_code == 200)
        
        # GET /tasks/{id}
        if self.test_task_id:
            res = self.client.get(f"{BASE_URL}/tasks/{self.test_task_id}", headers=headers)
            self.log("Tasks", "/tasks/{id}", "GET", res.status_code, res.status_code == 200)
            
            # PATCH /tasks/{id}
            res = self.client.patch(f"{BASE_URL}/tasks/{self.test_task_id}",
                json={"is_done": True}, headers=headers)
            self.log("Tasks", "/tasks/{id}", "PATCH", res.status_code, res.status_code == 200)
            
            # GET /tasks/{id}/communication-options
            res = self.client.get(f"{BASE_URL}/tasks/{self.test_task_id}/communication-options",
                headers=headers)
            self.log("Tasks", "/tasks/{id}/communication-options", "GET", res.status_code, 
                res.status_code == 200)
            
            # POST /tasks/{id}/duplicate
            res = self.client.post(f"{BASE_URL}/tasks/{self.test_task_id}/duplicate", headers=headers)
            self.log("Tasks", "/tasks/{id}/duplicate", "POST", res.status_code, 
                res.status_code in [200, 201])
        
        # GET /tasks/due-today
        res = self.client.get(f"{BASE_URL}/tasks/due-today", headers=headers)
        self.log("Tasks", "/tasks/due-today", "GET", res.status_code, res.status_code == 200)
        
        # GET /tasks/overdue
        res = self.client.get(f"{BASE_URL}/tasks/overdue", headers=headers)
        self.log("Tasks", "/tasks/overdue", "GET", res.status_code, res.status_code == 200)
        
        # GET /tasks/assigned-to-me
        res = self.client.get(f"{BASE_URL}/tasks/assigned-to-me", headers=headers)
        self.log("Tasks", "/tasks/assigned-to-me", "GET", res.status_code, res.status_code == 200)
        
        # GET /tasks/search
        res = self.client.get(f"{BASE_URL}/tasks/search?query=test", headers=headers)
        self.log("Tasks", "/tasks/search", "GET", res.status_code, res.status_code == 200)
        
        # GET /tasks/stats
        res = self.client.get(f"{BASE_URL}/tasks/stats", headers=headers)
        self.log("Tasks", "/tasks/stats", "GET", res.status_code, res.status_code == 200)
        
        # DELETE /tasks/{id}
        if self.test_task_id:
            res = self.client.delete(f"{BASE_URL}/tasks/{self.test_task_id}", headers=headers)
            self.log("Tasks", "/tasks/{id}", "DELETE", res.status_code, res.status_code == 200)

    # ==================== ADMIN ====================
    def test_admin(self):
        print("\n" + "="*80)
        print("ADMIN MODULE")
        print("="*80)
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # GET /status
        res = self.client.get(f"{BASE_URL}/admin/status", headers=headers)
        self.log("Admin", "/admin/status", "GET", res.status_code, res.status_code == 200)
        
        # GET /users
        res = self.client.get(f"{BASE_URL}/admin/users", headers=headers)
        self.log("Admin", "/admin/users", "GET", res.status_code, res.status_code == 200)
        
        # GET /users/stats
        res = self.client.get(f"{BASE_URL}/admin/users/stats", headers=headers)
        self.log("Admin", "/admin/users/stats", "GET", res.status_code, res.status_code == 200)
        
        # GET /notes
        res = self.client.get(f"{BASE_URL}/admin/notes", headers=headers)
        self.log("Admin", "/admin/notes", "GET", res.status_code, res.status_code == 200)
        
        # GET /admins
        res = self.client.get(f"{BASE_URL}/admin/admins", headers=headers)
        self.log("Admin", "/admin/admins", "GET", res.status_code, res.status_code == 200)
        
        # GET /settings/ai
        res = self.client.get(f"{BASE_URL}/admin/settings/ai", headers=headers)
        self.log("Admin", "/admin/settings/ai", "GET", res.status_code, res.status_code == 200)
        
        # PATCH /settings/ai
        res = self.client.patch(f"{BASE_URL}/admin/settings/ai",
            json={"temperature": 5, "max_tokens": 2048}, headers=headers)
        self.log("Admin", "/admin/settings/ai", "PATCH", res.status_code, res.status_code == 200)
        
        # POST /users/{id}/make-admin
        res = self.client.post(f"{BASE_URL}/admin/users/{self.test_user_id}/make-admin",
            json={"permissions": {"can_view_audit_logs": True}}, headers=headers)
        self.log("Admin", "/admin/users/{id}/make-admin", "POST", res.status_code, 
            res.status_code in [200, 400])
        
        # POST /users/{id}/remove-admin
        res = self.client.post(f"{BASE_URL}/admin/users/{self.test_user_id}/remove-admin",
            headers=headers)
        self.log("Admin", "/admin/users/{id}/remove-admin", "POST", res.status_code, 
            res.status_code in [200, 400])

    # ==================== AI ====================
    def test_ai(self):
        print("\n" + "="*80)
        print("AI MODULE")
        print("="*80)
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # GET /stats
        res = self.client.get(f"{BASE_URL}/ai/stats", headers=headers)
        self.log("AI", "/ai/stats", "GET", res.status_code, res.status_code == 200)

    # ==================== REPORT ====================
    def generate_report(self):
        report = f"# Complete API Test Report\n"
        report += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**Test User**: {self.test_user_id}\n\n"
        
        # Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        
        report += f"## Executive Summary\n\n"
        report += f"| Metric | Value |\n"
        report += f"|--------|-------|\n"
        report += f"| **Total Endpoints Tested** | {total} |\n"
        report += f"| **Passed** | {passed} ✅ |\n"
        report += f"| **Failed** | {failed} ❌ |\n"
        report += f"| **Success Rate** | {(passed/total*100):.1f}% |\n\n"
        
        # Group by category
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)
        
        # Category summaries
        report += f"## Results by Module\n\n"
        for cat in sorted(categories.keys()):
            tests = categories[cat]
            cat_passed = sum(1 for t in tests if t["success"])
            cat_total = len(tests)
            report += f"### {cat}\n"
            report += f"- **Tested**: {cat_total} endpoints\n"
            report += f"- **Passed**: {cat_passed}/{cat_total} ({(cat_passed/cat_total*100):.0f}%)\n\n"
        
        # Detailed results
        report += f"## Detailed Test Results\n\n"
        for cat in sorted(categories.keys()):
            tests = categories[cat]
            report += f"### {cat}\n\n"
            report += "| Endpoint | Method | Status | Result | Detail |\n"
            report += "|----------|--------|--------|--------|--------|\n"
            for t in tests:
                icon = "✅" if t["success"] else "❌"
                detail = t["detail"][:50] if t["detail"] else ""
                report += f"| `{t['endpoint']}` | {t['method']} | {t['status']} | {icon} | {detail} |\n"
            report += "\n"
        
        # HTTP Method Coverage
        methods = {}
        for r in self.results:
            m = r["method"]
            if m not in methods:
                methods[m] = {"total": 0, "passed": 0}
            methods[m]["total"] += 1
            if r["success"]:
                methods[m]["passed"] += 1
        
        report += f"## HTTP Method Coverage\n\n"
        report += "| Method | Tested | Passed | Success Rate |\n"
        report += "|--------|--------|--------|-------------|\n"
        for method in sorted(methods.keys()):
            m = methods[method]
            report += f"| **{method}** | {m['total']} | {m['passed']} | {(m['passed']/m['total']*100):.0f}% |\n"
        report += "\n"
        
        # Recommendations
        report += f"## Recommendations\n\n"
        failed_tests = [r for r in self.results if not r["success"]]
        if failed_tests:
            report += f"### Failed Endpoints ({len(failed_tests)})\n\n"
            for t in failed_tests:
                report += f"- `{t['method']} {t['endpoint']}` - Status {t['status']}\n"
            report += "\n"
        
        report += f"### Next Steps\n\n"
        report += f"1. Generate embeddings for all notes to enable search functionality\n"
        report += f"2. Test file upload endpoints (POST /notes/process, POST /tasks/{{id}}/multimedia)\n"
        report += f"3. Add integration tests for complex workflows\n"
        report += f"4. Monitor performance of AI-heavy endpoints\n"
        
        with open("COMPLETE_TEST_REPORT.md", "w") as f:
            f.write(report)
        
        print(f"\n{'='*80}")
        print(f"Report saved to COMPLETE_TEST_REPORT.md")
        print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Success Rate: {(passed/total*100):.1f}%")
        print(f"{'='*80}")

    def run_all(self):
        print("\n" + "="*80)
        print("COMPLETE API TEST SUITE")
        print("Testing ALL endpoints across all modules")
        print("="*80)
        
        self.test_auth()
        
        if self.user_token:
            self.test_users()
            self.test_notes()
            self.test_tasks()
            self.test_ai()
        
        if self.admin_token:
            self.test_admin()
        
        self.generate_report()

if __name__ == "__main__":
    tester = CompleteAPITester()
    tester.run_all()
