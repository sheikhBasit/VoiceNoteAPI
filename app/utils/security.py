import hashlib
import hmac
import os
import time
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.json_logger import JLogger


def is_dev_bypass(token: str) -> bool:
    """Centralized check for development bypass tokens."""
    if token and token.startswith("dev_"):
        if os.getenv("ENVIRONMENT") == "production":
            JLogger.warning(
                "DEVELOPMENT BYPASS USED IN PRODUCTION ENVIRONMENT", token=token
            )
        return True
    return False

# Secret key for device signature verification
DEVICE_SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "default_secret_for_dev_only")


async def verify_device_signature(request: Request, db: Session = Depends(get_db)):
    """
    Middleware/Dependency to verify X-Device-Signature.
    Signature = HMAC_SHA256(secret, method + path + query + timestamp + body_hash)

    Exemption: Admins (identified by Bearer token) bypass this check.
    Exemption: Testing environment.
    """
    # 0. Check for Testing Environment
    if os.getenv("ENVIRONMENT") == "testing" and not request.headers.get("X-Force-Signature-Check"):
        return True

    # 1. Check for Admin or Dev Bypass (Token-based)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

        if is_dev_bypass(token):
            return True

        try:
            import jwt
            from app.services.auth_service import ALGORITHM, SECRET_KEY
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                from app.db import models
                user = db.query(models.User).filter(models.User.id == user_id).first()
                if user and user.is_admin:
                    return True
        except Exception:
            pass  # Invalid token for bypass check, proceed to signature check

    signature = request.headers.get("X-Device-Signature")
    timestamp = request.headers.get("X-Device-Timestamp")  # Unix timestamp in seconds

    if not signature or not timestamp:
        JLogger.warning(
            "Missing device signature or timestamp",
            path=request.url.path,
            method=request.method,
            ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device signature or timestamp",
        )

    # Check for replay attacks (allow 5 minute clock skew)
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > 300:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request timestamp expired or out of sync",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid timestamp"
        )

    # Reconstruct message for HMAC
    # Matching Android HmacInterceptor: method + path + query + timestamp + body_hash
    query_string = request.url.query

    # Calculate Body Hash
    # Using RequestBodyCacheMiddleware's cached body if available.
    body_hash = ""
    if request.method not in ["GET", "HEAD", "DELETE"]:
        cached_body = request.scope.get("cached_body", b"")
        body_hash = hashlib.sha256(cached_body).hexdigest()

    message = f"{request.method}{request.url.path}{query_string}{timestamp}{body_hash}".encode()

    expected_signature = hmac.new(
        DEVICE_SECRET_KEY.encode(), message, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        # ... (logging)
        raise HTTPException(status_code=401, detail="Invalid device signature")

    return True

    return True


def is_admin(user: Session) -> bool:
    """Utility to check if the current user has an admin role."""
    return getattr(user, "is_admin", False)


def verify_note_ownership(db: Session, user: Any, note_id: str):
    """
    Dependency helper to verify that a note exists and belongs to the user or admin.
    """
    from app.db import models

    user_id = user.id
    is_user_admin = is_admin(user)

    # 1. Existence Check
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice note with ID '{note_id}' not found",
        )

    # 2. Ownership & Participation Check (B2B Shared Folders)
    if is_user_admin:
        return note

    # Check if user is a participant in the folder containing this note
    participant = False
    if note.folder_id:
        from app.db.models import folder_participants
        participant = db.query(folder_participants).filter(
            folder_participants.c.folder_id == note.folder_id,
            folder_participants.c.user_id == user_id
        ).first() is not None

    if note.user_id == user_id or participant:
        return note

    # Check for Team Membership
    if note.team_id:
        if any(t.id == note.team_id for t in user.teams) or \
           any(t.id == note.team_id for t in user.owned_teams):
            return note

    JLogger.warning("Ownership/Participation violation attempt", user_id=user_id, note_id=note_id)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied: You do not own this voice note and it is not in a shared folder you participate in.",
    )

    return note


def verify_task_ownership(db: Session, user: Any, task_id: str):
    """
    Dependency helper to verify that a task exists and its parent note belongs to the user or admin.
    """
    from app.db import models

    user_id = user.id
    is_user_admin = is_admin(user)

    # 1. Existence Check
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found",
        )

    # 2. Ownership & Participation Check
    if is_user_admin:
        return task

    # Check direct ownership
    if task.user_id == user_id:
        return task

    # Check parent note's folder for shared participation
    note = db.query(models.Note).filter(models.Note.id == task.note_id).first()
    if note:
        participant = False
        if note.folder_id:
            from app.db.models import folder_participants
            participant = db.query(folder_participants).filter(
                folder_participants.c.folder_id == note.folder_id,
                folder_participants.c.user_id == user_id
            ).first() is not None

        if note.user_id == user_id or participant:
            return task

    # Check for Team Membership
    if task.team_id:
        if any(t.id == task.team_id for t in user.teams) or \
           any(t.id == task.team_id for t in user.owned_teams):
            return task

    JLogger.warning("Task access violation attempt", user_id=user_id, task_id=task_id)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied: You do not have authority over this task.",
    )

    return task
