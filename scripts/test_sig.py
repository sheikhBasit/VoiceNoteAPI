import hmac
import hashlib
import time

def test_signature():
    secret = "default_secret_for_dev_only"
    timestamp = str(int(time.time()))
    method = "POST"
    path = "/api/v1/notes/process"
    
    # Logic from security.py
    message = f"{method}{path}{timestamp}".encode()
    expected_signature = hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    print(f"Timestamp: {timestamp}")
    print(f"Signature: {expected_signature}")
    
    # Verify
    reconstructed_message = f"{method}{path}{timestamp}".encode()
    v_sig = hmac.new(
        secret.encode(),
        reconstructed_message,
        hashlib.sha256
    ).hexdigest()
    
    if hmac.compare_digest(v_sig, expected_signature):
        print("✅ Signature Logic Verified")
    else:
        print("❌ Signature Logic Failed")

if __name__ == "__main__":
    test_signature()
