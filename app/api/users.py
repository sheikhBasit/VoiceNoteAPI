from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from app.schemas import user  # Fixed import
from app.utils.users_validation import (
    validate_email, validate_work_hours, validate_work_days, 
    validate_jargons, validate_device_model, validate_system_prompt,
    validate_user_id, validate_token, validate_device_id, validate_name,
    ValidationError
)
from typing import Optional
import time
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/0") 
router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.post("/sync", response_model=dict)
@limiter.limit("5/hour")
def sync_user(user_data: user.UserCreate, db: Session = Depends(get_db)):
    """
    POST /sync: Onboarding/Login. 
    Registers device ID and sets up the primary user role and system prompt.
    
    Phase 2 Fixes:
    - Email validation (RFC 5322)
    - Work hours validation (0-24)
    - Work days validation (0-6)
    - Jargons deduplication & validation
    - Device model sanitization
    - System prompt validation
    - Last login update on sync
    """
    try:
        # Phase 2 Fix: Validate all inputs
        validated_email = validate_email(user_data.email)
        validated_user_id = validate_user_id(user_data.id)
        validated_token = validate_token(user_data.token)
        validated_device_id = validate_device_id(user_data.device_id)
        validated_device_model = validate_device_model(user_data.device_model)
        validated_name = validate_name(user_data.name)
        validated_work_hours = validate_work_hours(user_data.work_start_hour, user_data.work_end_hour)
        validated_work_days = validate_work_days(user_data.work_days)
        validated_jargons = validate_jargons(user_data.jargons)
        validated_system_prompt = validate_system_prompt(user_data.system_prompt)
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    db_user = db.query(models.User).filter(models.User.id == validated_user_id).first()
    
    if not db_user:
        # First time onboarding - create with validated data
        db_user = models.User(
            id=validated_user_id,
            name=validated_name,
            email=validated_email,
            token=validated_token,
            device_id=validated_device_id,
            device_model=validated_device_model,
            primary_role=user_data.primary_role,
            secondary_role=user_data.secondary_role,
            system_prompt=validated_system_prompt,
            work_start_hour=validated_work_hours[0],
            work_end_hour=validated_work_hours[1],
            work_days=validated_work_days,
            jargons=validated_jargons,
            last_login=int(time.time() * 1000),
            is_deleted=False
        )
        db.add(db_user)
    else:
        # Phase 2 Fix: Update existing user sync info (token, last login, validated fields)
        db_user.token = validated_token
        db_user.device_id = validated_device_id
        db_user.device_model = validated_device_model
        db_user.name = validated_name
        db_user.email = validated_email
        db_user.last_login = int(time.time() * 1000)  # Update last login on sync
        if validated_system_prompt:
            db_user.system_prompt = validated_system_prompt
        if user_data.primary_role:
            db_user.primary_role = user_data.primary_role
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=dict)
@limiter.limit("60/minute")
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """
    GET /me: Fetches full user settings including Work hours and Jargons.
    
    Phase 2 Fixes:
    - Validate user_id format
    - Add error handling
    """
    try:
        validated_user_id = validate_user_id(user_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user = db.query(models.User).filter(models.User.id == validated_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/search", response_model=list)
@limiter.limit("30/minute")
def search_users(
    query: str = Query("", min_length=0, max_length=100),
    role: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    GET /search: Search users by name, email, or filter by role.
    
    Phase 2 Feature:
    - Search by name or email
    - Filter by role
    - Pagination support
    - Exclude deleted users
    
    Query Parameters:
        query: Search term (name or email)
        role: Filter by primary role
        skip: Pagination skip
        limit: Pagination limit (1-500)
    """
    # Start with non-deleted users
    users_query = db.query(models.User).filter(models.User.is_deleted == False)
    
    # Filter by role if provided
    if role:
        try:
            from app.db.models import UserRole
            valid_roles = [role_enum.value for role_enum in UserRole]
            if role not in valid_roles:
                raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
            users_query = users_query.filter(models.User.primary_role == role)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Search by name or email if query provided
    if query.strip():
        search_term = f"%{query}%"
        users_query = users_query.filter(
            (models.User.name.ilike(search_term)) |
            (models.User.email.ilike(search_term))
        )
    
    # Apply pagination
    total = users_query.count()
    users = users_query.offset(skip).limit(limit).all()
    
    return [user_schema.UserResponse.model_validate(user) for user in users]

@router.patch("/me", response_model=user_schema.UserResponse)
def update_user_settings(
    user_id: str, 
    update_data: user_schema.UserUpdate, 
    db: Session = Depends(get_db)
):
    """
    PATCH /me: Updates dynamic settings like system prompt, jargons, or work days.
    
    Phase 2 Fixes:
    - Validate all input fields
    - Sanitize string inputs
    - Add field update validation
    - Track updated_at timestamp
    """
    try:
        validated_user_id = validate_user_id(user_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    db_user = db.query(models.User).filter(models.User.id == validated_user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Phase 2 Fix: Validate each field being updated
    update_dict = {}
    
    for key, value in update_data.model_dump(exclude_unset=True).items():
        if value is None:
            continue
            
        try:
            # Validate specific fields
            if key == "name" and value:
                update_dict[key] = validate_name(value)
            elif key == "email" and value:
                update_dict[key] = validate_email(value)
            elif key == "system_prompt" and value:
                update_dict[key] = validate_system_prompt(value)
            elif key == "work_start_hour" and value is not None:
                # Re-validate work hours together
                end_hour = update_data.work_end_hour or db_user.work_end_hour
                validated = validate_work_hours(value, end_hour)
                update_dict["work_start_hour"] = validated[0]
            elif key == "work_end_hour" and value is not None:
                # Re-validate work hours together
                start_hour = update_data.work_start_hour or db_user.work_start_hour
                validated = validate_work_hours(start_hour, value)
                update_dict["work_end_hour"] = validated[1]
            elif key == "work_days" and value:
                update_dict[key] = validate_work_days(value)
            elif key == "jargons" and value:
                update_dict[key] = validate_jargons(value)
            elif key == "primary_role" and value:
                update_dict[key] = value  # Enum validation handled by schema
            else:
                update_dict[key] = value
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"{key}: {str(e)}")
    
    # Phase 2 Fix: Update only validated fields and track update time
    for key, value in update_dict.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = int(time.time() * 1000)  # Track when profile was updated
    
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

    notes = db.query(models.Note).filter(models.Note.user_id == user_id).all()
    now = int(time.time() * 1000)

    if hard:
        # Hard delete will cascade to Notes and Tasks if defined in models
        for note in notes:
            # Delete tasks for each note
            db.query(models.Task).filter(models.Task.note_id == note.id).delete()
            db.delete(note)
        db.delete(db_user)
        message = "Account and all data permanently erased."
    else:
        # Soft delete logic
        db_user.is_deleted = True
        db_user.deleted_at = now
        for note in notes:
            note.is_deleted = True
            note.deleted_at = now
            # Soft delete all tasks for this note
            db.query(models.Task).filter(models.Task.note_id == note.id).update({
                "is_deleted": True, "deleted_at": now
            })
        message = "Account deactivated (Soft Delete)."

    db.commit()
    return {"status": "success", "message": message, "type": "hard" if hard else "soft"}


@router.patch("/{user_id}/role")
def update_user_role(user_id: str, role: str, db: Session = Depends(get_db)):
    """
    PATCH /{user_id}/role: Explicitly update only the user role.
    
    Phase 2 Fixes:
    - Validate user_id format
    - Validate role enum value
    - Track update time
    """
    try:
        validated_user_id = validate_user_id(user_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user = db.query(models.User).filter(models.User.id == validated_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Phase 2 Fix: Validate role is a valid enum value
    try:
        # This will raise ValueError if invalid
        from app.db.models import UserRole
        valid_roles = [role_enum.value for role_enum in UserRole]
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user.primary_role = role
    user.updated_at = int(time.time() * 1000)  # Track update time
    db.commit()
    return user_schema.UserResponse.model_validate(user)


@router.patch("/{user_id}/restore")
def restore_user_account(user_id: str, db: Session = Depends(get_db)):
    """PATCH: Reactive a soft-deleted user and all their history."""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Restore User
    db_user.is_deleted = False
    db_user.deleted_at = None

    # 2. Find all notes belonging to this user
    notes = db.query(models.Note).filter(models.Note.user_id == user_id).all()
    
    for note in notes:
        note.is_deleted = False
        note.deleted_at = None
        # 3. Restore tasks for each note
        db.query(models.Task).filter(models.Task.note_id == note.id).update({
            "is_deleted": False, 
            "deleted_at": None
        })

    db.commit()
    return {"message": "User account and all historical data have been reactivated."}