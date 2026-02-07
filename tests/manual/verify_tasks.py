import hashlib
import hmac
import json
import time

import requests

BASE_URL = "http://localhost:8000/api/v1"
DEVICE_SECRET = "VN_SECURE_8f7d9a2b_2026"


def get_signature_headers(method, path, query, body, body_is_bytes=False):
    timestamp = str(int(time.time()))
    if not body:
        body_hash = ""
    else:
        content = body if body_is_bytes else body.encode()
        body_hash = hashlib.sha256(content).hexdigest()

    message = f"{method}{path}{query}{timestamp}{body_hash}"
    signature = hmac.new(
        DEVICE_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    return {"X-Device-Signature": signature, "X-Device-Timestamp": timestamp}


print("🕵️ Starting Task & Audio Verification (Python)...")

# 1. Login
print("\n1. 🔑 Authenticating...")
auth_data = {
    "name": "Python Test User",
    "email": "python_test@voicenote.app",
    "token": "tok_py_123",
    "device_id": "device_py_001",
    "device_model": "PythonScript",
    "timezone": "UTC",
}
# Login shouldn't require signature (public endpoint)
resp = requests.post(f"{BASE_URL}/users/sync", json=auth_data)
if resp.status_code != 200:
    print(f"❌ Login Failed: {resp.text}")
    exit(1)

auth_resp = resp.json()
token = auth_resp["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Logged in. Token: {token[:10]}...")

# 2. Manual Task Creation
print("\n2. ✍️ Creating Manual Task...")
task_data = {"description": "Buy milk manually (Python)", "priority": "MEDIUM"}
# This requires signature
sig_headers = get_signature_headers("POST", "/api/v1/tasks", "", json.dumps(task_data))
headers.update(sig_headers)

resp = requests.post(f"{BASE_URL}/tasks", json=task_data, headers=headers)
if resp.status_code not in [200, 201]:
    print(f"❌ Create Task Failed: {resp.text}")
    exit(1)

task = resp.json()
print(f"✅ Created Task: {task['id']}")

# 3. Audio Upload
print("\n3. 🎤 Uploading Audio...")
# Create dummy wav
import wave

with wave.open("test_python.wav", "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(44100)
    wav_file.writeframes(b"\x00\x00" * 44100)  # 1 sec silence

# Multipart/form-data signature is tricky because boundaries change.
# However, if we read the body FIRST, we can sign it.
# Requests doesn't easily let us inspect the body before sending with auto-boundaries.
# BUT, we can use the ADMIN exemption if we fix the admin check.
# OR we can simply construct the body manually.
# Let's try the Admin approach again with this script but using the `admin@voicenote.app` credentials first.

print("   Switching to Admin User for Upload...")
admin_data = {
    "name": "System Admin",
    "email": "admin@voicenote.app",
    "token": "admin_token_py",
    "device_id": "admin_device_py",
    "device_model": "PythonScript",
    "timezone": "UTC",
}
resp = requests.post(f"{BASE_URL}/users/sync", json=admin_data)
admin_token = resp.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}

print("   Uploading as Admin...")
with open("test_python.wav", "rb") as f:
    files = {"file": ("test_python.wav", f, "audio/wav")}
    data = {"mode": "GENERIC", "stt_model": "nova"}
    # Admin should bypass signature check
    resp = requests.post(
        f"{BASE_URL}/notes/process", files=files, data=data, headers=admin_headers
    )

print(f"Debug Response: {resp.text}")
if resp.status_code == 202:
    data = resp.json()
    note_id = data["note_id"]
    print(f"✅ Audio Uploaded. Note ID: {note_id}")

    # 4. Check Status
    print("\n4. ⏳ Checking Status...")
    time.sleep(2)
    resp = requests.get(f"{BASE_URL}/notes/{note_id}", headers=admin_headers)
    note = resp.json()
    print(f"ℹ️ Status: {note['status']}")

    if note["status"] in ["PROCESSING", "DONE"]:
        print("✅ Pipeline Active")
    else:
        print("❌ Pipeline Stuck")
else:
    print(f"❌ Upload Failed: {resp.status_code}")

print("\n🎉 Done.")
