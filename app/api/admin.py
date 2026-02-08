"""
Admin API Endpoints

Provides endpoints for:
- User management
- Content moderation
- Analytics & reporting
- System settings
- Permission management
"""

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_management
from app.db import models
from app.db.session import get_db
from app.schemas import billing as billing_schema
from app.schemas import system as system_schema
from app.schemas import user as user_schema
from app.services.auth_service import get_current_active_admin
from app.utils.admin_utils import AdminManager
from app.utils.ai_service_utils import AIServiceError
from app.utils.json_logger import JLogger

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ==================== USER MANAGEMENT ====================


@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: str,
    level: str = Query("full", pattern="^(full|moderator|viewer)$"),
    admin_user: models.User = Depends(require_admin_management),
    db: Session = Depends(get_db),
):
    """
    Promote user to admin role

    **Authorization:** Admin + can_manage_admins permission

    Args:
        user_id: User to promote
        level: Permission level ("full", "moderator", "viewer")

    Returns:
        Updated user with admin role
    """
    try:
        # Admin and permission already verified by dependency!

        updated_user = AdminManager.grant_admin_role(
            db=db, user_id=user_id, granted_by=admin_user.id, permission_level=level
        )

        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="MAKE_ADMIN",
            target_id=user_id,
            details={"level": level},
        )

        return {
            "status": "success",
            "message": f"User promoted to {level} admin",
            "user": updated_user,
        }
    except AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/remove-admin")
async def remove_user_admin(
    user_id: str,
    admin_user: models.User = Depends(require_admin_management),
    db: Session = Depends(get_db),
):
    """
    Revoke admin role from user

    **Authorization:** Admin + can_manage_admins permission
    """
    try:
        # Admin and permission already verified by dependency!

        updated_user = AdminManager.revoke_admin_role(db=db, user_id=user_id)

        AdminManager.log_admin_action(
            db=db, admin_id=admin_user.id, action="REMOVE_ADMIN", target_id=user_id
        )

        return {
            "status": "success",
            "message": "Admin role revoked",
            "user": updated_user,
        }
    except AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users")
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    List all users in system

    Permission Required: can_view_all_users
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_view_all_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_view_all_users' is missing",
        )

    from sqlalchemy.orm import joinedload

    users = (
        db.query(models.User)
        .options(joinedload(models.User.wallet), joinedload(models.User.plan))
        .offset(skip)
        .limit(limit)
        .all()
    )
    total = db.query(models.User).count()

    # Enhanced user list with usage summaries
    results = []
    for u in users:
        wallet = u.wallet
        results.append(
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "is_admin": u.is_admin,
                "plan_id": u.plan_id,
                "plan_name": u.plan.name if u.plan else "NONE",
                "balance": wallet.balance if wallet else 0,
                "usage_stats": u.usage_stats,
                "is_deleted": u.is_deleted,
                "last_login": u.last_login,
            }
        )

    return {"total": total, "skip": skip, "limit": limit, "users": results}


@router.get("/users/stats")
async def get_user_statistics(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get statistics about all users

    Permission Required: can_view_analytics
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_view_analytics' is missing",
        )

    total_users = db.query(models.User).count()
    admin_count = db.query(models.User).filter(models.User.is_admin == True).count()
    active_users = db.query(models.User).filter(models.User.is_deleted == False).count()

    return {
        "total_users": total_users,
        "admin_count": admin_count,
        "active_users": active_users,
        "deleted_users": total_users - active_users,
        "timestamp": int(time.time() * 1000),
    }


# ==================== CONTENT MODERATION ====================


@router.get("/notes")
async def list_all_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    View all notes across all users

    Permission Required: can_view_all_notes
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_view_all_notes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_view_all_notes' is missing",
        )

    notes = db.query(models.Note).offset(skip).limit(limit).all()
    total = db.query(models.Note).count()

    return {"total": total, "skip": skip, "limit": limit, "notes": notes}


@router.delete("/notes/{note_id}")
async def delete_note_as_admin(
    note_id: str,
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Delete note as admin (content moderation)

    Permission Required: can_delete_notes
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_delete_notes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_delete_notes' is missing",
        )

    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID '{note_id}' not found",
        )

    note.is_deleted = True
    note.deleted_at = int(time.time() * 1000)
    db.commit()

    AdminManager.log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="DELETE_NOTE",
        target_id=note_id,
        details={"reason": reason},
    )

    return {"status": "success", "message": "Note deleted", "note_id": note_id}


@router.delete("/users/{user_id}")
async def delete_user_as_admin(
    user_id: str,
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Delete user account as admin

    Permission Required: can_delete_users
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_delete_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_delete_users' is missing",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    user.is_deleted = True
    user.deleted_at = int(time.time() * 1000)

    # Soft delete all user's notes
    db.query(models.Note).filter(models.Note.user_id == user_id).update(
        {"is_deleted": True, "deleted_at": int(time.time() * 1000)}
    )

    db.commit()

    AdminManager.log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="DELETE_USER",
        target_id=user_id,
        details={"reason": reason},
    )

    return {"status": "success", "message": "User deleted", "user_id": user_id}


@router.get("/users/{user_id}")
async def get_user_details_admin(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get detailed admin view of user account

    Permission Required: can_view_all_users

    Returns:
    - User account details
    - Admin status and permissions
    - Device list
    - Usage statistics
    - Wallet/subscription info
    - Last login time
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_view_all_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_view_all_users' is missing",
        )

    try:
        from sqlalchemy.orm import joinedload

        user = (
            db.query(models.User)
            .options(joinedload(models.User.wallet), joinedload(models.User.plan))
            .filter(models.User.id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )

        # Count user content
        notes_count = (
            db.query(models.Note).filter(models.Note.user_id == user_id).count()
        )
        tasks_count = (
            db.query(models.Task).filter(models.Task.user_id == user_id).count()
        )

        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "is_admin": user.is_admin,
                "admin_permissions": user.admin_permissions if user.is_admin else None,
                "is_deleted": user.is_deleted,
                "deleted_at": user.deleted_at if user.is_deleted else None,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "last_login": user.last_login,
            },
            "subscription": {
                "plan": user.plan.name if user.plan else "NONE",
                "tier": user.tier.value if user.tier else "GUEST",
                "balance": user.wallet.balance if user.wallet else 0,
                "monthly_limit": user.wallet.monthly_limit if user.wallet else 0,
                "used_this_month": user.wallet.used_this_month if user.wallet else 0,
            },
            "devices": user.authorized_devices or [],
            "content": {"notes_count": notes_count, "tasks_count": tasks_count},
            "usage": user.usage_stats or {},
            "timestamp": int(time.time() * 1000),
        }
    except HTTPException:
        raise
    except Exception as e:
        JLogger.error("Failed to fetch user details", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Failed to fetch user details",
        )


@router.patch("/users/{user_id}", response_model=user_schema.UserResponse)
async def update_user_details_admin(
    user_id: str,
    update_data: user_schema.UserUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Update user details (Admin)

    Permission Required: can_delete_users (as proxy for full user write access)
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    # Using can_delete_users as it implies high-level user management rights
    if not AdminManager.has_permission(admin_user, "can_delete_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_delete_users' is missing",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    # Import validation explicitly to avoid circular dependencies at module level if any
    from app.services.validation_service import ValidationService, ValidationError

    update_dict = {}
    for key, value in update_data.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        try:
            if key == "name" and value:
                update_dict[key] = ValidationService.validate_name(value)
            elif key == "email" and value:
                # Check if email is taken by another user
                existing = (
                    db.query(models.User)
                    .filter(models.User.email == value, models.User.id != user_id)
                    .first()
                )
                if existing:
                    raise HTTPException(status_code=400, detail="Email already in use")
                update_dict[key] = ValidationService.validate_email(value)
            elif key == "system_prompt" and value:
                update_dict[key] = ValidationService.validate_system_prompt(value)
            elif key == "work_start_hour" and value is not None:
                end_hour = update_data.work_end_hour or user.work_end_hour
                validated = ValidationService.validate_work_hours(value, end_hour)
                update_dict["work_start_hour"] = validated[0]
            elif key == "work_end_hour" and value is not None:
                start_hour = update_data.work_start_hour or user.work_start_hour
                validated = ValidationService.validate_work_hours(start_hour, value)
                update_dict["work_end_hour"] = validated[1]
            elif key == "timezone" and value:
                # Basic timezone validation could go here, for now trust schema or add validation
                update_dict[key] = value
            elif key == "primary_role" and value:
                # Role validation handled by Enum in schema usually, but logic here:
                update_dict[key] = value
            else:
                update_dict[key] = value
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation failed for '{key}': {str(e)}",
            )

    try:
        for key, value in update_dict.items():
            setattr(user, key, value)

        user.updated_at = int(time.time() * 1000)
        db.commit()
        db.refresh(user)

        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="UPDATE_USER",
            target_id=user_id,
            details={"updates": list(update_dict.keys())},
        )

        return user
    except Exception as e:
        db.rollback()
        JLogger.error(
            "Failed to update user",
            user_id=user_id,
            admin_id=admin_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Failed to update user",
        )


@router.delete("/users/{user_id}/hard")
async def hard_delete_user_as_admin(
    user_id: str,
    confirmation: str = Query("", description="Must equal user_id for confirmation"),
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Hard delete user account permanently (IRREVERSIBLE)

    Permission Required: can_delete_users

    WARNING: This permanently deletes:
    - User account
    - All notes
    - All tasks
    - All audit logs
    - Cannot be undone!

    Args:
        user_id: User to delete
        confirmation: Must match user_id to prevent accidental deletion
        reason: Reason for deletion (stored in audit)
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_delete_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_delete_users' is missing",
        )

    # Safety check: require confirmation
    if confirmation != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation mismatch: confirmation must equal user_id to prevent accidental deletion",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    try:
        from app.services.deletion_service import DeletionService

        # Perform hard delete via service
        result = DeletionService.hard_delete_user(
            db=db, user_id=user_id, admin_id=admin_user.id
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Hard delete failed: {result.get('error', 'Unknown error')}",
            )

        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="HARD_DELETE_USER",
            target_id=user_id,
            details={
                "reason": reason,
                "notes_deleted": result.get("notes_deleted", 0),
                "tasks_deleted": result.get("tasks_deleted", 0),
            },
        )

        return {
            "status": "success",
            "message": "User permanently deleted (irreversible)",
            "user_id": user_id,
            "deleted_items": {
                "notes": result.get("notes_deleted", 0),
                "tasks": result.get("tasks_deleted", 0),
                "deleted_at": int(time.time() * 1000),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        JLogger.error(
            "Hard delete user failed",
            user_id=user_id,
            admin_id=admin_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Hard delete operation failed",
        )


@router.patch("/users/{user_id}/restore")
async def restore_user_as_admin(
    user_id: str,
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Restore a soft-deleted user account (admin only)

    Permission Required: can_manage_admins

    Restores:
    - User account status
    - User's soft-deleted notes
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_manage_admins' is missing",
        )

    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )

        if not user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not deleted",
            )

        # Restore user
        user.is_deleted = False
        user.deleted_at = None

        # Restore user's notes
        notes_restored = (
            db.query(models.Note)
            .filter(models.Note.user_id == user_id, models.Note.is_deleted == True)
            .update({"is_deleted": False, "deleted_at": None})
        )

        db.commit()

        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="RESTORE_USER",
            target_id=user_id,
            details={"reason": reason, "notes_restored": notes_restored},
        )

        return {
            "status": "success",
            "message": "User account restored",
            "user_id": user_id,
            "restored_at": int(time.time() * 1000),
            "notes_restored": notes_restored,
        }
    except HTTPException:
        raise
    except Exception as e:
        JLogger.error(
            "Restore user failed", user_id=user_id, admin_id=admin_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Restore operation failed",
        )


@router.get("/users/{user_id}/devices")
async def get_user_devices(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get list of user's authorized devices

    Permission Required: can_view_all_users

    Returns:
    - Device list with timestamps
    - Current active device
    - Device authorization history
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_view_all_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_view_all_users' is missing",
        )

    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )

        return {
            "user_id": user_id,
            "current_device_id": user.current_device_id,
            "devices": user.authorized_devices or [],
            "total_devices": len(user.authorized_devices or []),
            "timestamp": int(time.time() * 1000),
        }
    except HTTPException:
        raise
    except Exception as e:
        JLogger.error("Failed to fetch user devices", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Failed to fetch user devices",
        )


# ==================== PERMISSION MANAGEMENT ====================


@router.put("/permissions/{user_id}")
async def update_admin_permissions(
    user_id: str,
    permissions: dict,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Update permissions for an admin user

    Permission Required: can_manage_admins

    Example body:
    {
        "can_view_all_notes": true,
        "can_delete_notes": false,
        "can_manage_admins": false
    }
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_manage_admins' is missing",
        )

    try:
        updated_user = AdminManager.update_permissions(
            db=db, user_id=user_id, permissions=permissions
        )

        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="UPDATE_PERMISSIONS",
            target_id=user_id,
            details={"permissions": permissions},
        )

        return {
            "status": "success",
            "message": "Permissions updated",
            "user": updated_user,
        }
    except AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admins")
async def list_all_admins(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    List all admin users

    Permission Required: can_manage_admins
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_manage_admins' is missing",
        )

    admins = db.query(models.User).filter(models.User.is_admin == True).all()

    return {"total": len(admins), "admins": admins}


# ==================== SYSTEM INFO ====================


@router.get("/status")
async def get_admin_panel_status(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get admin panel status and system information

    Permission Required: is_admin
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    return {
        "status": "operational",
        "admin_id": admin_user.id,
        "admin_name": admin_user.name,
        "permissions": admin_user.admin_permissions,
        "last_action": admin_user.admin_last_action,
        "created_at": admin_user.admin_created_at,
        "timestamp": int(time.time() * 1000),
    }


# ==================== SYSTEM SETTINGS ====================


@router.get("/settings/ai", response_model=system_schema.AISettingsResponse)
async def get_ai_settings(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    GET /settings/ai: Retrieve global AI parameters.
    Permission Required: is_admin
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    settings = db.query(models.SystemSettings).first()
    if not settings:
        # Initialize default if missing
        settings = models.SystemSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.patch("/settings/ai", response_model=system_schema.AISettingsResponse)
async def update_ai_settings(
    settings_update: system_schema.AISettingsUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    PATCH /settings/ai: Update global AI parameters.
    Permission Required: can_modify_system_settings
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )

    if not AdminManager.has_permission(admin_user, "can_modify_system_settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Required permission 'can_modify_system_settings' is missing",
        )

    settings = db.query(models.SystemSettings).first()
    if not settings:
        settings = models.SystemSettings(id=1)
        db.add(settings)
        db.commit()

    update_data = settings_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)

    settings.updated_at = int(time.time() * 1000)
    settings.updated_by = admin_user.id

    db.commit()
    db.refresh(settings)

    AdminManager.log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="UPDATE_AI_SETTINGS",
        target_id="GLOBAL_SYSTEM_SETTINGS",
        details=update_data,
    )

    return settings


# ==================== BILLING & USAGE MANAGEMENT ====================


@router.post("/plans", response_model=billing_schema.ServicePlanResponse)
async def create_service_plan(
    plan: billing_schema.ServicePlanCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Create a new billing/service plan."""
    if not AdminManager.has_permission(admin_user, "can_modify_system_settings"):
        raise HTTPException(status_code=403, detail="Permission denied")

    db_plan = models.ServicePlan(**plan.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)

    AdminManager.log_admin_action(db, admin_user.id, "CREATE_PLAN", db_plan.id)
    return db_plan


@router.get("/plans", response_model=List[billing_schema.ServicePlanResponse])
async def list_service_plans(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """List all available service plans."""
    return db.query(models.ServicePlan).all()


@router.get("/users/{user_identifier}/usage")
async def get_user_usage_report(
    user_identifier: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get detailed usage and transaction history for a user.
    user_identifier can be ID or Email.
    """
    if not AdminManager.has_permission(admin_user, "can_view_analytics"):
        raise HTTPException(status_code=403, detail="Permission denied")

    from sqlalchemy.orm import joinedload

    user = (
        db.query(models.User)
        .options(joinedload(models.User.wallet), joinedload(models.User.plan))
        .filter(
            (models.User.id == user_identifier) | (models.User.email == user_identifier)
        )
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    usage_logs = (
        db.query(models.UsageLog)
        .filter(models.UsageLog.user_id == user.id)
        .order_by(models.UsageLog.timestamp.desc())
        .limit(100)
        .all()
    )
    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.wallet_id == user.id)
        .order_by(models.Transaction.created_at.desc())
        .limit(100)
        .all()
    )

    return {
        "user_id": user.id,
        "email": user.email,
        "usage_stats": user.usage_stats,
        "wallet": {
            "balance": user.wallet.balance if user.wallet else 0,
            "currency": user.wallet.currency if user.wallet else "USD",
            "plan": user.plan.name if user.plan else "FREE",
        },
        "recent_usage": usage_logs,
        "recent_transactions": transactions,
    }


@router.patch("/users/{user_id}/plan")
async def update_user_plan(
    user_id: str,
    plan_id: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Assign a user to a specific billing plan."""
    if not AdminManager.has_permission(admin_user, "can_modify_system_settings"):
        raise HTTPException(status_code=403, detail="Permission denied")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    plan = db.query(models.ServicePlan).filter(models.ServicePlan.id == plan_id).first()

    if not user or not plan:
        raise HTTPException(status_code=404, detail="User or Plan not found")

    user.plan_id = plan_id
    db.commit()

    AdminManager.log_admin_action(
        db, admin_user.id, "UPDATE_USER_PLAN", user_id, {"new_plan": plan_id}
    )
    return {
        "status": "success",
        "message": f"User {user.email} moved to {plan.name} plan",
    }


# ==================== AUDIT LOGS ====================


@router.get("/audit-logs")
async def get_audit_logs(
    admin_id: Optional[str] = Query(None, description="Filter by admin ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[int] = Query(None, description="Start timestamp (ms)"),
    end_date: Optional[int] = Query(None, description="End timestamp (ms)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get audit logs of admin actions.

    Permission Required: can_view_analytics
    """
    if not AdminManager.has_permission(admin_user, "can_view_analytics"):
        raise HTTPException(status_code=403, detail="Permission denied")

    query = db.query(models.AdminActionLog)

    if admin_id:
        query = query.filter(models.AdminActionLog.admin_id == admin_id)
    if action:
        query = query.filter(models.AdminActionLog.action == action)
    if start_date:
        query = query.filter(models.AdminActionLog.timestamp >= start_date)
    if end_date:
        query = query.filter(models.AdminActionLog.timestamp <= end_date)

    total = query.count()
    logs = (
        query.order_by(models.AdminActionLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {"total": total, "offset": offset, "limit": limit, "logs": logs}


# ==================== B2B MANAGEMENT ====================

@router.post("/organizations", status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: dict,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    POST /organizations: Create a new B2B organization.
    Expects: {id, name, admin_user_id}
    """
    if not AdminManager.is_admin(admin_user):
         raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Create corporate wallet automatically
    wallet_id = f"wallet_{org_data['id']}"
    corporate_wallet = models.Wallet(
        user_id=wallet_id,
        balance=10000, # Initial credits for testing
        currency="USD"
    )
    db.add(corporate_wallet)

    new_org = models.Organization(
        id=org_data["id"],
        name=org_data["name"],
        admin_user_id=org_data.get("admin_user_id", admin_user.id),
        corporate_wallet_id=wallet_id
    )
    db.add(new_org)
    
    # Associate admin user with org
    target_user_id = org_data.get("admin_user_id", admin_user.id)
    target_user = db.query(models.User).filter(models.User.id == target_user_id).first()
    if target_user:
        target_user.org_id = new_org.id
        
    db.commit()
    db.refresh(new_org)
    return new_org

@router.post("/locations", status_code=status.HTTP_201_CREATED)
async def create_location(
    loc_data: dict,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    POST /locations: Add a work location for geofencing.
    Expects: {org_id, name, latitude, longitude, radius}
    """
    if not AdminManager.is_admin(admin_user):
         raise HTTPException(status_code=403, detail="Admin privileges required")
    
    new_loc = models.WorkLocation(
        id=str(__import__("uuid").uuid4()),
        org_id=loc_data["org_id"],
        name=loc_data["name"],
        latitude=loc_data["latitude"],
        longitude=loc_data["longitude"],
        radius=loc_data.get("radius", 100)
    )
    db.add(new_loc)
    db.commit()
    db.refresh(new_loc)
    return new_loc
@router.get("/organizations/{org_id}/balance")
async def get_org_balance(
    org_id: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """GET /organizations/{org_id}/balance: Check corporate wallet balance."""
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == org.corporate_wallet_id).first()
    return {
        "org_id": org.id,
        "wallet_id": org.corporate_wallet_id,
        "balance": wallet.balance if wallet else 0,
        "currency": wallet.currency if wallet else "USD"
    }
