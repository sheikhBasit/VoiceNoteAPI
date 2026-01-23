"""
V-Model Load Test - Concurrent Cascade Deletion

Simulates users performing cascade deletions simultaneously to check for deadlocks and performance.
V-Model Level: System/Load Testing (Top level)
"""

from locust import HttpUser, task, between, events
import uuid
import random

class DeletionLoadUser(HttpUser):
    wait_time = between(1, 2)
    
    def on_start(self):
        """Setup user and data for deletion."""
        self.user_id = f"load_user_{uuid.uuid4()}"
        # Register user
        self.client.post("/api/v1/users/sync", json={
            "id": self.user_id,
            "name": "Load Test",
            "email": f"load_{uuid.uuid4()}@ex.com",
            "token": "test_token",
            "device_id": "load_device",
            "device_model": "Locust",
            "primary_role": "GENERIC"
        })
        
        # Create some notes and tasks
        self.note_ids = []
        for _ in range(3):
            note_id = str(uuid.uuid4())
            self.client.post("/api/v1/notes/process", data={
                "user_id": self.user_id,
                "instruction": "Test Load"
            }, files={
                "file": ("test.mp3", b"fake-audio-content", "audio/mpeg")
            }, headers={"X-Signature": "dummy_sig"}) # Mocks usually bypass sig or we provide dummy
            self.note_ids.append(note_id)

    @task(3)
    def delete_single_note(self):
        """Simulate frequent note deletions."""
        if self.note_ids:
            note_id = self.note_ids.pop()
            with self.client.delete(
                f"/api/v1/notes/{note_id}?user_id={self.user_id}",
                name="/api/v1/notes/[id]",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to delete note: {response.text}")

    @task(1)
    def delete_account(self):
        """Simulate final account deletion (heavy cascade)."""
        with self.client.delete(
            f"/api/v1/users/me?user_id={self.user_id}&hard=false",
            name="/api/v1/users/me",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                self.interrupt() # Stop this user since account is deleted
            else:
                response.failure(f"Failed to delete account: {response.text}")

@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--my-extra-arg", help="It's working")
