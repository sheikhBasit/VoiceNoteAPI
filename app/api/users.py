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
@limiter.limit("20/minute") # Stricter limit for auth
def sync_user(request: Request, user_data: user_schema.UserCreate, db: Session = Depends(get_db)):
    """
    POST /sync: Email-First Authentication.
    - If Email New: Account created, device authorized.
    - If Email Exists + Device New: Returns 403 + Email Sent.
    - If Email Exists + Device Authorized: Login Success.
    """
    try:
        validated_email = validate_email(user_data.email)
        validated_device_id = validate_device_id(user_data.device_id)
        # validated_token = validate_token(user_data.token) # Biometric token checks
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 1. Find User by Email
    db_user = db.query(models.User).filter(models.User.email == validated_email).first()
    
    # 2. Case: New User (Auto-Register)
    if not db_user:
        import uuid
        new_user_id = str(uuid.uuid4())
        
        # Initialize authorized devices list
        initial_device = {
            "device_id": validated_device_id,
            "device_model": user_data.device_model,
            "biometric_token": user_data.token,
            "authorized_at": int(time.time() * 1000)
        }
        
        db_user = models.User(
            id=new_user_id,
            name=user_data.name,
            email=validated_email,
            authorized_devices=[initial_device], # PRIMARY CHANGE
            current_device_id=validated_device_id,
            
            # Defaults
            primary_role=user_data.primary_role,
            work_days=[2,3,4,5,6],
            last_login=int(time.time() * 1000),
            is_deleted=False
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Issue Token
        access_token = create_access_token(data={"sub": db_user.id})
        return {"user": db_user, "access_token": access_token, "token_type": "bearer"}

    # 3. Case: Existing User - Check Device Authorization
    authorized_devices = db_user.authorized_devices or []
    
    # Check if this device + token matches any authorized entry
    is_authorized = False
    for dev in authorized_devices:
        if dev.get("device_id") == validated_device_id:
            # Optional: Check biometric token match strictly? 
            # For now, if device_id matches, we assume it's valid, 
            # OR we can update the token if it rotated.
            is_authorized = True
            
            # Update metadata if needed
            dev["last_seen"] = int(time.time() * 1000)
            dev["biometric_token"] = user_data.token # Update latest token
            break
            
    if is_authorized:
        # Login Success
        db_user.current_device_id = validated_device_id
        db_user.last_login = int(time.time() * 1000)
        
        # Must flag modified for JSON updates in SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(db_user, "authorized_devices")
        
        db.commit()
        access_token = create_access_token(data={"sub": db_user.id})
        return {"user": db_user, "access_token": access_token, "token_type": "bearer"}
        
    else:
        # 4. Case: UNKNOWN DEVICE -> Trigger Magic Link
        from app.services.auth_service import create_device_verification_token, mock_send_verification_email
        
        # Generate Verification Token
        verification_token = create_device_verification_token(
            email=validated_email,
            device_id=validated_device_id,
            device_model=user_data.device_model,
            biometric_token=user_data.token
        )
        
        # Construct Link (In real app, this is a deep link or web url)
        # e.g. https://api.voicenote.ai/api/v1/users/verify-device?token=...
        magic_link = f"http://localhost:8000/api/v1/users/verify-device?token={verification_token}"
        
        mock_send_verification_email(validated_email, magic_link)
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device not authorized. Check your email to verify this device.",
            headers={"X-Auth-Reason": "DEVICE_VERIFICATION_REQUIRED"}
        )

@router.get("/verify-device")
def verify_new_device(token: str, db: Session = Depends(get_db)):
    """GET /verify-device: Clicked from Email."""
    from app.services.auth_service import verify_device_token
    
    payload = verify_device_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")
        
    email = payload["sub"]
    device_id = payload["device_id"]
    
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    # check if already authorized
    authorized_devices = db_user.authorized_devices or []
    for dev in authorized_devices:
        if dev.get("device_id") == device_id:
             return {"message": "Device already authorized. You can login now."}
             
    # Add new device
    new_device = {
        "device_id": device_id,
        "device_model": payload["device_model"],
        "biometric_token": payload["biometric_token"],
        "authorized_at": int(time.time() * 1000)
    }
    
    authorized_devices.append(new_device)
    db_user.authorized_devices = authorized_devices
    
    # Must flag modified
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(db_user, "authorized_devices")
    
    db.commit()
    
    return {"message": "Device authorized successfully! Return to the app to login."}

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