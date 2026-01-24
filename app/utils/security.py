import os
import hmac
import hashlib
import time
from fastapi import Request, HTTPException, status
from functools import wraps
from app.utils.json_logger import JLogger

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
        JLogger.warning("Missing device signature or timestamp", 
                        path=request.url.path, 
                        method=request.method,
                        ip=request.client.host if request.client else "unknown")
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
    # Hardened version: method + path + query_string + timestamp
    query_string = request.url.query
    message = f"{request.method}{request.url.path}{query_string}{timestamp}".encode()
    
    expected_signature = hmac.new(
        DEVICE_SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        JLogger.error("Invalid device signature detected", 
                      path=request.url.path, 
                      method=request.method,
                      timestamp=timestamp,
                      ip=request.client.host if request.client else "unknown")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device signature"
        )
    
    return True

    return True

def verify_note_ownership(db: "Session", user_id: str, note_id: str):
    """
    Dependency helper to verify that a note exists and belongs to the user.
    """
    from app.db import models
    
    # 1. Existence Check
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice note with ID '{note_id}' not found"
        )
    
    # 2. Ownership Check
    if note.user_id != user_id:
        JLogger.warning("Ownership violation attempt", 
                        user_id=user_id, 
                        note_id=note_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You do not own this voice note"
        )
        
    return note


def verify_task_ownership(db: "Session", user_id: str, task_id: str):
    """
    Dependency helper to verify that a task exists and its parent note belongs to the user.
    """
    from app.db import models
    
    # 1. Existence Check
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found"
        )
    
    # 2. Parent Note Check
    note = db.query(models.Note).filter(models.Note.id == task.note_id).first()
    if not note or note.user_id != user_id:
        JLogger.warning("Task ownership violation attempt", 
                        user_id=user_id, 
                        task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You do not have authority over this task"
        )
        
    return task

