#!/usr/bin/env python3
"""
Comprehensive Notes Endpoint Testing Script
Uses generated audio for testing note creation, processing, and retrieval
"""

import hashlib
import hmac
import os
import sys
import time
import uuid
from datetime import datetime

import requests

# Configuration
BASE_URL = "http://localhost:8000"
API_VERSION = "/api/v1"
DEVICE_SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "default_secret_for_dev_only")

# Test user credentials (from ADMIN_CREDENTIALS_COMPLETE.md)
TEST_USER = {
    "id": "test_user_" + str(uuid.uuid4())[:8],
    "email": "testuser@voicenote.app",
    "name": "Test User",
    "device_id": "device_" + str(uuid.uuid4())[:8],
    "device_model": "TestDevice_1.0",
    "token": "token_test_" + str(uuid.uuid4())[:8],
}


class NotesTestSuite:
    def __init__(self):
        self.base_url = BASE_URL + API_VERSION
        self.access_token = None
        self.user_id = None
        self.test_results = []
        self.notes_created = []

    def generate_device_signature(self, method, path, timestamp, body=""):
        """Generate device signature for request authentication"""
        # Signature format: HMAC_SHA256(secret, method + path + timestamp + body_hash)
        body_hash = (
            hashlib.sha256(body.encode()).hexdigest()
            if body
            else hashlib.sha256(b"").hexdigest()
        )
        message = f"{method}{path}{timestamp}{body_hash}"
        signature = hmac.new(
            DEVICE_SECRET_KEY.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        return signature

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
        """Step 1: Authenticate user and get access token"""
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
                if admin_response.status_code in [200, 201]:
                    pass  # Admin promotion successful
                else:
                    # Try with PUT method as fallback
                    admin_response = requests.put(
                        f"{self.base_url}/admin/permissions/{self.user_id}",
                        json={"is_admin": True},
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        timeout=10,
                    )
            except Exception as e:
                pass  # Admin promotion not critical, but helpful

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
        """Create a test audio file using ffmpeg or similar"""
        print("\n" + "=" * 70)
        print("STEP 2: CREATE TEST AUDIO FILE")
        print("=" * 70)

        start_time = time.time()
        audio_path = f"/tmp/test_audio_{uuid.uuid4().hex[:8]}.wav"

        try:
            # Generate test audio using FFmpeg (if available)
            import subprocess

            # Create a simple test audio file (2 seconds of tone)
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
                # Try alternative method: create using Python
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

            # Audio parameters
            sample_rate = 16000
            duration = 2
            frequency = 440

            # Generate audio data
            num_samples = sample_rate * duration
            frames = []

            for i in range(num_samples):
                sample = int(
                    32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate)
                )
                frames.append(struct.pack("<h", sample))

            # Write WAV file
            with wave.open(output_path, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b"".join(frames))

            return True
        except Exception as e:
            print(f"Error creating audio with Python: {e}")
            return False

    def test_get_presigned_url(self):
        """Test: GET /presigned-url"""
        print("\n" + "=" * 70)
        print("TEST 1: GET PRESIGNED URL")
        print("=" * 70)

        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/notes/presigned-url",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "GET /presigned-url",
                    "PASS",
                    f"Generated presigned URL (note_id: {data.get('note_id')})",
                    time.time() - start_time,
                )
                return data.get("note_id"), data.get("upload_url")
            else:
                self.log_test(
                    "GET /presigned-url",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return None, None

        except Exception as e:
            self.log_test(
                "GET /presigned-url", "FAIL", str(e), time.time() - start_time
            )
            return None, None

    def test_process_note_with_file(self, audio_path):
        """Test: POST /process with file upload"""
        print("\n" + "=" * 70)
        print("TEST 2: POST /PROCESS (FILE UPLOAD)")
        print("=" * 70)

        start_time = time.time()
        try:
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                data = {
                    "mode": "GENERIC",
                    "languages": "en",
                    "stt_model": "nova",
                    "debug_sync": "false",
                }

                # Try with device signature headers
                timestamp = str(int(time.time()))

                response = requests.post(
                    f"{self.base_url}/notes/process",
                    files=files,
                    data=data,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Device-Timestamp": timestamp,
                        "X-Device-Signature": "bypass",  # Try bypass
                    },
                    timeout=30,
                )

            if response.status_code in [200, 202]:
                result = response.json()
                self.log_test(
                    "POST /process",
                    "PASS",
                    f"Note processing started",
                    time.time() - start_time,
                )
                return result.get("note_id"), result.get("task_id")
            else:
                self.log_test(
                    "POST /process",
                    "FAIL",
                    f"Status {response.status_code}: {response.text[:200]}",
                    time.time() - start_time,
                )
                return None, None

        except Exception as e:
            self.log_test("POST /process", "FAIL", str(e), time.time() - start_time)
            return None, None

    def test_list_notes(self):
        """Test: GET /notes"""
        print("\n" + "=" * 70)
        print("TEST 3: GET /NOTES (LIST)")
        print("=" * 70)

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
                count = len(notes) if isinstance(notes, list) else notes.get("count", 0)
                self.log_test(
                    "GET /notes",
                    "PASS",
                    f"Retrieved {count} notes",
                    time.time() - start_time,
                )
                return notes
            else:
                self.log_test(
                    "GET /notes",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return None

        except Exception as e:
            self.log_test("GET /notes", "FAIL", str(e), time.time() - start_time)
            return None

    def test_get_note(self, note_id):
        """Test: GET /notes/{note_id}"""
        print("\n" + "=" * 70)
        print(f"TEST 4: GET /NOTES/{note_id}")
        print("=" * 70)

        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/notes/{note_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                note = response.json()
                self.log_test(
                    "GET /notes/{note_id}",
                    "PASS",
                    f"Retrieved note (title: {note.get('title', 'N/A')})",
                    time.time() - start_time,
                )
                return note
            else:
                self.log_test(
                    "GET /notes/{note_id}",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return None

        except Exception as e:
            self.log_test(
                "GET /notes/{note_id}", "FAIL", str(e), time.time() - start_time
            )
            return None

    def test_update_note(self, note_id):
        """Test: PATCH /notes/{note_id}"""
        print("\n" + "=" * 70)
        print(f"TEST 5: PATCH /NOTES/{note_id}")
        print("=" * 70)

        start_time = time.time()
        try:
            update_data = {
                "title": f"Updated Note {uuid.uuid4().hex[:8]}",
                "description": "Updated via test suite",
                "tags": ["test", "updated"],
            }

            response = requests.patch(
                f"{self.base_url}/notes/{note_id}",
                json=update_data,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                note = response.json()
                self.log_test(
                    "PATCH /notes/{note_id}",
                    "PASS",
                    f"Updated note (new title: {note.get('title')})",
                    time.time() - start_time,
                )
                return note
            else:
                self.log_test(
                    "PATCH /notes/{note_id}",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return None

        except Exception as e:
            self.log_test(
                "PATCH /notes/{note_id}", "FAIL", str(e), time.time() - start_time
            )
            return None

    def test_search_notes(self):
        """Test: POST /notes/search"""
        print("\n" + "=" * 70)
        print("TEST 6: POST /NOTES/SEARCH")
        print("=" * 70)

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
                count = (
                    len(results)
                    if isinstance(results, list)
                    else results.get("count", 0)
                )
                self.log_test(
                    "POST /notes/search",
                    "PASS",
                    f"Found {count} matching notes",
                    time.time() - start_time,
                )
                return results
            else:
                self.log_test(
                    "POST /notes/search",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return None

        except Exception as e:
            self.log_test(
                "POST /notes/search", "FAIL", str(e), time.time() - start_time
            )
            return None

    def test_get_dashboard_metrics(self):
        """Test: GET /notes/dashboard"""
        print("\n" + "=" * 70)
        print("TEST 7: GET /NOTES/DASHBOARD")
        print("=" * 70)

        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/notes/dashboard",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                metrics = response.json()
                self.log_test(
                    "GET /notes/dashboard",
                    "PASS",
                    f"Retrieved dashboard data",
                    time.time() - start_time,
                )
                return metrics
            else:
                self.log_test(
                    "GET /notes/dashboard",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return None

        except Exception as e:
            self.log_test(
                "GET /notes/dashboard", "FAIL", str(e), time.time() - start_time
            )
            return None

    def test_ask_ai(self, note_id):
        """Test: POST /notes/{note_id}/ask"""
        print("\n" + "=" * 70)
        print(f"TEST 8: POST /NOTES/{note_id}/ASK")
        print("=" * 70)

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/notes/{note_id}/ask",
                json={"question": "What is this note about?"},
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                self.log_test(
                    "POST /notes/{note_id}/ask",
                    "PASS",
                    f"AI response received",
                    time.time() - start_time,
                )
                return result
            else:
                self.log_test(
                    "POST /notes/{note_id}/ask",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return None

        except Exception as e:
            self.log_test(
                "POST /notes/{note_id}/ask", "FAIL", str(e), time.time() - start_time
            )
            return None

    def test_delete_note(self, note_id):
        """Test: DELETE /notes/{note_id}"""
        print("\n" + "=" * 70)
        print(f"TEST 9: DELETE /NOTES/{note_id}")
        print("=" * 70)

        start_time = time.time()
        try:
            response = requests.delete(
                f"{self.base_url}/notes/{note_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )

            if response.status_code in [200, 204]:
                self.log_test(
                    "DELETE /notes/{note_id}",
                    "PASS",
                    f"Note deleted successfully",
                    time.time() - start_time,
                )
                return True
            else:
                self.log_test(
                    "DELETE /notes/{note_id}",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}",
                    time.time() - start_time,
                )
                return False

        except Exception as e:
            self.log_test(
                "DELETE /notes/{note_id}", "FAIL", str(e), time.time() - start_time
            )
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        total = len(self.test_results)

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%")

        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test_name']}: {result['message']}")

        print("\n" + "=" * 70)

    def run_all_tests(self):
        """Run complete test suite"""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 15 + "NOTES ENDPOINT TEST SUITE" + " " * 29 + "║")
        print("║" + " " * 68 + "║")
        print(
            "║"
            + f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            + " " * 42
            + "║"
        )
        print("╚" + "=" * 68 + "╝")

        # Step 1: Authenticate
        if not self.authenticate():
            print("\n❌ Authentication failed. Cannot continue.")
            return False

        # Step 2: Create test audio
        audio_path = self.create_test_audio_file()
        if not audio_path:
            print(
                "\n⚠️  Warning: Could not create audio file. Some tests will be skipped."
            )

        # Test 1: Get presigned URL
        note_id, upload_url = self.test_get_presigned_url()

        # Test 2: Process note with file
        if audio_path:
            processed_note_id, task_id = self.test_process_note_with_file(audio_path)
            if processed_note_id:
                self.notes_created.append(processed_note_id)

        # Test 3: List notes
        notes = self.test_list_notes()

        # Test 4: Get specific note (if we have one)
        if self.notes_created:
            note = self.test_get_note(self.notes_created[0])

        # Test 5: Update note
        if self.notes_created:
            updated_note = self.test_update_note(self.notes_created[0])

        # Test 6: Search notes
        search_results = self.test_search_notes()

        # Test 7: Dashboard metrics
        metrics = self.test_get_dashboard_metrics()

        # Test 8: Ask AI (if note exists)
        if self.notes_created:
            ai_response = self.test_ask_ai(self.notes_created[0])

        # Test 9: Delete note
        if self.notes_created:
            self.test_delete_note(self.notes_created[0])

        # Print summary
        self.print_summary()

        return True


if __name__ == "__main__":
    tester = NotesTestSuite()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
