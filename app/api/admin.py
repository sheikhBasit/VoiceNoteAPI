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
from app.schemas import user as user_schema
from app.schemas import system as system_schema
from app.utils.admin_utils import AdminManager
from app.utils.ai_service_utils import AIServiceError
from app.services.auth_service import create_access_token, verify_password, get_current_active_admin
from typing import List, Optional
import time

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login")
async def admin_login(
    login_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    POST /login: Authenticate admin and return JWT.
    """
    admin = db.query(models.User).filter(
        models.User.email == login_data.username,
        models.User.is_admin == True,
        models.User.is_deleted == False
    ).first()
    
    if not admin or not verify_password(login_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    access_token = create_access_token(data={"sub": admin.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_schema.UserResponse.model_validate(admin)
    }


# ==================== USER MANAGEMENT ====================

@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: str,
    level: str = Query("full", pattern="^(full|moderator|viewer)$"),
    admin_user: models.User = Depends(get_current_active_admin),
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Permission denied: Required permission 'can_manage_admins' is missing"
            )
        
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
    admin_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke admin role from user
    
    Permission Required: can_manage_admins
    """
    try:
        if not AdminManager.is_admin(admin_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Permission denied: Administrative privileges required"
            )
        
        if not AdminManager.has_permission(admin_user, "can_manage_admins"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Permission denied: Required permission 'can_manage_admins' is missing"
            )
        
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    List all users in system
    
    Permission Required: can_view_all_users
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_view_all_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_view_all_users' is missing"
        )
    
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
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    Get statistics about all users
    
    Permission Required: can_view_analytics
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_view_analytics' is missing"
        )
    
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    View all notes across all users
    
    Permission Required: can_view_all_notes
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_view_all_notes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_view_all_notes' is missing"
        )
    
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
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    Delete note as admin (content moderation)
    
    Permission Required: can_delete_notes
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_delete_notes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_delete_notes' is missing"
        )
    
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Note with ID '{note_id}' not found"
        )
    
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
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    Delete user account as admin
    
    Permission Required: can_delete_users
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_delete_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_delete_users' is missing"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID '{user_id}' not found"
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
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
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
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_manage_admins' is missing"
        )
    
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
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    List all admin users
    
    Permission Required: can_manage_admins
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_manage_admins' is missing"
        )
    
    admins = db.query(models.User).filter(models.User.is_admin == True).all()
    
    return {
        "total": len(admins),
        "admins": admins
    }


# ==================== SYSTEM INFO ====================

@router.get("/status")
async def get_admin_panel_status(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    Get admin panel status and system information
    
    Permission Required: is_admin
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    return {
        "status": "operational",
        "admin_id": admin_user.id,
        "admin_name": admin_user.name,
        "permissions": admin_user.admin_permissions,
        "last_action": admin_user.admin_last_action,
        "created_at": admin_user.admin_created_at,
        "timestamp": int(time.time() * 1000)
    }


# ==================== SYSTEM SETTINGS ====================

@router.get("/settings/ai", response_model=system_schema.AISettingsResponse)
async def get_ai_settings(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    GET /settings/ai: Retrieve global AI parameters.
    Permission Required: is_admin
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
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
    admin_user: models.User = Depends(get_current_active_admin)
):
    """
    PATCH /settings/ai: Update global AI parameters.
    Permission Required: can_modify_system_settings
    """
    if not AdminManager.is_admin(admin_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_modify_system_settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_modify_system_settings' is missing"
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
        details=update_data
    )
    
    return settings
