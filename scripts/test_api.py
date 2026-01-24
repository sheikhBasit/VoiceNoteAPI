import httpx
import json
import uuid
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

class APITester:
    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
        self.user_token = None
        self.admin_token = None
        self.test_user_id = "test_runner_" + str(uuid.uuid4())[:8]
        self.test_note_id = None
        self.results = []

    def log_result(self, endpoint, method, status_code, success, detail=""):
        self.results.append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "success": success,
            "detail": detail
        })
        print(f"[{method}] {endpoint} - {status_code} - {'PASS' if success else 'FAIL'}")

    def test_sync_user(self):
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
            self.log_result("/users/sync", "POST", res.status_code, True)
        else:
            self.log_result("/users/sync", "POST", res.status_code, False, res.text)

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
            self.log_result("/users/sync (Admin)", "POST", res.status_code, True)

    def test_create_note(self):
        # We'll mock a note creation. Since /notes POST usually expects a file,
        # we'll look for an endpoint that allows text-based creation or just use 
        # the DB to inject if necessary. 
        # Wait, the app has a `process` endpoint for audio. 
        # Let's see if there's a simple 'create' endpoint in notes.py
        pass

    def test_admin_settings_update(self):
        url = f"{BASE_URL}/admin/settings/ai"
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        payload = {
            "temperature": 7,
            "llm_model": "llama-3.1-8b-instant"
        }
        res = self.client.patch(url, json=payload, headers=headers)
        if res.status_code == 200:
            self.log_result("/admin/settings/ai", "PATCH", res.status_code, True)
        else:
            self.log_result("/admin/settings/ai", "PATCH", res.status_code, False, res.text)

    def test_get_ai_settings(self):
        url = f"{BASE_URL}/admin/settings/ai"
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.get(url, headers=headers)
        self.log_result("/admin/settings/ai", "GET", res.status_code, res.status_code == 200)

    def run_all(self):
        self.test_sync_user()
        self.test_admin_sync()
        if self.admin_token:
            self.test_get_ai_settings()
            self.test_admin_settings_update()
        
        self.generate_report()

    def generate_report(self):
        report = f"# API Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "| Endpoint | Method | Status | Success | Detail |\n"
        report += "|----------|--------|--------|---------|--------|\n"
        for r in self.results:
            report += f"| {r['endpoint']} | {r['method']} | {r['status_code']} | {'✅' if r['success'] else '❌'} | {r['detail']} |\n"
        
        with open("test_results.md", "w") as f:
            f.write(report)

if __name__ == "__main__":
    tester = APITester()
    tester.run_all()
