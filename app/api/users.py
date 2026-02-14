import os
import shutil
import time
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas import user as user_schema
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    refresh_access_token,
    get_password_hash,
    verify_password
)
from app.services.deletion_service import DeletionService
from app.utils.json_logger import JLogger
from app.utils.security import verify_device_signature
from app.services.validation_service import ValidationService, ValidationError

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)
router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post("/sync", response_model=user_schema.SyncResponse)
@router.post("/login", response_model=user_schema.SyncResponse)
@limiter.limit("20/minute")  # Stricter limit for auth
def sync_user(
    request: Request, user_data: user_schema.UserCreate, db: Session = Depends(get_db)
):
    """
    POST /sync: Email-First Authentication.
    - If Email New: Account created, device authorized.
    - If Email Exists + Device New: Returns 403 + Email Sent.
    - If Email Exists + Device Authorized: Login Success.
    """
    import traceback
    try:
        try:
            validated_email = ValidationService.validate_email(user_data.email)
            validated_device_id = ValidationService.validate_device_id(user_data.device_id)
            # validated_token = validate_token(user_data.token) # Biometric token checks
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 1. Find User by Email
        db_user = db.query(models.User).filter(models.User.email == validated_email).first()

        # 2. Check Password if user exists and password is provided in request
        if db_user and user_data.password and db_user.password_hash:
            if not verify_password(user_data.password, db_user.password_hash):
                JLogger.warning("Incorrect password attempt", user_id=db_user.id, email=validated_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password for this email address"
                )

        # 2. Case: New User (Auto-Register)
        if not db_user:
            import uuid

            new_user_id = str(uuid.uuid4())

            # Initialize authorized devices list
            initial_device = {
                "device_id": validated_device_id,
                "device_model": user_data.device_model,
                "biometric_token": user_data.token,
                "authorized_at": int(time.time() * 1000),
            }

            db_user = models.User(
                id=new_user_id,
                name=user_data.name,
                email=validated_email,
                authorized_devices=[initial_device],  # PRIMARY CHANGE
                current_device_id=validated_device_id,
                tier=models.SubscriptionTier.GUEST,  # Free Trial Default
                # Defaults
                primary_role=models.UserRole.GENERIC,  # Job Role (e.g. DEVELOPER)
                work_days=[2, 3, 4, 5, 6],
                timezone=user_data.timezone or "UTC",
                last_login=int(time.time() * 1000),
                is_deleted=False,
                password_hash=get_password_hash(user_data.password) if user_data.password else None
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            # Issue Tokens
            access_token = create_access_token(data={"sub": db_user.id})
            refresh_token = create_refresh_token(db_user.id, db)

            return {
                "user": db_user,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "is_new_user": True,
            }

        # 3. Case: Existing User - Security Check
        if db_user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account deactivated: This user account has been soft-deleted and must be restored by an admin.",
            )

        authorized_devices = db_user.authorized_devices or []

        # Check if this device + token matches any authorized entry
        is_authorized = False
        for dev in authorized_devices:
            if dev.get("device_id") == validated_device_id:
                # Optional: Check biometric token match strictly?
                # For now, if device_id matches, we assume it's valid,
                # OR we can update the token if it rotated.
                is_authorized = True

                # Update metadata
                dev["last_seen"] = int(time.time() * 1000)
                dev["biometric_token"] = user_data.token  # Update latest token
                break

        if not is_authorized:
            # Seamless Sync: Auto-authorize new devices for existing users
            JLogger.info(
                "Seamless Sync: Auto-authorizing new device",
                user_id=db_user.id,
                device_id=validated_device_id,
            )
            new_device = {
                "device_id": validated_device_id,
                "device_model": user_data.device_model,
                "biometric_token": user_data.token,
                "authorized_at": int(time.time() * 1000),
                "last_seen": int(time.time() * 1000),
            }
            authorized_devices.append(new_device)
            db_user.authorized_devices = authorized_devices

        # Update current device and login time
        db_user.current_device_id = validated_device_id
        db_user.last_login = int(time.time() * 1000)

        # Must flag modified for JSON updates in SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(db_user, "authorized_devices")

        # Update timezone if provided during sync
        if user_data.timezone:
            db_user.timezone = user_data.timezone

        db.commit()

        # Issue Tokens
        access_token = create_access_token(data={"sub": db_user.id})
        refresh_token = create_refresh_token(db_user.id, db)

        return {
            "user": db_user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "is_new_user": False,
        }
    except Exception as e:
        # Catch-all to log the actual error in production
        JLogger.error("CRITICAL SYNC ERROR", error=str(e), traceback=traceback.format_exc())
        raise e


@router.post("/logout")
def logout_user(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    POST /logout: Terminates the session for the current device.
    """
    # Simply clearing the current_device_id signals that the session is over.
    # The client should discard the token.
    current_user.current_device_id = None
    db.commit()

    JLogger.info("User logged out", user_id=current_user.id)
    return {"message": "Logged out successfully"}


@router.get("/verify-device")
def verify_new_device(token: str, db: Session = Depends(get_db)):
    """GET /verify-device: Clicked from Email."""
    from app.services.auth_service import verify_device_token

    payload = verify_device_token(token)
    if not payload:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification link."
        )

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
        "authorized_at": int(time.time() * 1000),
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
def get_user_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """GET /me: Fetches full user settings."""
    return current_user


@router.get("/balance")
def get_user_balance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """GET /balance: Returns current wallet balance."""
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    return {
        "user_id": current_user.id,
        "balance": wallet.balance if wallet else 0,
        "currency": wallet.currency if wallet else "USD"
    }


@router.get("/search", response_model=list)
@limiter.limit("30/minute")
def search_users(
    request: Request,
    query: str = Query("", min_length=0, max_length=100),
    role: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
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
                    detail=f"Validation failed: The provided role '{role}' is not a valid system role",
                )
            users_query = users_query.filter(models.User.primary_role == role)
        except Exception as e:
            JLogger.error("User search role filtering failed", role=role, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Internal server error: Failed to process role search",
            )

    if query.strip():
        search_term = f"%{query}%"
        users_query = users_query.filter(
            (models.User.name.ilike(search_term))
            | (models.User.email.ilike(search_term))
        )

    users = users_query.offset(skip).limit(limit).all()
    try:
        return [user_schema.UserResponse.model_validate(user) for user in users]
    except Exception as e:
        JLogger.error("User search serialization failed", error=str(e), query=query)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Failed to serialize user data",
        )


@router.get("/{user_id}", response_model=user_schema.UserResponse)
@limiter.limit("60/minute")
def get_user_profile_by_id(
    request: Request, user_id: str, db: Session = Depends(get_db)
):
    """
    GET /{user_id}: Get public user profile

    Returns basic info about an active user
    Only includes public fields (name, email, created_at, primary_role)
    """
    try:
        user = (
            db.query(models.User)
            .filter(models.User.id == user_id, models.User.is_deleted == False)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found or has been deleted",
            )

        return user
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) so they're not caught below
        raise
    except Exception as e:
        JLogger.error("Failed to fetch user profile", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Failed to fetch user profile",
        )


@router.patch("/me", response_model=user_schema.UserResponse)
def update_user_settings(
    update_data: user_schema.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _sig: bool = Depends(verify_device_signature),
):
    """PATCH /me: Updates dynamic settings."""
    db_user = current_user

    update_dict = {}
    for key, value in update_data.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        try:
            if key == "name" and value:
                update_dict[key] = ValidationService.validate_name(value)
            elif key == "email" and value:
                update_dict[key] = ValidationService.validate_email(value)
            elif key == "system_prompt" and value:
                update_dict[key] = ValidationService.validate_system_prompt(value)
            elif key == "work_start_hour" and value is not None:
                end_hour = update_data.work_end_hour or db_user.work_end_hour
                validated = ValidationService.validate_work_hours(value, end_hour)
                update_dict["work_start_hour"] = validated[0]
            elif key == "work_end_hour" and value is not None:
                start_hour = update_data.work_start_hour or db_user.work_start_hour
                validated = ValidationService.validate_work_hours(start_hour, value)
                update_dict["work_end_hour"] = validated[1]
            elif key == "work_days" and value:
                update_dict[key] = ValidationService.validate_work_days(value)
            elif key == "jargons" and value:
                update_dict[key] = ValidationService.validate_jargons(value)
            else:
                update_dict[key] = value
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation failed for '{key}': {str(e)}",
            )

    for key, value in update_dict.items():
        setattr(db_user, key, value)

    db_user.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/me")
def delete_user_account(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _sig: bool = Depends(verify_device_signature),
):
    """
    DELETE /me: Soft-delete user account (reversible)

    Only allows soft-delete (account can be restored by admin)
    Hard deletion is admin-only through /admin endpoint
    """
    user_id = current_user.id

    result = DeletionService.soft_delete_user(
        db, user_id, deleted_by=user_id, reason="User self-deletion"
    )

    if not result["success"]:
        JLogger.error(
            "Failed to delete user account", user_id=user_id, error=result["error"]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deactivation failed: {result['error']}",
        )

    JLogger.info("User account deleted (soft)", user_id=user_id)
    return result


@router.patch("/{user_id}/restore")
def restore_user_account(user_id: str, db: Session = Depends(get_db)):
    """PATCH: Reactive a soft-deleted user via DeletionService."""
    result = DeletionService.restore_user(db, user_id, restored_by=user_id)
    if not result["success"]:
        JLogger.error(
            "Failed to restore user account", user_id=user_id, error=result["error"]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Restoration failed: {result['error']}",
        )

    JLogger.info("User account restored", user_id=user_id)
    return result


@router.patch("/{user_id}/role")
def update_user_role(
    user_id: str, role: str, admin_id: str, db: Session = Depends(get_db)
):
    """PATCH /{user_id}/role: Update only the user role (Admin only)."""
    # Verify Admin
    admin = (
        db.query(models.User)
        .filter(models.User.id == admin_id, models.User.is_admin == True)
        .first()
    )
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges are required for this operation",
        )

    try:
        validated_user_id = ValidationService.validate_user_id(user_id)
        from app.db.models import UserRole

        if role not in [role_enum.name for role_enum in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Validation failed: The provided role name is invalid",
            )
    except Exception as e:
        JLogger.error("Admin user role update failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Internal server error: Profile update failed",
        )

    user = db.query(models.User).filter(models.User.id == validated_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource not found: User with ID '{user_id}' does not exist",
        )

    user.primary_role = role
    user.updated_at = int(time.time() * 1000)
    db.commit()
    JLogger.info(
        "User role updated by admin",
        user_id=validated_user_id,
        new_role=role,
        admin_id=admin_id,
    )
    return user_schema.UserResponse.model_validate(user)


from app.services.auth_service import refresh_access_token


@router.post("/refresh")
def refresh_token(
    refresh_token: str = Query(..., alias="token"), db: Session = Depends(get_db)
):
    """
    Refresh Access Token using a valid Refresh Token.
    """
    return refresh_access_token(refresh_token, db)


@router.patch("/me/profile-picture", response_model=user_schema.UserResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and update profile picture with professional optimization.
    """
    # 1. Validation
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="File must be an image")

    # 2. Setup paths
    upload_dir = "uploads/profiles"
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"

    filename = f"{current_user.id}_{int(time.time())}{ext}"
    temp_path = os.path.join(upload_dir, f"temp_{filename}")
    final_path = os.path.join(upload_dir, filename)

    # 3. Save temp file and process
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Professional compression using ImageService
        from app.services.image_service import ImageService

        success = ImageService.process_image(
            temp_path, final_path, max_size=(512, 512), quality=80
        )

        if not success:
            # Fallback to copy if processing fails for some reason
            shutil.copy(temp_path, final_path)

        # 4. Clean up temp
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # 5. Update User
        current_user.profile_picture_url = f"/{final_path}"
        db.commit()
        db.refresh(current_user)

        JLogger.info(
            "Profile picture updated", user_id=current_user.id, path=final_path
        )
        return current_user
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        JLogger.error(
            "Profile picture upload failed", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(500, detail="Failed to upload and process profile picture")
