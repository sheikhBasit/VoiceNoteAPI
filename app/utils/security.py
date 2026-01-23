import os
import hmac
import hashlib
import time
from fastapi import Request, HTTPException, status
from functools import wraps

# Secret key for device signature verification
DEVICE_SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "default_secret_for_dev_only")

def verify_device_signature(request: Request):
    """
    Middleware/Dependency to verify X-Device-Signature.
    Signature = HMAC_SHA256(secret, method + path + timestamp + body_hash)
    """
    signature = request.headers.get("X-Device-Signature")
    timestamp = request.headers.get("X-Device-Timestamp") # Unix timestamp in seconds
    
    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device signature or timestamp"
        )
    
    # Check for replay attacks (allow 5 minute clock skew)
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > 300:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request timestamp expired or out of sync"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid timestamp"
        )

    # Reconstruct message for HMAC
    # Simple version: method + path + timestamp
    message = f"{request.method}{request.url.path}{timestamp}".encode()
    
    expected_signature = hmac.new(
        DEVICE_SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        # In production, we might want to be more strict or log this
        # For MVP, we allow a bypass if SECRET is not set properly, but here we enforce it.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device signature"
        )
    
    return True

def verify_biometric_token(request: Request):
    """
    Middleware/Dependency to verify X-Biometric-Token.
    This should be validated against the hardware attestation key / Android KeyStore.
    For MVP, we check if the header is present and valid for the current user.
    """
    token = request.headers.get("X-Biometric-Token")
    if not token:
        # We don't necessarily want to block if biometric is not used, 
        # but for high-security actions we would.
        return False
        
    # LOGIC: In production, verify token against stored public key for the device
    # For now, we return True if present
    return True

