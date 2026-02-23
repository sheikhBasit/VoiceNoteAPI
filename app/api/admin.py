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

    query = db.query(models.User).filter(models.User.is_deleted == False)
    total = query.count()
    users = (
        query.options(joinedload(models.User.wallet), joinedload(models.User.plan))
        .offset(skip)
        .limit(limit)
        .all()
    )

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

    from sqlalchemy import func, case
    stats = db.query(
        func.count(models.User.id).label("total"),
        func.sum(case((models.User.is_deleted == False, 1), else_=0)).label("active"),
        func.sum(case((models.User.is_admin == True, 1), else_=0)).label("admin"),
        func.sum(case((models.User.is_deleted == True, 1), else_=0)).label("deleted")
    ).first()

    return {
        "total_users": stats.active or 0, # Based on H-07 requirement to focus on active
        "admin_count": stats.admin or 0,
        "active_users": stats.active or 0,
        "deleted_users": stats.deleted or 0,
        "timestamp": int(time.time() * 1000),
    }


# ==================== CONTENT MODERATION ====================


from app.schemas import note as note_schema
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class AdminNoteListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    notes: List[dict]


@router.get("/notes")
async def list_all_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    View all notes across all users
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

    try:
        notes_query = db.query(models.Note).filter(models.Note.is_deleted == False)
        total = notes_query.count()
        notes = notes_query.offset(skip).limit(limit).all()
    except Exception as e:
        JLogger.error(f"DB QUERY ERROR in list_all_notes: {e}", traceback=True)
        raise HTTPException(status_code=500, detail=f"Database Query Error: {str(e)}")
    
    # Manual serialization to avoid Pydantic/SQLAlchemy issues
    serialized_notes = []
    try:
        for n in notes:
            serialized_notes.append({
                "id": str(n.id),
                "title": str(n.title or "Untitled"),
                "user_id": str(n.user_id) if n.user_id else None,
                "timestamp": int(n.timestamp) if n.timestamp is not None else 0,
                "summary": str(n.summary or ""),
                "is_deleted": bool(n.is_deleted),
                "is_pinned": bool(n.is_pinned),
                "is_archived": bool(n.is_archived)
            })
    except Exception as e:
        JLogger.error(f"SERIALIZATION ERROR in list_all_notes: {e}", traceback=True)
        raise HTTPException(status_code=500, detail=f"Serialization Error: {str(e)}")
    
    return {"total": total, "skip": skip, "limit": limit, "notes": serialized_notes}


@router.get("/notes/audit")
async def list_note_audit_logs(
    note_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    View audit logs specifically for notes
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

    from app.services.admin_audit_service import AdminAuditService

    # If note_id is provided, filter specifically for that note
    # Otherwise, get all note-related actions
    action_filter = None
    if not note_id:
        # Generic note actions filter - this is a bit of a stretch for the service but we can filter by action prefix
        pass

    logs = AdminAuditService.get_audit_logs(
        db=db,
        action=None,  # Service doesn't support prefix filtering yet, but we'll return all for now or filter manually
        limit=limit,
        skip=skip
    )
    
    # Simple manual filter for note actions if note_id not specified
    if not note_id:
        note_actions = ["CREATE_NOTE", "UPDATE_NOTE", "DELETE_NOTE", "RESTORE_NOTE", "VIEW_NOTE"]
        # logs["logs"] is a list of dicts — use dict access, not attribute access
        raw_logs = logs.get("logs", []) if isinstance(logs, dict) else []
        filtered_logs = [
            log for log in raw_logs
            if (log.get("action") if isinstance(log, dict) else getattr(log, "action", None)) in note_actions
        ]
        return {
            "total": len(filtered_logs),
            "skip": skip,
            "limit": limit,
            "logs": filtered_logs
        }

    return logs


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
                "admin_created_at": user.admin_created_at,
                "admin_last_action": user.admin_last_action,
                "last_login": user.last_login,
            },
            "subscription": {
                "plan": user.plan.name if user.plan else "NONE",
                "tier": user.tier.value if user.tier else "GUEST",
                "balance": user.wallet.balance if user.wallet else 0,
                "monthly_limit": getattr(user.wallet, "monthly_limit", 0) if user.wallet else 0,
                "used_this_month": getattr(user.wallet, "used_this_month", 0) if user.wallet else 0,
                "is_frozen": user.wallet.is_frozen if user.wallet else False,
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
    """List all available service plans (including inactive)."""
    return db.query(models.ServicePlan).all()


@router.patch("/plans/{plan_id}", response_model=billing_schema.ServicePlanResponse)
async def update_service_plan(
    plan_id: str,
    updates: billing_schema.ServicePlanUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Update an existing service plan."""
    if not AdminManager.has_permission(admin_user, "can_modify_system_settings"):
        raise HTTPException(status_code=403, detail="Permission denied")

    plan = db.query(models.ServicePlan).filter(models.ServicePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    plan.updated_at = int(time.time() * 1000)

    db.commit()
    db.refresh(plan)

    AdminManager.log_admin_action(
        db, admin_user.id, "UPDATE_PLAN", plan_id, update_data
    )
    return plan


@router.delete("/plans/{plan_id}")
async def delete_service_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """Soft-delete a service plan (sets is_active=False)."""
    if not AdminManager.has_permission(admin_user, "can_modify_system_settings"):
        raise HTTPException(status_code=403, detail="Permission denied")

    plan = db.query(models.ServicePlan).filter(models.ServicePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_active = False
    plan.updated_at = int(time.time() * 1000)
    db.commit()

    AdminManager.log_admin_action(db, admin_user.id, "DELETE_PLAN", plan_id)
    return {"status": "success", "message": f"Plan '{plan.name}' deactivated"}


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

from pydantic import BaseModel, Field
from typing import Optional as OptionalType

class CreateOrganizationRequest(BaseModel):
    id: str
    name: str
    admin_user_id: OptionalType[str] = None

class CreateLocationRequest(BaseModel):
    org_id: str
    name: str
    latitude: float
    longitude: float
    radius: float = Field(default=100, ge=1)


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: CreateOrganizationRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    POST /organizations: Create a new B2B organization.
    """
    if not AdminManager.is_admin(admin_user):
         raise HTTPException(status_code=403, detail="Admin privileges required")

    # Create corporate wallet automatically
    wallet_id = f"wallet_{org_data.id}"
    corporate_wallet = models.Wallet(
        user_id=wallet_id,
        balance=10000,
        currency="USD"
    )
    db.add(corporate_wallet)

    new_org = models.Organization(
        id=org_data.id,
        name=org_data.name,
        admin_user_id=org_data.admin_user_id or admin_user.id,
        corporate_wallet_id=wallet_id
    )
    db.add(new_org)

    # Associate admin user with org
    target_user_id = org_data.admin_user_id or admin_user.id
    target_user = db.query(models.User).filter(models.User.id == target_user_id).first()
    if target_user:
        target_user.org_id = new_org.id

    db.commit()
    db.refresh(new_org)
    return new_org

@router.post("/locations", status_code=status.HTTP_201_CREATED)
async def create_location(
    loc_data: CreateLocationRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    POST /locations: Add a work location for geofencing.
    """
    if not AdminManager.is_admin(admin_user):
         raise HTTPException(status_code=403, detail="Admin privileges required")

    import uuid
    new_loc = models.WorkLocation(
        id=str(uuid.uuid4()),
        org_id=loc_data.org_id,
        name=loc_data.name,
        latitude=loc_data.latitude,
        longitude=loc_data.longitude,
        radius=loc_data.radius
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

# ============================================================================
# PHASE 1: CRITICAL ADMIN ENDPOINTS (NEW)
# ============================================================================


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get dashboard overview with all key metrics
    
    **Authorization:** Admin only
    
    Returns:
        Dashboard metrics including users, content, activity, system health, revenue, and recent admin activity
    """
    from app.services.metrics_service import MetricsService
    from app.services.admin_audit_service import AdminAuditService
    
    overview = MetricsService.get_dashboard_overview(db)
    
    # Add recent activity logs
    recent_activity = AdminAuditService.get_recent_activity(db, hours=24, limit=10)
    overview["recent_activity"] = recent_activity["recent_activity"]
    
    # Log admin action
    AdminManager.log_admin_action(
        db, admin_user.id, "VIEW_DASHBOARD", None,
        details={"action": "viewed dashboard overview"}
    )
    
    return overview



@router.get("/metrics/realtime")
async def get_realtime_metrics(
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get real-time system metrics
    
    **Authorization:** Admin only
    
    Returns:
        Real-time metrics including users online, API RPM, processing status, error rates
    """
    from app.services.metrics_service import MetricsService
    
    return MetricsService.get_realtime_metrics(db)


@router.get("/system/health")
async def get_system_health(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get system health status
    
    **Authorization:** Admin only
    
    Returns:
        Health status of database, Redis, Celery, and disk
    """
    from app.services.system_health_service import SystemHealthService
    
    return SystemHealthService.get_overall_health()


@router.get("/tasks")
async def list_admin_tasks(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    List all tasks (admin view)
    
    **Authorization:** Admin only
    
    Args:
        limit: Number of tasks to return (1-100)
        skip: Number of tasks to skip
        user_id: Filter by user ID
        status: Filter by task status
    
    Returns:
        List of tasks with total count
    """
    query = db.query(models.Task)
    
    if user_id:
        query = query.filter(models.Task.user_id == user_id)
    
    if status:
        query = query.filter(models.Task.status == status)
    
    # Order by created_at descending
    query = query.order_by(models.Task.created_at.desc())
    
    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "tasks": tasks,
        "limit": limit,
        "skip": skip
    }


@router.delete("/tasks/{task_id}")
async def delete_admin_task(
    task_id: str,
    reason: str = Query("", description="Reason for deletion"),
    hard: bool = Query(False, description="Hard delete (permanent)"),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a task (admin override)
    
    **Authorization:** Admin only
    
    Args:
        task_id: Task ID to delete
        reason: Reason for deletion
        hard: If True, permanently delete; if False, soft delete
    
    Returns:
        Deletion result
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if hard:
        # Hard delete - permanently remove
        db.delete(task)
        db.commit()
        result = {"deleted": True, "permanent": True}
    else:
        # Soft delete using DeletionService
        from app.services.deletion_service import DeletionService
        result = DeletionService.soft_delete_task(db, task_id, admin_user.id, reason)
    
    # Log admin action
    AdminManager.log_admin_action(
        db, admin_user.id, "DELETE_TASK",
        target_id=task_id,
        details={"reason": reason, "hard": hard}
    )
    
    return {"status": "success", "result": result}


@router.patch("/tasks/{task_id}/restore")
async def restore_admin_task(
    task_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Restore a soft-deleted task
    
    **Authorization:** Admin only
    
    Args:
        task_id: Task ID to restore
    
    Returns:
        Restoration result
    """
    from app.services.deletion_service import DeletionService
    
    result = DeletionService.restore_task(db, task_id, admin_user.id)
    
    AdminManager.log_admin_action(
        db, admin_user.id, "RESTORE_TASK",
        target_id=task_id
    )
    
    return {"status": "success", "result": result}


@router.post("/notes/create")
async def create_test_note(
    user_id: str,
    title: str = "Test Note",
    summary: str = "",
    transcript_groq: str = "",
    priority: str = "MEDIUM",
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Create a test note from dashboard
    
    **Authorization:** Admin only
    
    Args:
        user_id: User ID to create note for
        title: Note title
        summary: Note summary
        transcript_groq: Transcript text
        priority: Note priority (LOW, MEDIUM, HIGH)
    
    Returns:
        Created note
    """
    import uuid
    
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create note
    note = models.Note(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        summary=summary,
        transcript_groq=transcript_groq,
        priority=models.Priority[priority],
        timestamp=int(time.time() * 1000),
        updated_at=int(time.time() * 1000),
        languages=["en"]
    )
    
    db.add(note)
    db.commit()
    db.refresh(note)
    
    AdminManager.log_admin_action(
        db, admin_user.id, "CREATE_TEST_NOTE",
        target_id=note.id,
        details={"user_id": user_id, "title": title}
    )
    
    return {"status": "success", "note": note}


# ============================================================================
# PHASE 2: OPERATIONS ENDPOINTS (NEW)
# ============================================================================


@router.get("/api-keys")
async def list_api_keys(
    service_name: Optional[str] = None,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    List all API keys
    
    **Authorization:** Admin only
    
    Args:
        service_name: Optional filter by service (groq, deepgram, openai, anthropic)
    
    Returns:
        List of API keys (masked for security)
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    return AdminOperationsService.list_api_keys(db, service_name)


@router.post("/api-keys")
async def create_api_key(
    service_name: str,
    api_key: str,
    priority: int = 1,
    is_active: bool = True,
    notes: Optional[str] = None,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new API key
    
    **Authorization:** Admin only
    
    Args:
        service_name: Service name (groq, deepgram, openai, anthropic)
        api_key: The API key
        priority: Priority (lower = higher priority)
        is_active: Whether the key is active
        notes: Optional notes
    
    Returns:
        Created key info
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    try:
        result = AdminOperationsService.create_api_key(
            db, service_name, api_key, priority, is_active, notes
        )
        
        AdminManager.log_admin_action(db, admin_user.id, "CREATE_API_KEY", None, details={"service": service_name}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/api-keys/{key_id}")
async def update_api_key(
    key_id: str,
    priority: Optional[int] = None,
    is_active: Optional[bool] = None,
    notes: Optional[str] = None,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Update an API key
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    try:
        result = AdminOperationsService.update_api_key(
            db, key_id, priority, is_active, notes
        )
        
        AdminManager.log_admin_action(
            db, admin_user.id, "UPDATE_API_KEY",
            target_id=key_id
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Delete an API key
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    try:
        result = AdminOperationsService.delete_api_key(db, key_id)
        
        AdminManager.log_admin_action(
            db, admin_user.id, "DELETE_API_KEY",
            target_id=key_id
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api-keys/health")
async def get_api_key_health(
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get health status of all API keys
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    return AdminOperationsService.get_api_key_health(db)


@router.post("/bulk/delete")
async def bulk_delete_items(
    item_type: str,
    ids: str,  # Comma-separated IDs
    reason: str,
    hard: bool = False,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Bulk delete items
    
    **Authorization:** Admin only
    
    Args:
        item_type: Type of items (notes, tasks, users)
        ids: Comma-separated list of item IDs to delete
        reason: Reason for deletion
        hard: If True, permanently delete; if False, soft delete
    
    Returns:
        Deletion result with count
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    # Split comma-separated IDs
    id_list = [id.strip() for id in ids.split(',') if id.strip()]

    if len(id_list) > 100:
        raise HTTPException(status_code=400, detail="Max 100 items per bulk operation")

    try:
        result = AdminOperationsService.bulk_delete(
            db, item_type, id_list, admin_user.id, reason, hard
        )
        
        AdminManager.log_admin_action(db, admin_user.id, "BULK_DELETE", None, details={"type": item_type, "count": len(id_list), "hard": hard}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk/restore")
async def bulk_restore_items(
    item_type: str,
    ids: str,  # Comma-separated IDs
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Bulk restore soft-deleted items
    
    **Authorization:** Admin only
    
    Args:
        item_type: Type of items (notes, tasks, users)
        ids: Comma-separated list of item IDs to restore
    
    Returns:
        Restoration result with count
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    # Split comma-separated IDs
    id_list = [id.strip() for id in ids.split(',') if id.strip()]

    if len(id_list) > 100:
        raise HTTPException(status_code=400, detail="Max 100 items per bulk operation")

    try:
        result = AdminOperationsService.bulk_restore(
            db, item_type, id_list, admin_user.id
        )
        
        AdminManager.log_admin_action(db, admin_user.id, "BULK_RESTORE", None, details={"type": item_type, "count": len(id_list)}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/wallets")
async def list_wallets(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    is_frozen: Optional[bool] = None,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    List all wallets
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    return AdminOperationsService.list_wallets(db, limit, skip, is_frozen)


@router.post("/wallets/{user_id}/credit")
async def credit_wallet(
    user_id: str,
    amount: int,
    reason: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Credit a user's wallet
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    try:
        result = AdminOperationsService.credit_wallet(
            db, user_id, amount, admin_user.id, reason
        )
        
        AdminManager.log_admin_action(
            db, admin_user.id, "CREDIT_WALLET",
            target_id=user_id,
            details={"amount": amount, "reason": reason}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/wallets/{user_id}/debit")
async def debit_wallet(
    user_id: str,
    amount: int,
    reason: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Debit a user's wallet
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    try:
        result = AdminOperationsService.debit_wallet(
            db, user_id, amount, admin_user.id, reason
        )
        
        AdminManager.log_admin_action(
            db, admin_user.id, "DEBIT_WALLET",
            target_id=user_id,
            details={"amount": amount, "reason": reason}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wallets/{user_id}/freeze")
async def freeze_wallet(
    user_id: str,
    reason: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Freeze a user's wallet
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    try:
        result = AdminOperationsService.freeze_wallet(
            db, user_id, admin_user.id, reason
        )
        
        AdminManager.log_admin_action(
            db, admin_user.id, "FREEZE_WALLET",
            target_id=user_id,
            details={"reason": reason}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/wallets/{user_id}/unfreeze")
async def unfreeze_wallet(
    user_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Unfreeze a user's wallet
    
    **Authorization:** Admin only
    """
    from app.services.admin_operations_service import AdminOperationsService
    
    try:
        result = AdminOperationsService.unfreeze_wallet(
            db, user_id, admin_user.id
        )
        
        AdminManager.log_admin_action(
            db, admin_user.id, "UNFREEZE_WALLET",
            target_id=user_id
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# PHASE 3: ANALYTICS ENDPOINTS (NEW)
# ============================================================================


@router.get("/analytics/usage")
async def get_usage_analytics(
    start_date: int = Query(..., description="Start timestamp (ms)"),
    end_date: int = Query(..., description="End timestamp (ms)"),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get usage analytics for date range
    
    **Authorization:** Admin only
    
    Args:
        start_date: Start timestamp in milliseconds
        end_date: End timestamp in milliseconds
        group_by: Group by day, week, or month
    
    Returns:
        Usage analytics including audio minutes, API calls, notes, tasks, active users
    """
    from app.services.admin_analytics_service import AdminAnalyticsService
    try:
        return AdminAnalyticsService.get_usage_analytics(db, start_date, end_date, group_by)
    except Exception as e:
        JLogger.error("Usage analytics failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@router.get("/analytics/growth")
async def get_growth_analytics(
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get growth trends and metrics
    
    **Authorization:** Admin only
    
    Returns:
        Growth analytics including signups, tier distribution, retention, churn
    """
    from app.services.admin_analytics_service import AdminAnalyticsService
    
    return AdminAnalyticsService.get_growth_analytics(db)


@router.post("/wallets/{user_id}/toggle-freeze")
async def toggle_wallet_freeze(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_admin),
):
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    wallet.is_frozen = not wallet.is_frozen
    db.commit()
    return {"is_frozen": wallet.is_frozen}


@router.get("/reports/revenue")
async def get_revenue_report(
    start_date: int = Query(..., description="Start timestamp (ms)"),
    end_date: int = Query(..., description="End timestamp (ms)"),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get revenue report for date range
    
    **Authorization:** Admin only
    
    Args:
        start_date: Start timestamp in milliseconds
        end_date: End timestamp in milliseconds
    
    Returns:
        Revenue report including total revenue, expenses, net revenue, ARPU
    """
    from app.services.admin_analytics_service import AdminAnalyticsService
    
    return AdminAnalyticsService.get_revenue_report(db, start_date, end_date)


@router.get("/analytics/user-behavior")
async def get_user_behavior_analytics(
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get user behavior insights
    
    **Authorization:** Admin only
    
    Returns:
        User behavior analytics including top users, averages, peak hours, feature usage
    """
    from app.services.admin_analytics_service import AdminAnalyticsService
    try:
        return AdminAnalyticsService.get_user_behavior_analytics(db)
    except Exception as e:
        JLogger.error("User behavior analytics failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@router.get("/analytics/system-metrics")
async def get_system_metrics(
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get overall system metrics
    
    **Authorization:** Admin only
    
    Returns:
        System metrics including storage usage and database statistics
    """
    from app.services.admin_analytics_service import AdminAnalyticsService
    
    return AdminAnalyticsService.get_system_metrics(db)


# ============================================================================
# PHASE 4: CELERY & JOBS ENDPOINTS (NEW)
# ============================================================================


@router.get("/celery/tasks/active")
async def get_active_celery_tasks(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get all currently active Celery tasks
    
    **Authorization:** Admin only
    
    Returns:
        List of active tasks with worker info
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    return CeleryMonitorService.get_active_tasks()


@router.get("/celery/tasks/pending")
async def get_pending_celery_tasks(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get all pending Celery tasks
    
    **Authorization:** Admin only
    
    Returns:
        List of pending/scheduled tasks
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    return CeleryMonitorService.get_pending_tasks()


@router.get("/celery/tasks/{task_id}/status")
async def get_celery_task_status(
    task_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get status of a specific Celery task
    
    **Authorization:** Admin only
    
    Args:
        task_id: Celery task ID
    
    Returns:
        Task status, state, result
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    return CeleryMonitorService.get_task_status(task_id)


@router.post("/celery/tasks/{task_id}/retry")
async def retry_celery_task(
    task_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retry a failed Celery task
    
    **Authorization:** Admin only
    
    Args:
        task_id: Celery task ID to retry
    
    Returns:
        Retry result
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    result = CeleryMonitorService.retry_task(task_id)
    
    AdminManager.log_admin_action(
        db, admin_user.id, "RETRY_CELERY_TASK",
        target_id=task_id
    )
    
    return result


@router.post("/celery/tasks/{task_id}/cancel")
async def cancel_celery_task(
    task_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Cancel a pending or running Celery task
    
    **Authorization:** Admin only
    
    Args:
        task_id: Celery task ID to cancel
    
    Returns:
        Cancellation result
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    result = CeleryMonitorService.cancel_task(task_id)
    
    AdminManager.log_admin_action(
        db, admin_user.id, "CANCEL_CELERY_TASK",
        target_id=task_id
    )
    
    return result


@router.get("/celery/workers/stats")
async def get_worker_stats(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get statistics for all Celery workers
    
    **Authorization:** Admin only
    
    Returns:
        Worker stats including pool info, concurrency, processes
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    return CeleryMonitorService.get_worker_stats()


@router.get("/celery/workers/tasks")
async def get_registered_tasks(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get all registered Celery tasks
    
    **Authorization:** Admin only
    
    Returns:
        List of registered task names
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    return CeleryMonitorService.get_registered_tasks()


@router.post("/celery/workers/{worker_name}/shutdown")
async def shutdown_worker(
    worker_name: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Shutdown a specific Celery worker
    
    **Authorization:** Admin only
    
    Args:
        worker_name: Name of worker to shutdown
    
    Returns:
        Shutdown result
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    result = CeleryMonitorService.shutdown_worker(worker_name)
    
    AdminManager.log_admin_action(db, admin_user.id, "SHUTDOWN_WORKER", None, details={"worker": worker_name}
    )
    
    return result


@router.post("/celery/workers/pool-restart")
async def restart_worker_pool(
    worker_name: Optional[str] = None,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Restart worker pool
    
    **Authorization:** Admin only
    
    Args:
        worker_name: Optional specific worker to restart (all if not provided)
    
    Returns:
        Restart result
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    result = CeleryMonitorService.pool_restart(worker_name)
    
    AdminManager.log_admin_action(db, admin_user.id, "RESTART_WORKER_POOL", None, details={"worker": worker_name or "all"}
    )
    
    return result


@router.get("/celery/queues")
async def get_queue_info(
    admin_user: models.User = Depends(get_current_active_admin),
):
    """
    Get information about all Celery queues
    
    **Authorization:** Admin only
    
    Returns:
        Queue information including workers and routing
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    return CeleryMonitorService.get_queue_lengths()


@router.post("/celery/queues/{queue_name}/purge")
async def purge_queue(
    queue_name: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Purge all tasks from a queue
    
    **Authorization:** Admin only
    
    Args:
        queue_name: Name of queue to purge
    
    Returns:
        Purge result
    """
    from app.services.celery_monitor_service import CeleryMonitorService
    
    result = CeleryMonitorService.purge_queue(queue_name)
    
    AdminManager.log_admin_action(db, admin_user.id, "PURGE_QUEUE", None, details={"queue": queue_name}
    )
    
    return result


# ============================================================================
# PHASE 5: USER MANAGEMENT ENDPOINTS (NEW)
# ============================================================================


@router.get("/users/search")
async def search_users(
    query: Optional[str] = None,
    tier: Optional[str] = None,
    is_admin: Optional[bool] = None,
    is_deleted: Optional[bool] = False,
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Search and filter users
    
    **Authorization:** Admin only
    
    Args:
        query: Search by name or email
        tier: Filter by subscription tier
        is_admin: Filter by admin status
        is_deleted: Filter by deleted status
        limit: Results per page
        skip: Results to skip
    
    Returns:
        Filtered user list with pagination
    """
    from app.services.admin_user_management_service import AdminUserManagementService
    
    return AdminUserManagementService.search_users(
        db, query, tier, is_admin, is_deleted, limit, skip
    )


@router.get("/users/{user_id}/detail")
async def get_user_detail(
    user_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get detailed user information
    
    **Authorization:** Admin only
    
    Args:
        user_id: User ID to get details for
    
    Returns:
        User details with statistics
    """
    from app.services.admin_user_management_service import AdminUserManagementService
    
    try:
        return AdminUserManagementService.get_user_detail(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/users/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    new_tier: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Update user's subscription tier
    
    **Authorization:** Admin only
    
    Args:
        user_id: User ID to update
        new_tier: New subscription tier
    
    Returns:
        Update result
    """
    from app.services.admin_user_management_service import AdminUserManagementService
    
    try:
        result = AdminUserManagementService.update_user_tier(
            db, user_id, new_tier, admin_user.id
        )
        
        AdminManager.log_admin_action(
            db, admin_user.id, "UPDATE_USER_TIER",
            target_id=user_id,
            details={"new_tier": new_tier}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get all active sessions for a user
    
    **Authorization:** Admin only
    
    Args:
        user_id: User ID to get sessions for
    
    Returns:
        List of active sessions
    """
    from app.services.admin_user_management_service import AdminUserManagementService
    
    return AdminUserManagementService.get_user_sessions(db, user_id)


@router.post("/users/{user_id}/force-logout")
async def force_logout_user(
    user_id: str,
    session_id: Optional[str] = None,
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Force logout user by revoking sessions
    
    **Authorization:** Admin only
    
    Args:
        user_id: User ID to logout
        session_id: Optional specific session to revoke (all if None)
    
    Returns:
        Logout result with sessions revoked count
    """
    from app.services.admin_user_management_service import AdminUserManagementService
    
    try:
        result = AdminUserManagementService.force_logout(
            db, user_id, admin_user.id, session_id
        )
        
        AdminManager.log_admin_action(
            db, admin_user.id, "FORCE_LOGOUT",
            target_id=user_id,
            details={"session_id": session_id}
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get user activity for the last N days
    
    **Authorization:** Admin only
    
    Args:
        user_id: User ID to get activity for
        days: Number of days to look back (1-365)
    
    Returns:
        User activity statistics
    """
    from app.services.admin_user_management_service import AdminUserManagementService
    
    return AdminUserManagementService.get_user_activity(db, user_id, days)


# ============================================================================
# AUDIT & ACTIVITY LOG ENDPOINTS (ENHANCED)
# ============================================================================


@router.get("/activity/recent")
async def get_recent_activity(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get recent admin activity for dashboard
    
    **Authorization:** Admin only
    
    Args:
        hours: Number of hours to look back (1-168)
        limit: Maximum activities to return (1-100)
    
    Returns:
        Recent activity feed with human-readable messages
    """
    from app.services.admin_audit_service import AdminAuditService
    
    return AdminAuditService.get_recent_activity(db, hours, limit)


@router.get("/activity/stats")
async def get_admin_action_stats(
    days: int = Query(30, ge=1, le=365),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get statistics on admin actions
    
    **Authorization:** Admin only
    
    Args:
        days: Number of days to analyze (1-365)
    
    Returns:
        Admin action statistics including counts by action type and top admins
    """
    from app.services.admin_audit_service import AdminAuditService
    
    return AdminAuditService.get_admin_action_stats(db, days)


@router.get("/activity/timeline")
async def get_activity_timeline(
    days: int = Query(7, ge=1, le=30),
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Get activity timeline for visualization
    
    **Authorization:** Admin only
    
    Args:
        days: Number of days to include (1-30)
    
    Returns:
        Activity timeline grouped by hour
    """
    from app.services.admin_audit_service import AdminAuditService
    
    return AdminAuditService.get_activity_timeline(db, days)
