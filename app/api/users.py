from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from app.schemas import user as user_schema
from app.utils.users_validation import (
    validate_email, validate_work_hours, validate_work_days, 
    validate_jargons, validate_device_model, validate_system_prompt,
    validate_user_id, validate_token, validate_device_id, validate_name,
    ValidationError
)
from app.services.deletion_service import DeletionService
from typing import Optional
import time
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.utils.json_logger import JLogger
from app.services.auth_service import create_access_token, get_current_user

limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0")) 
router = APIRouter(prefix="/api/v1/users", tags=["Users"])
@router.post("/sync", response_model=user_schema.SyncResponse)
@limiter.limit("100/minute")
def sync_user(request: Request, user_data: user_schema.UserCreate, db: Session = Depends(get_db)):
    """
    POST /sync: Onboarding/Login. 
    Registers device ID and sets up the primary user role and system prompt.
    """
    try:
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Validation failed: {str(e)}"
        )
    
    db_user = db.query(models.User).filter(models.User.id == validated_user_id).first()
    
    if not db_user:
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
        db_user.token = validated_token
        db_user.device_id = validated_device_id
        db_user.device_model = validated_device_model
        db_user.name = validated_name
        db_user.email = validated_email
        db_user.last_login = int(time.time() * 1000)
        if validated_system_prompt:
            db_user.system_prompt = validated_system_prompt
        if user_data.primary_role:
            db_user.primary_role = user_data.primary_role
    
    db.commit()
    db.refresh(db_user)
    
    # ISSUE JWT TOKEN
    access_token = create_access_token(data={"sub": db_user.id})
    
    JLogger.info("User synced profile", user_id=db_user.id, email=db_user.email)
    return {
        "user": db_user,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=user_schema.UserResponse)
@limiter.limit("60/minute")
def get_user_profile(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """GET /me: Fetches full user settings."""
    return current_user

@router.get("/search", response_model=list)
@limiter.limit("30/minute")
def search_users(
    request: Request,
    query: str = Query("", min_length=0, max_length=100),
    role: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """GET /search: Search users."""
    users_query = db.query(models.User).filter(models.User.is_deleted == False)
    
    if role:
        try:
            from app.db.models import UserRole
            valid_roles = [role_enum.value for role_enum in UserRole]
            if role not in valid_roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Validation failed: The provided role '{role}' is not a valid system role"
                )
            users_query = users_query.filter(models.User.primary_role == role)
        except Exception as e:
            JLogger.error("User search role filtering failed", role=role, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Internal server error: Failed to process role search"
            )
    
    if query.strip():
        search_term = f"%{query}%"
        users_query = users_query.filter(
            (models.User.name.ilike(search_term)) |
            (models.User.email.ilike(search_term))
        )
    
    users = users_query.offset(skip).limit(limit).all()
    try:
        return [user_schema.UserResponse.model_validate(user) for user in users]
    except Exception as e:
        JLogger.error("User search serialization failed", error=str(e), query=query)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Failed to serialize user data"
        )

@router.patch("/me", response_model=user_schema.UserResponse)
def update_user_settings(
    update_data: user_schema.UserUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """PATCH /me: Updates dynamic settings."""
    db_user = current_user

    update_dict = {}
    for key, value in update_data.model_dump(exclude_unset=True).items():
        if value is None: continue
        try:
            if key == "name" and value:
                update_dict[key] = validate_name(value)
            elif key == "email" and value:
                update_dict[key] = validate_email(value)
            elif key == "system_prompt" and value:
                update_dict[key] = validate_system_prompt(value)
            elif key == "work_start_hour" and value is not None:
                end_hour = update_data.work_end_hour or db_user.work_end_hour
                validated = validate_work_hours(value, end_hour)
                update_dict["work_start_hour"] = validated[0]
            elif key == "work_end_hour" and value is not None:
                start_hour = update_data.work_start_hour or db_user.work_start_hour
                validated = validate_work_hours(start_hour, value)
                update_dict["work_end_hour"] = validated[1]
            elif key == "work_days" and value:
                update_dict[key] = validate_work_days(value)
            elif key == "jargons" and value:
                update_dict[key] = validate_jargons(value)
            else:
                update_dict[key] = value
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Validation failed for '{key}': {str(e)}"
            )
    
    for key, value in update_dict.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/me")
def delete_user_account(hard: bool = False, admin_id: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """DELETE /me: Handles account deletion via DeletionService."""
    user_id = current_user.id
    if hard:
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Permission denied: Admin ID must be provided to perform a hard account deletion"
            )
        admin = db.query(models.User).filter(models.User.id == admin_id, models.User.is_admin == True).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Permission denied: Administrative privileges are required for this operation"
            )
        result = DeletionService.hard_delete_user(db, user_id, admin_id=admin_id)
    else:
        result = DeletionService.soft_delete_user(db, user_id, deleted_by=user_id, reason="User self-deletion")
    
    if not result["success"]:
        JLogger.error("Failed to delete user account", user_id=user_id, error=result["error"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Deactivation failed: {result['error']}"
        )
    
    JLogger.info("User account deleted", user_id=user_id, hard=hard, admin_id=admin_id)
    return result

@router.patch("/{user_id}/restore")
def restore_user_account(user_id: str, db: Session = Depends(get_db)):
    """PATCH: Reactive a soft-deleted user via DeletionService."""
    result = DeletionService.restore_user(db, user_id, restored_by=user_id)
    if not result["success"]:
        JLogger.error("Failed to restore user account", user_id=user_id, error=result["error"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Restoration failed: {result['error']}"
        )
    
    JLogger.info("User account restored", user_id=user_id)
    return result

@router.patch("/{user_id}/role")
def update_user_role(user_id: str, role: str, admin_id: str, db: Session = Depends(get_db)):
    """PATCH /{user_id}/role: Update only the user role (Admin only)."""
    # Verify Admin
    admin = db.query(models.User).filter(models.User.id == admin_id, models.User.is_admin == True).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges are required for this operation"
        )
        
    try:
        validated_user_id = validate_user_id(user_id)
        from app.db.models import UserRole
        if role not in [role_enum.name for role_enum in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Validation failed: The provided role name is invalid"
            )
    except Exception as e:
        JLogger.error("Admin user role update failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Internal server error: Profile update failed"
        )
    
    user = db.query(models.User).filter(models.User.id == validated_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Resource not found: User with ID '{user_id}' does not exist"
        )
    
    user.primary_role = role
    user.updated_at = int(time.time() * 1000)
    db.commit()
    JLogger.info("User role updated by admin", user_id=validated_user_id, new_role=role, admin_id=admin_id)
    return user_schema.UserResponse.model_validate(user)