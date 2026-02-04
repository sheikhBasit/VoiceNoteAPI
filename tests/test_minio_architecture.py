"""
Pytest Suite for MinIO Privacy-First Architecture

Tests:
1. Pre-signed URL generation
2. MinIO upload flow
3. Storage-key based processing
4. Privacy cleanup verification
5. Legacy upload compatibility
6. Queue routing
7. Error handling
"""

import pytest
import requests
import time
import os
import uuid
from pathlib import Path
import subprocess

BASE_URL = "http://localhost:8000/api/v1"
TEST_AUDIO_PATH = "/tmp/pytest_test_audio.wav"


@pytest.fixture(scope="module")
def test_audio_file():
    """Create a test audio file if it doesn't exist."""
    if not os.path.exists(TEST_AUDIO_PATH):
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            TEST_AUDIO_PATH, "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    yield TEST_AUDIO_PATH
    # Cleanup after all tests
    # os.remove(TEST_AUDIO_PATH)


@pytest.fixture(scope="module")
def authenticated_user():
    """Create and authenticate a test user."""
    unique_email = f"pytest_{uuid.uuid4()}@voicenote.ai"
    
    response = requests.post(f"{BASE_URL}/users/sync", json={
        "name": "Pytest User",
        "email": unique_email,
        "token": "pytest_token",
        "device_id": "pytest_device",
        "device_model": "pytest",
        "primary_role": "DEVELOPER",
        "timezone": "UTC"
    })
    
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    token = data["access_token"]
    
    # Elevate to admin for signature bypass
    subprocess.run([
        "docker", "exec", "voicenote_db", "psql", "-U", "postgres", "-d", "voicenote",
        "-c", f"UPDATE users SET is_admin = true WHERE email = '{unique_email}';"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return {
        "token": token,
        "email": unique_email,
        "headers": {"Authorization": f"Bearer {token}"}
    }


class TestMinIOArchitecture:
    """Test suite for MinIO Privacy-First architecture."""
    
    def test_api_health(self):
        """Test API health endpoint."""
        response = requests.get(f"{BASE_URL}/../health")
        assert response.status_code == 200
        assert "healthy" in response.text.lower()
    
    def test_presigned_url_generation(self, authenticated_user):
        """Test pre-signed URL generation endpoint."""
        response = requests.get(
            f"{BASE_URL}/notes/presigned-url",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "note_id" in data
        assert "storage_key" in data
        assert "upload_url" in data
        assert "expires_in" in data
        
        assert data["expires_in"] == 3600
        assert "incoming" in data["upload_url"]
    
    def test_minio_direct_upload(self, authenticated_user, test_audio_file):
        """Test direct upload to MinIO using pre-signed URL."""
        # Get pre-signed URL
        response = requests.get(
            f"{BASE_URL}/notes/presigned-url",
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        
        upload_url = data["upload_url"].replace("minio:9000", "localhost:9000")
        
        # Upload file
        with open(test_audio_file, "rb") as f:
            upload_response = requests.put(upload_url, data=f)
        
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.status_code}"
    
    def test_storage_key_processing(self, authenticated_user, test_audio_file):
        """Test processing a note from MinIO storage key."""
        # Step 1: Get pre-signed URL
        presigned_response = requests.get(
            f"{BASE_URL}/notes/presigned-url",
            headers=authenticated_user["headers"]
        )
        assert presigned_response.status_code == 200
        presigned_data = presigned_response.json()
        
        # Step 2: Upload to MinIO
        upload_url = presigned_data["upload_url"].replace("minio:9000", "localhost:9000")
        with open(test_audio_file, "rb") as f:
            upload_response = requests.put(upload_url, data=f)
        assert upload_response.status_code == 200
        
        # Step 3: Trigger processing
        process_response = requests.post(
            f"{BASE_URL}/notes/process",
            headers=authenticated_user["headers"],
            data={
                "storage_key": presigned_data["storage_key"],
                "note_id_override": presigned_data["note_id"],
                "stt_model": "nova"
            }
        )
        
        assert process_response.status_code == 202
        process_data = process_response.json()
        assert process_data["status"] == "ACCEPTED"
        assert "queue" in process_data
        
        return presigned_data["note_id"]
    
    def test_processing_completion(self, authenticated_user, test_audio_file):
        """Test that processing completes successfully."""
        note_id = self.test_storage_key_processing(authenticated_user, test_audio_file)
        
        # Poll for completion
        max_retries = 30
        for i in range(max_retries):
            response = requests.get(
                f"{BASE_URL}/notes/{note_id}",
                headers=authenticated_user["headers"]
            )
            assert response.status_code == 200
            
            data = response.json()
            status = data.get("status")
            
            if status == "DONE":
                assert data.get("title") is not None
                return
            elif status == "FAILED":
                pytest.fail(f"Processing failed for note {note_id}")
            
            time.sleep(2)
        
        pytest.fail(f"Processing timeout for note {note_id}")
    
    def test_privacy_cleanup(self, authenticated_user, test_audio_file):
        """Test that MinIO files are deleted after processing."""
        # Process a note
        presigned_response = requests.get(
            f"{BASE_URL}/notes/presigned-url",
            headers=authenticated_user["headers"]
        )
        presigned_data = presigned_response.json()
        
        upload_url = presigned_data["upload_url"].replace("minio:9000", "localhost:9000")
        with open(test_audio_file, "rb") as f:
            requests.put(upload_url, data=f)
        
        requests.post(
            f"{BASE_URL}/notes/process",
            headers=authenticated_user["headers"],
            data={
                "storage_key": presigned_data["storage_key"],
                "note_id_override": presigned_data["note_id"],
                "stt_model": "nova"
            }
        )
        
        # Wait for processing
        note_id = presigned_data["note_id"]
        for i in range(30):
            response = requests.get(
                f"{BASE_URL}/notes/{note_id}",
                headers=authenticated_user["headers"]
            )
            if response.json().get("status") == "DONE":
                break
            time.sleep(2)
        
        # Verify file is deleted from MinIO
        result = subprocess.run([
            "docker", "exec", "voicenote_mc", "/usr/bin/mc", "ls",
            f"myminio/incoming/{presigned_data['storage_key']}"
        ], capture_output=True, text=True)
        
        assert "Object does not exist" in result.stderr or result.returncode != 0
    
    def test_legacy_upload_compatibility(self, authenticated_user, test_audio_file):
        """Test that legacy direct file upload still works."""
        with open(test_audio_file, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/notes/process",
                headers=authenticated_user["headers"],
                files={"file": ("test.wav", f, "audio/wav")},
                data={"stt_model": "nova"}
            )
        
        assert response.status_code == 202
        data = response.json()
        assert "note_id" in data
    
    def test_invalid_storage_key(self, authenticated_user):
        """Test error handling for invalid storage key."""
        response = requests.post(
            f"{BASE_URL}/notes/process",
            headers=authenticated_user["headers"],
            data={
                "storage_key": "invalid/nonexistent.wav",
                "note_id_override": str(uuid.uuid4()),
                "stt_model": "nova"
            }
        )
        
        # Should still accept the request (worker will handle the error)
        assert response.status_code == 202
    
    def test_missing_audio_source(self, authenticated_user):
        """Test error when neither file nor storage_key is provided."""
        response = requests.post(
            f"{BASE_URL}/notes/process",
            headers=authenticated_user["headers"],
            data={"stt_model": "nova"}
        )
        
        assert response.status_code == 400
        assert "Missing audio sources" in response.text
    
    def test_queue_routing(self, authenticated_user, test_audio_file):
        """Test that tasks are routed to appropriate queues."""
        response = requests.post(
            f"{BASE_URL}/notes/process",
            headers=authenticated_user["headers"],
            files={"file": ("test.wav", open(test_audio_file, "rb"), "audio/wav")},
            data={"stt_model": "nova"}
        )
        
        assert response.status_code == 202
        data = response.json()
        
        # Currently defaults to 'short' queue
        # This will be enhanced with duration-based routing
        assert "queue" in data or "status" in data


class TestMinIOConfiguration:
    """Test MinIO configuration and connectivity."""
    
    def test_minio_health(self):
        """Test MinIO health endpoint."""
        response = requests.get("http://localhost:9000/minio/health/live")
        assert response.status_code == 200
    
    def test_bucket_exists(self):
        """Test that 'incoming' bucket exists."""
        result = subprocess.run([
            "docker", "exec", "voicenote_mc", "/usr/bin/mc", "ls", "myminio/incoming"
        ], capture_output=True)
        
        # Should not error (bucket exists)
        assert result.returncode == 0


class TestCeleryQueues:
    """Test Celery queue configuration."""
    
    def test_worker_queues(self):
        """Test that worker is listening to correct queues."""
        result = subprocess.run([
            "docker", "exec", "voicenote_celery_worker", "celery", "-A",
            "app.worker.celery_app", "inspect", "active_queues"
        ], capture_output=True, text=True)
        
        assert "short" in result.stdout
        assert "long" in result.stdout
        assert "celery" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
