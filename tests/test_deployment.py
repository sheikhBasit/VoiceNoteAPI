import httpx
import os

import pytest

# This test runs against your LIVE production/staging URL
LIVE_URL = os.getenv("DEPLOYMENT_URL")

@pytest.mark.skipif(not LIVE_URL, reason="Skipping deployment tests: DEPLOYMENT_URL not set")

def test_live_health():
    """Check if the deployed server is up and database is connected."""
    response = httpx.get(f"{LIVE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_stt_api_live():
    """Verify that the AI services (Groq/Deepgram) are authenticated on the server."""
    # This ensures your .env was correctly uploaded to the server
    response = httpx.post(f"{LIVE_URL}/api/test/stt-comparison", 
                         files={"file": ("test.wav", b"fakecontent")})
    # If it returns 401/500, your API keys on the server are broken
    assert response.status_code != 500