"""
Admin Role & Permissions Management Utilities

Provides:
- Admin permission verification
- Role-based access control (RBAC)
- Admin action logging
- Permission sets
"""

import time
from typing import Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.utils.ai_service_utils import AIServiceError

# Predefined permission sets
DEFAULT_ADMIN_PERMISSIONS = {
    "can_view_all_users": True,
    "can_delete_users": True,
    "can_view_all_notes": True,
    "can_delete_notes": True,
    "can_manage_admins": True,
    "can_view_analytics": True,
    "can_modify_system_settings": True,
    "can_moderate_content": True,
    "can_manage_roles": True,
    "can_export_data": True,
}

MODERATOR_PERMISSIONS = {
    "can_view_all_notes": True,
    "can_moderate_content": True,
    "can_delete_notes": True,
}

VIEWER_PERMISSIONS = {
    "can_view_all_users": True,
    "can_view_all_notes": True,
    "can_view_analytics": True,
}


class AdminManager:
    """Manages admin roles and permissions"""

    @staticmethod
    def is_admin(user: models.User) -> bool:
        """Check if user is admin"""
        return user.is_admin is True

    @staticmethod
    def has_permission(user: models.User, permission: str) -> bool:
        """Check if admin has specific permission"""
        if not user.is_admin:
            return False

        if not user.admin_permissions:
            return False

        return user.admin_permissions.get(permission, False)

    @staticmethod
    def has_any_permission(user: models.User, permissions: List[str]) -> bool:
        """Check if admin has ANY of the permissions"""
        return any(AdminManager.has_permission(user, perm) for perm in permissions)

    @staticmethod
    def has_all_permissions(user: models.User, permissions: List[str]) -> bool:
        """Check if admin has ALL of the permissions"""
        return all(AdminManager.has_permission(user, perm) for perm in permissions)

    @staticmethod
    def grant_admin_role(
        db: Session, user_id: str, granted_by: str, permission_level: str = "full"
    ) -> models.User:
        """
        Grant admin role to a user

        Args:
            db: Database session
            user_id: User to promote to admin
            granted_by: Admin ID granting the role
            permission_level: "full", "moderator", or "viewer"

        Returns:
            Updated user model
        """
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise AIServiceError(f"User {user_id} not found")

        # Determine permissions based on level
        if permission_level == "full":
            permissions = DEFAULT_ADMIN_PERMISSIONS.copy()
        elif permission_level == "moderator":
            permissions = MODERATOR_PERMISSIONS.copy()
        elif permission_level == "viewer":
            permissions = VIEWER_PERMISSIONS.copy()
        else:
            raise AIServiceError(f"Invalid permission level: {permission_level}")

        # Add metadata
        permissions["created_at"] = int(time.time() * 1000)
        permissions["granted_by"] = granted_by
        permissions["level"] = permission_level

        user.is_admin = True
        user.admin_permissions = permissions
        user.admin_created_at = int(time.time() * 1000)
        user.admin_last_action = int(time.time() * 1000)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def revoke_admin_role(db: Session, user_id: str) -> models.User:
        """Revoke admin role from user"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise AIServiceError(f"User {user_id} not found")

        user.is_admin = False
        user.admin_permissions = {}

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_permissions(
        db: Session, user_id: str, permissions: Dict[str, bool]
    ) -> models.User:
        """Update specific permissions for admin user"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise AIServiceError(f"User {user_id} not found")

        if not user.is_admin:
            raise AIServiceError(f"User {user_id} is not an admin")

        # Merge with existing permissions
        current_perms = dict(user.admin_permissions or {})
        current_perms.update(permissions)
        user.admin_permissions = current_perms
        user.admin_last_action = int(time.time() * 1000)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def log_admin_action(
        db: Session,
        admin_id: str,
        action: str,
        target_id: str,
        details: Dict = None,
        ip_address: str = None,
        user_agent: str = None,
    ):
        """
        Log admin action to database for persistent audit trail.

        Args:
            db: Database session
            admin_id: ID of admin performing action
            action: Action type (e.g., "DELETE_USER", "UPDATE_PERMISSIONS")
            target_id: ID of affected resource
            details: Additional context as dict
            ip_address: Request IP address (optional)
            user_agent: Request user agent (optional)

        Returns:
            AdminActionLog instance
        """
        import uuid

        from app.db import models

        log_entry = models.AdminActionLog(
            id=str(uuid.uuid4()),
            admin_id=admin_id,
            action=action,
            target_id=target_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=int(time.time() * 1000),
        )

        try:
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)

            # Also log to stdout for development
            print(f"🛡️ Admin Action Log: {action} by {admin_id} on {target_id}")

            return log_entry
        except Exception as e:
            db.rollback()
            # Fallback to stdout if database write fails
            print(f"⚠️ Failed to persist admin log: {e}")
            # Return None to maintain backward compatibility with tests
            return None


# FastAPI Dependency for admin verification
async def verify_admin(user_id: str, db: Session) -> models.User:
    """Dependency to verify user is admin"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )
    if not AdminManager.is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )
    return user


async def verify_permission(user_id: str, permission: str, db: Session) -> models.User:
    """Dependency to verify user has specific permission"""
    user = await verify_admin(user_id, db)
    if not AdminManager.has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: Required permission '{permission}' is missing",
        )
    return user
