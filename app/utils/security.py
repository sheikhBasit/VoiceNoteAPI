import os
import hmac
import hashlib
import time
from fastapi import Request, HTTPException, status
from functools import wraps
from sqlalchemy.orm import Session
from app.utils.json_logger import JLogger

# Secret key for device signature verification
DEVICE_SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "default_secret_for_dev_only")

async def verify_device_signature(request: Request):
    """
    Middleware/Dependency to verify X-Device-Signature.
    Signature = HMAC_SHA256(secret, method + path + query + timestamp + body_hash)
    Match Android HmacInterceptor logic.
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
    # Matching Android HmacInterceptor: method + path + query + timestamp + body_hash
    query_string = request.url.query
    
    # Calculate Body Hash
    body_bytes = await request.body()
    
    # Logic matching Android HmacInterceptor:
    # val bodyHash = originalRequest.body?.let { ... SHA256(...) } ?: ""
    # GET/HEAD/DELETE usually have null body in OkHttp -> ""
    # POST/PUT/PATCH usually have non-null body -> SHA256(bytes)
    
    if request.method in ["GET", "HEAD", "DELETE"]:
        body_hash = ""
    else:
        # For POST/PUT, even if body is empty, OkHttp usually creates a RequestBody.
        # SHA256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        if body_bytes:
             body_hash = hashlib.sha256(body_bytes).hexdigest()
        else:
             # Empty POST body
             body_hash = hashlib.sha256(b"").hexdigest()

    message = f"{request.method}{request.url.path}{query_string}{timestamp}{body_hash}".encode()
    
    expected_signature = hmac.new(
        DEVICE_SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        # DEBUG: Check if using default key
        if DEVICE_SECRET_KEY == "default_secret_for_dev_only":
            JLogger.warning("Security Warning: Using DEFAULT device secret key. Client may be using a different key.")

        JLogger.error("Invalid device signature detected", 
                      path=request.url.path, 
                      method=request.method,
                      timestamp=timestamp,
                      ip=request.client.host if request.client else "unknown",
                      debug_message=message.decode('utf-8', errors='ignore'),
                      body_hash_debug=body_hash,
                      expected_sig=expected_signature,
                      received_sig=signature)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid device signature"
        )
    
    return True

    return True

def verify_note_ownership(db: Session, user_id: str, note_id: str):
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


def verify_task_ownership(db: Session, user_id: str, task_id: str):
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
    
    # 2. Ownership Check
    # NEW: Check task.user_id first (manual tasks may not have a parent note)
    if task.user_id:
        if task.user_id != user_id:
            JLogger.warning("Task ownership violation attempt", 
                            user_id=user_id, 
                            task_id=task_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: You do not have authority over this task"
            )
    else:
        # Fallback for old tasks that might not have user_id populated yet
        note = db.query(models.Note).filter(models.Note.id == task.note_id).first()
        if not note or note.user_id != user_id:
            JLogger.warning("Task ownership violation attempt (legacy check)", 
                            user_id=user_id, 
                            task_id=task_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: You do not have authority over this task"
            )
        
    return task

