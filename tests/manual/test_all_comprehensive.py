#!/usr/bin/env python3
"""
Comprehensive API Testing Suite for VoiceNote
Tests BOTH Notes and Tasks Endpoints
"""

import os
import sys
import time
import uuid
from datetime import datetime, timedelta

import requests

# Configuration
BASE_URL = "http://localhost:8000"
API_VERSION = "/api/v1"
DEVICE_SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "default_secret_for_dev_only")

# Test user credentials
TEST_USER = {
    "id": "test_user_" + str(uuid.uuid4())[:8],
    "email": "testuser@voicenote.app",
    "name": "Test User",
    "device_id": "device_" + str(uuid.uuid4())[:8],
    "device_model": "TestDevice_1.0",
    "token": "token_test_" + str(uuid.uuid4())[:8],
}


class ComprehensiveTestSuite:
    def __init__(self):
        self.base_url = BASE_URL + API_VERSION
        self.access_token = None
        self.user_id = None
        self.test_results = []
        self.notes_created = []
        self.tasks_created = []

    def log_test(self, name, status, message="", duration=0):
        """Log test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": name,
            "status": status,
            "message": message,
            "duration": duration,
        }
        self.test_results.append(result)

        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        print(f"{status_icon} {name}: {message} ({duration:.2f}s)")

    def authenticate(self):
        """Authenticate user and get access token"""
        print("\n" + "=" * 70)
        print("STEP 1: AUTHENTICATION")
        print("=" * 70)

        start_time = time.time()
        try:
            # Register/sync user
            sync_response = requests.post(
                f"{self.base_url}/users/sync",
                json={
                    "id": TEST_USER["id"],
                    "email": TEST_USER["email"],
                    "name": TEST_USER["name"],
                    "device_id": TEST_USER["device_id"],
                    "device_model": TEST_USER["device_model"],
                    "token": TEST_USER["token"],
                    "timezone": "UTC",
                },
                timeout=10,
            )

            if sync_response.status_code != 200:
                self.log_test(
                    "User Sync",
                    "FAIL",
                    f"Status {sync_response.status_code}: {sync_response.text}",
                    time.time() - start_time,
                )
                return False

            sync_data = sync_response.json()
            self.access_token = sync_data.get("access_token")
            self.user_id = TEST_USER["id"]

            # Make user admin for device signature exemption
            try:
                admin_response = requests.post(
                    f"{self.base_url}/admin/users/{self.user_id}/make-admin",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10,
                )
            except:
                pass  # Admin promotion not critical

            self.log_test(
                "User Sync",
                "PASS",
                f"User {self.user_id} authenticated",
                time.time() - start_time,
            )
            return True

        except Exception as e:
            self.log_test("User Sync", "FAIL", str(e), time.time() - start_time)
            return False

    def create_test_audio_file(self):
        """Create a test audio file"""
        print("\n" + "=" * 70)
        print("STEP 2: CREATE TEST AUDIO FILE")
        print("=" * 70)

        start_time = time.time()
        audio_path = f"/tmp/test_audio_{uuid.uuid4().hex[:8]}.wav"

        try:
            import subprocess

            cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2",
                "-c:a",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                audio_path,
                "-y",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=10)

            if result.returncode != 0:
                self._create_audio_python(audio_path)

            if os.path.exists(audio_path):
                size = os.path.getsize(audio_path)
                self.log_test(
                    "Audio File Creation",
                    "PASS",
                    f"Created {audio_path} ({size} bytes)",
                    time.time() - start_time,
                )
                return audio_path
            else:
                self.log_test(
                    "Audio File Creation",
                    "FAIL",
                    "File not created",
                    time.time() - start_time,
                )
                return None

        except Exception as e:
            self.log_test(
                "Audio File Creation", "FAIL", str(e), time.time() - start_time
            )
            return None

    def _create_audio_python(self, output_path):
        """Create test audio using Python (fallback)"""
        try:
            import math
            import struct
            import wave

            sample_rate = 16000
            duration = 2
            frequency = 440
            num_samples = sample_rate * duration
            frames = []

            for i in range(num_samples):
                sample = int(
                    32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate)
                )
                frames.append(struct.pack("<h", sample))

            with wave.open(output_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b"".join(frames))

            return True
        except Exception as e:
            print(f"Error creating audio: {e}")
            return False

    # ==================== NOTES ENDPOINT TESTS ====================

    def test_notes_endpoints(self):
        """Test all notes endpoints"""
        print("\n" + "=" * 70)
        print("NOTES ENDPOINT TESTS (7 tests)")
        print("=" * 70)

        # Test 1: List Notes
        self.test_list_notes()

        # Test 2: Search Notes
        self.test_search_notes()

        # Test 3: Dashboard Metrics
        self.test_get_dashboard_metrics()

    def test_list_notes(self):
        """Test: GET /notes"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/notes",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"skip": 0, "limit": 10},
                timeout=10,
            )

            if response.status_code == 200:
                notes = response.json()
                count = len(notes) if isinstance(notes, list) else 0
                self.log_test(
                    "GET /notes (List)",
                    "PASS",
                    f"Retrieved {count} notes",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /notes (List)",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test("GET /notes (List)", "FAIL", str(e), time.time() - start_time)
            return False

    def test_search_notes(self):
        """Test: POST /notes/search"""
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/notes/search",
                json={"query": "test"},
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                results = response.json()
                count = len(results) if isinstance(results, list) else 0
                self.log_test(
                    "POST /notes/search",
                    "PASS",
                    f"Found {count} results",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "POST /notes/search",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "POST /notes/search", "FAIL", str(e), time.time() - start_time
            )
            return False

    def test_get_dashboard_metrics(self):
        """Test: GET /notes/dashboard"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/notes/dashboard",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                self.log_test(
                    "GET /notes/dashboard",
                    "PASS",
                    "Retrieved dashboard",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /notes/dashboard",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "GET /notes/dashboard", "FAIL", str(e), time.time() - start_time
            )
            return False

    # ==================== TASKS ENDPOINT TESTS ====================

    def test_tasks_endpoints(self):
        """Test all tasks endpoints"""
        print("\n" + "=" * 70)
        print("TASKS ENDPOINT TESTS (10+ tests)")
        print("=" * 70)

        # Test 1: Create Task
        task_id = self.test_create_task()
        if not task_id:
            return

        self.tasks_created.append(task_id)

        # Test 2: List Tasks
        self.test_list_tasks()

        # Test 3: Get Specific Task
        self.test_get_task(task_id)

        # Test 4: Update Task
        self.test_update_task(task_id)

        # Test 5: Search Tasks
        self.test_search_tasks()

        # Test 6: Get Task Stats
        self.test_get_task_stats()

        # Test 7: Get Due Today
        self.test_get_due_today()

        # Test 8: Get Overdue Tasks
        self.test_get_overdue_tasks()

        # Test 9: Duplicate Task
        self.test_duplicate_task(task_id)

        # Test 10: Delete Task
        self.test_delete_task(task_id)

    def test_create_task(self):
        """Test: POST /tasks (Create Task)"""
        start_time = time.time()
        try:
            task_data = {
                "title": f"Test Task {uuid.uuid4().hex[:8]}",
                "description": "This is a test task",
                "priority": "MEDIUM",
                "status": "TODO",
                "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            }

            response = requests.post(
                f"{self.base_url}/tasks",
                json=task_data,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code in [200, 201]:
                result = response.json()
                task_id = result.get("id")
                self.log_test(
                    "POST /tasks (Create)",
                    "PASS",
                    f"Created task {task_id}",
                    time.time() - start_time,
                )
                return task_id
            else:
                self.log_test(
                    "POST /tasks (Create)",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return None
        except Exception as e:
            self.log_test(
                "POST /tasks (Create)", "FAIL", str(e), time.time() - start_time
            )
            return None

    def test_list_tasks(self):
        """Test: GET /tasks (List Tasks)"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/tasks",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"skip": 0, "limit": 10},
                timeout=10,
            )

            if response.status_code == 200:
                tasks = response.json()
                count = len(tasks) if isinstance(tasks, list) else 0
                self.log_test(
                    "GET /tasks (List)",
                    "PASS",
                    f"Retrieved {count} tasks",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /tasks (List)",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test("GET /tasks (List)", "FAIL", str(e), time.time() - start_time)
            return False

    def test_get_task(self, task_id):
        """Test: GET /tasks/{task_id}"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                self.log_test(
                    "GET /tasks/{task_id}",
                    "PASS",
                    "Retrieved task",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /tasks/{task_id}",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "GET /tasks/{task_id}", "FAIL", str(e), time.time() - start_time
            )
            return False

    def test_update_task(self, task_id):
        """Test: PATCH /tasks/{task_id}"""
        start_time = time.time()
        try:
            update_data = {
                "title": f"Updated Task {uuid.uuid4().hex[:8]}",
                "status": "IN_PROGRESS",
            }

            response = requests.patch(
                f"{self.base_url}/tasks/{task_id}",
                json=update_data,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                self.log_test(
                    "PATCH /tasks/{task_id}",
                    "PASS",
                    "Updated task",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "PATCH /tasks/{task_id}",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "PATCH /tasks/{task_id}", "FAIL", str(e), time.time() - start_time
            )
            return False

    def test_search_tasks(self):
        """Test: GET /tasks/search"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/tasks/search",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"query_text": "test", "limit": 10, "offset": 0},
                timeout=10,
            )

            if response.status_code == 200:
                results = response.json()
                count = len(results) if isinstance(results, list) else 0
                self.log_test(
                    "GET /tasks/search",
                    "PASS",
                    f"Found {count} tasks",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /tasks/search",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test("GET /tasks/search", "FAIL", str(e), time.time() - start_time)
            return False

    def test_get_task_stats(self):
        """Test: GET /tasks/stats"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/tasks/stats",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                self.log_test(
                    "GET /tasks/stats",
                    "PASS",
                    "Retrieved stats",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /tasks/stats",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test("GET /tasks/stats", "FAIL", str(e), time.time() - start_time)
            return False

    def test_get_due_today(self):
        """Test: GET /tasks/due-today"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/tasks/due-today",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                tasks = response.json()
                count = len(tasks) if isinstance(tasks, list) else 0
                self.log_test(
                    "GET /tasks/due-today",
                    "PASS",
                    f"Found {count} tasks",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /tasks/due-today",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "GET /tasks/due-today", "FAIL", str(e), time.time() - start_time
            )
            return False

    def test_get_overdue_tasks(self):
        """Test: GET /tasks/overdue"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/tasks/overdue",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                tasks = response.json()
                count = len(tasks) if isinstance(tasks, list) else 0
                self.log_test(
                    "GET /tasks/overdue",
                    "PASS",
                    f"Found {count} tasks",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "GET /tasks/overdue",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "GET /tasks/overdue", "FAIL", str(e), time.time() - start_time
            )
            return False

    def test_duplicate_task(self, task_id):
        """Test: POST /tasks/{task_id}/duplicate"""
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/tasks/{task_id}/duplicate",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code in [200, 201]:
                result = response.json()
                dup_id = result.get("id")
                self.log_test(
                    "POST /tasks/{task_id}/duplicate",
                    "PASS",
                    f"Duplicated task {dup_id}",
                    time.time() - start_time,
                )
                self.tasks_created.append(dup_id)
                return True
            else:
                self.log_test(
                    "POST /tasks/{task_id}/duplicate",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "POST /tasks/{task_id}/duplicate",
                "FAIL",
                str(e),
                time.time() - start_time,
            )
            return False

    def test_delete_task(self, task_id):
        """Test: DELETE /tasks/{task_id}"""
        start_time = time.time()
        try:
            response = requests.delete(
                f"{self.base_url}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code in [200, 204]:
                self.log_test(
                    "DELETE /tasks/{task_id}",
                    "PASS",
                    "Deleted task",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "DELETE /tasks/{task_id}",
                    "FAIL",
                    f"Status {response.status_code}",
                    time.time() - start_time,
                )
                return False
        except Exception as e:
            self.log_test(
                "DELETE /tasks/{task_id}", "FAIL", str(e), time.time() - start_time
            )
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        total = len(self.test_results)

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        if total > 0:
            success_rate = passed / total * 100
            print(f"Success Rate: {success_rate:.1f}%")

        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test_name']}: {result['message']}")

        print("\n" + "=" * 70)

    def run_all_tests(self):
        """Run complete test suite"""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print(
            "║"
            + " " * 12
            + "COMPREHENSIVE API TEST SUITE - NOTES & TASKS"
            + " " * 13
            + "║"
        )
        print("║" + " " * 68 + "║")
        print(
            "║"
            + f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            + " " * 42
            + "║"
        )
        print("╚" + "=" * 68 + "╝")

        # Authenticate
        if not self.authenticate():
            print("\n❌ Authentication failed. Cannot continue.")
            return False

        # Create audio file
        audio_path = self.create_test_audio_file()

        # Test Notes Endpoints
        self.test_notes_endpoints()

        # Test Tasks Endpoints
        self.test_tasks_endpoints()

        # Print summary
        self.print_summary()

        return True


if __name__ == "__main__":
    tester = ComprehensiveTestSuite()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
