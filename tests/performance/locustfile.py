import uuid

from locust import HttpUser, between, task


class VoiceNoteLoadTester(HttpUser):
    wait_time = between(1, 5)  # Simulate human delay

    def on_start(self):
        """Setup a fake biometric session for the virtual user."""
        self.user_id = f"load_user_{uuid.uuid4()}"
        self.headers = {"X-Device-Token": "test_secret_token"}
        # Register user
        self.client.post(
            "/api/v1/users/register",
            json={
                "id": self.user_id,
                "email": f"{self.user_id}@loadtest.com",
                "name": "Load User",
                "password": "loadtestpassword123"
            },
        )

    @task(3)
    def view_notes(self):
        """Simulate browsing notes."""
        self.client.get(f"/api/v1/notes/?user_id={self.user_id}", headers=self.headers)

    @task(1)
    def semantic_search(self):
        """Simulate AI vector search (High CPU usage)."""
        self.client.post(
            "/api/v1/ai/search",
            params={"query": "budget plans", "user_id": self.user_id},
            headers=self.headers,
        )

    @task(1)
    def upload_audio_stress(self):
        """Simulate audio upload (Network & Disk I/O stress)."""
        file_content = b"a" * 1024 * 1024  # 1MB fake file
        self.client.post(
            "/api/v1/notes/process",
            headers=self.headers,
            data={"user_id": self.user_id},
            files={"file": ("stress_test.mp3", file_content)},
        )
