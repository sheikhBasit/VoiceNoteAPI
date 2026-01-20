from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from app.schemas import user_schema  # Assuming you have User schemas defined
import time
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/0") 
router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.post("/sync", response_model=user_schema.UserResponse)
@limiter.limit("5/hour")
def sync_user(user_data: user_schema.UserCreate, db: Session = Depends(get_db)):
    """
    POST /sync: Onboarding/Login. 
    Registers device ID and sets up the primary user role and system prompt.
    """
    db_user = db.query(models.User).filter(models.User.id == user_data.id).first()
    
    if not db_user:
        # First time onboarding
        db_user = models.User(**user_data.model_dump())
        db.add(db_user)
    else:
        # Update existing user sync info (token, last login)
        db_user.token = user_data.token
        db_user.last_login = int(time.time() * 1000)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=user_schema.UserResponse)
@limiter.limit("60/minute")
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """GET /me: Fetches full user settings including Work hours and Jargons."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/me", response_model=user_schema.UserResponse)
def update_user_settings(
    user_id: str, 
    update_data: user_schema.UserUpdate, 
    db: Session = Depends(get_db)
):
    """PATCH /me: Updates dynamic settings like system prompt, jargons, or work days."""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only the fields provided in the request
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/me")
def delete_user_account(user_id: str, hard: bool = False, db: Session = Depends(get_db)):
    """
    DELETE /me: Handles account deletion.
    Soft Delete: Hides account (is_deleted = true).
    Hard Delete: Wipes user and all associated Notes/Tasks from DB.
    """
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if hard:
        # Hard delete will cascade to Notes and Tasks if defined in models
        db.delete(db_user)
        message = "Account and all data permanently erased."
    else:
        # Soft delete logic
        db_user.is_deleted = True
        db_user.deleted_at = int(time.time() * 1000)
        message = "Account deactivated (Soft Delete)."

    db.commit()
    return {"status": "success", "message": message, "type": "hard" if hard else "soft"}