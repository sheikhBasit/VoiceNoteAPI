"""
Admin API Endpoints

Provides endpoints for:
- User management
- Content moderation
- Analytics & reporting
- System settings
- Permission management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from app.schemas import user_schema
from app.utils.admin_utils import AdminManager, verify_admin, verify_permission
from app.utils.ai_service_utils import AIServiceError
from typing import List, Optional
import time

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ==================== USER MANAGEMENT ====================

@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: str,
    level: str = Query("full", regex="^(full|moderator|viewer)$"),
    admin_user: models.User = Depends(lambda user_id: verify_admin(user_id, Depends(get_db))),
    db: Session = Depends(get_db)
):
    """
    Promote user to admin role
    
    Permission Required: can_manage_admins
    
    Args:
        user_id: User to promote
        level: Permission level ("full", "moderator", "viewer")
    
    Returns:
        Updated user with admin role
    """
    try:
        if not AdminManager.has_permission(admin_user, "can_manage_admins"):
            raise HTTPException(status_code=403, detail="can_manage_admins permission required")
        
        updated_user = AdminManager.grant_admin_role(
            db=db,
            user_id=user_id,
            granted_by=admin_user.id,
            permission_level=level
        )
        
        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="MAKE_ADMIN",
            target_id=user_id,
            details={"level": level}
        )
        
        return {
            "status": "success",
            "message": f"User promoted to {level} admin",
            "user": updated_user
        }
    except AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/remove-admin")
async def remove_user_admin(
    user_id: str,
    current_admin_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Revoke admin role from user
    
    Permission Required: can_manage_admins
    """
    try:
        admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
        if not admin_user or not AdminManager.is_admin(admin_user):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not AdminManager.has_permission(admin_user, "can_manage_admins"):
            raise HTTPException(status_code=403, detail="can_manage_admins permission required")
        
        updated_user = AdminManager.revoke_admin_role(db=db, user_id=user_id)
        
        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="REMOVE_ADMIN",
            target_id=user_id
        )
        
        return {
            "status": "success",
            "message": "Admin role revoked",
            "user": updated_user
        }
    except AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users")
async def list_all_users(
    current_admin_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all users in system
    
    Permission Required: can_view_all_users
    """
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AdminManager.has_permission(admin_user, "can_view_all_users"):
        raise HTTPException(status_code=403, detail="can_view_all_users permission required")
    
    users = db.query(models.User).offset(skip).limit(limit).all()
    total = db.query(models.User).count()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": users
    }


@router.get("/users/stats")
async def get_user_statistics(
    current_admin_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get statistics about all users
    
    Permission Required: can_view_analytics
    """
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AdminManager.has_permission(admin_user, "can_view_analytics"):
        raise HTTPException(status_code=403, detail="can_view_analytics permission required")
    
    total_users = db.query(models.User).count()
    admin_count = db.query(models.User).filter(models.User.is_admin == True).count()
    active_users = db.query(models.User).filter(
        models.User.is_deleted == False
    ).count()
    
    return {
        "total_users": total_users,
        "admin_count": admin_count,
        "active_users": active_users,
        "deleted_users": total_users - active_users,
        "timestamp": int(time.time() * 1000)
    }


# ==================== CONTENT MODERATION ====================

@router.get("/notes")
async def list_all_notes(
    current_admin_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    View all notes across all users
    
    Permission Required: can_view_all_notes
    """
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AdminManager.has_permission(admin_user, "can_view_all_notes"):
        raise HTTPException(status_code=403, detail="can_view_all_notes permission required")
    
    notes = db.query(models.Note).offset(skip).limit(limit).all()
    total = db.query(models.Note).count()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "notes": notes
    }


@router.delete("/notes/{note_id}")
async def delete_note_as_admin(
    note_id: str,
    current_admin_id: str = Query(...),
    reason: str = Query(""),
    db: Session = Depends(get_db)
):
    """
    Delete note as admin (content moderation)
    
    Permission Required: can_delete_notes
    """
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AdminManager.has_permission(admin_user, "can_delete_notes"):
        raise HTTPException(status_code=403, detail="can_delete_notes permission required")
    
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note.is_deleted = True
    note.deleted_at = int(time.time() * 1000)
    db.commit()
    
    AdminManager.log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="DELETE_NOTE",
        target_id=note_id,
        details={"reason": reason}
    )
    
    return {
        "status": "success",
        "message": "Note deleted",
        "note_id": note_id
    }


@router.delete("/users/{user_id}")
async def delete_user_as_admin(
    user_id: str,
    current_admin_id: str = Query(...),
    reason: str = Query(""),
    db: Session = Depends(get_db)
):
    """
    Delete user account as admin
    
    Permission Required: can_delete_users
    """
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AdminManager.has_permission(admin_user, "can_delete_users"):
        raise HTTPException(status_code=403, detail="can_delete_users permission required")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
        details={"reason": reason}
    )
    
    return {
        "status": "success",
        "message": "User deleted",
        "user_id": user_id
    }


# ==================== PERMISSION MANAGEMENT ====================

@router.put("/permissions/{user_id}")
async def update_admin_permissions(
    user_id: str,
    permissions: dict,
    current_admin_id: str = Query(...),
    db: Session = Depends(get_db)
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
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(status_code=403, detail="can_manage_admins permission required")
    
    try:
        updated_user = AdminManager.update_permissions(
            db=db,
            user_id=user_id,
            permissions=permissions
        )
        
        AdminManager.log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="UPDATE_PERMISSIONS",
            target_id=user_id,
            details={"permissions": permissions}
        )
        
        return {
            "status": "success",
            "message": "Permissions updated",
            "user": updated_user
        }
    except AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admins")
async def list_all_admins(
    current_admin_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    List all admin users
    
    Permission Required: can_manage_admins
    """
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(status_code=403, detail="can_manage_admins permission required")
    
    admins = db.query(models.User).filter(models.User.is_admin == True).all()
    
    return {
        "total": len(admins),
        "admins": admins
    }


# ==================== SYSTEM INFO ====================

@router.get("/status")
async def get_admin_panel_status(
    current_admin_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get admin panel status and system information
    
    Permission Required: is_admin
    """
    admin_user = db.query(models.User).filter(models.User.id == current_admin_id).first()
    if not admin_user or not AdminManager.is_admin(admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "status": "operational",
        "admin_id": admin_user.id,
        "admin_name": admin_user.name,
        "permissions": admin_user.admin_permissions,
        "last_action": admin_user.admin_last_action,
        "created_at": admin_user.admin_created_at,
        "timestamp": int(time.time() * 1000)
    }
