"""
Reusable Authorization & Authentication Dependencies

Centralized location for all FastAPI dependency functions used across endpoints.
These dependencies handle authorization checks and return appropriate HTTP errors.

Usage:
    from fastapi import Depends
    from app.api.dependencies import require_admin, require_permission

    @app.delete("/users/{id}")
    async def delete_user(
        user_id: str,
        current_user = Depends(require_admin),  # Admin check built-in
    ):
        # Admin already verified, just do business logic
        pass

Benefits:
    ✅ DRY principle - authorization logic defined once
    ✅ Consistency - same pattern across all endpoints
    ✅ Maintainability - change one place, updates everywhere
    ✅ Readability - endpoint intent is clear from dependencies
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.services.auth_service import get_current_user
from app.utils.user_roles import PermissionChecker, ResourceOwnershipChecker, is_admin

# ============================================================================
# BASIC ROLE CHECKS
# ============================================================================


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency: Verify user is admin.

    Raises:
        HTTPException: 403 Forbidden if user is not admin

    Returns:
        User: The authenticated admin user

    Usage:
        @app.delete("/admin/users/{id}")
        async def delete_user(
            user_id: str,
            current_user = Depends(require_admin),
        ):
            # User is guaranteed to be admin
            pass
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


# ============================================================================
# PERMISSION-BASED CHECKS
# ============================================================================


def require_permission(permission_name: str):
    """
    Dependency factory: Verify user has a specific permission.

    Args:
        permission_name: Name of the permission to check

    Returns:
        Dependency function that checks permission

    Raises:
        HTTPException: 403 Forbidden if permission is not granted

    Usage:
        @app.post("/admin/roles/grant")
        async def grant_admin(
            current_user = Depends(require_permission("can_manage_admins")),
        ):
            # User has can_manage_admins permission
            pass

    Supported Permissions:
        - can_view_all_users
        - can_manage_users
        - can_delete_users
        - can_manage_admins
        - can_view_all_notes
        - can_delete_notes
        - can_moderate_content
        - can_view_analytics
        - can_export_data
        - can_modify_system_settings
        - can_manage_roles
    """

    def check(current_user: models.User = Depends(get_current_user)) -> models.User:
        if not PermissionChecker.has_permission(current_user, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' required",
            )
        return current_user

    return check


def require_any_permission(permission_names: list[str]):
    """
    Dependency factory: Verify user has ANY of the permissions.

    Args:
        permission_names: List of permissions to check

    Raises:
        HTTPException: 403 Forbidden if user lacks all permissions

    Usage:
        @app.post("/moderate")
        async def moderate(
            current_user = Depends(require_any_permission([
                "can_moderate_content",
                "can_manage_admins"
            ])),
        ):
            # User has at least one of the permissions
            pass
    """

    def check(current_user: models.User = Depends(get_current_user)) -> models.User:
        if not PermissionChecker.has_any(current_user, permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return check


def require_all_permissions(permission_names: list[str]):
    """
    Dependency factory: Verify user has ALL of the permissions.

    Args:
        permission_names: List of permissions to check

    Raises:
        HTTPException: 403 Forbidden if user lacks any permission

    Usage:
        @app.post("/admin/export-all-data")
        async def export_data(
            current_user = Depends(require_all_permissions([
                "can_view_analytics",
                "can_export_data"
            ])),
        ):
            # User has all required permissions
            pass
    """

    def check(current_user: models.User = Depends(get_current_user)) -> models.User:
        if not PermissionChecker.has_all(current_user, permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return check


# ============================================================================
# COMPOUND CHECKS (Admin + Specific Permission)
# ============================================================================


def require_user_management(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency: Verify admin status + can_manage_users permission.

    Raises:
        HTTPException: 403 if not admin or lacks permission

    Usage:
        @app.post("/admin/users")
        async def create_user(
            user_data: UserCreate,
            current_user = Depends(require_user_management),
        ):
            # Admin + can_manage_users permission verified
            pass
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    if not PermissionChecker.has_permission(current_user, "can_manage_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission 'can_manage_users' required",
        )

    return current_user


def require_user_deletion(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency: Verify admin status + can_delete_users permission.

    Usage:
        @app.delete("/admin/users/{id}")
        async def delete_user(
            user_id: str,
            current_user = Depends(require_user_deletion),
        ):
            # Admin + can_delete_users permission verified
            pass
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    if not PermissionChecker.has_permission(current_user, "can_delete_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission 'can_delete_users' required",
        )

    return current_user


def require_admin_management(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency: Verify admin status + can_manage_admins permission.

    Usage:
        @app.post("/admin/users/{id}/make-admin")
        async def make_admin(
            user_id: str,
            current_user = Depends(require_admin_management),
        ):
            # Admin + can_manage_admins permission verified
            pass
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    if not PermissionChecker.has_permission(current_user, "can_manage_admins"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission 'can_manage_admins' required",
        )

    return current_user


def require_analytics_access(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency: Verify admin status + can_view_analytics permission.

    Usage:
        @app.get("/admin/stats")
        async def get_stats(
            current_user = Depends(require_analytics_access),
        ):
            # Admin + can_view_analytics permission verified
            pass
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    if not PermissionChecker.has_permission(current_user, "can_view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission 'can_view_analytics' required",
        )

    return current_user


def require_moderation_access(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency: Verify admin status + can_moderate_content permission.

    Usage:
        @app.post("/admin/moderate/{id}")
        async def moderate_content(
            content_id: str,
            current_user = Depends(require_moderation_access),
        ):
            # Admin + can_moderate_content permission verified
            pass
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    if not PermissionChecker.has_permission(current_user, "can_moderate_content"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission 'can_moderate_content' required",
        )

    return current_user


# ============================================================================
# RESOURCE OWNERSHIP CHECKS
# ============================================================================


def require_note_ownership(note_id: str):
    """
    Dependency factory: Verify user can access note (owns it or is admin).

    Args:
        note_id: ID of the note to access

    Returns:
        Note object if access is granted

    Raises:
        HTTPException: 404 if note not found, 403 if access denied

    Usage:
        @app.put("/notes/{note_id}")
        async def update_note(
            note_id: str,
            note_data: NoteUpdate,
            note = Depends(require_note_ownership(note_id)),
        ):
            # Note ownership verified, note object provided
            pass
    """

    async def check(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> models.Note:
        note = db.query(models.Note).filter(models.Note.id == note_id).first()

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
            )

        if not ResourceOwnershipChecker.can_access_note(current_user, note):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        return note

    return check


def require_task_ownership(task_id: str):
    """
    Dependency factory: Verify user can access task (owns it or is admin).

    Args:
        task_id: ID of the task to access

    Returns:
        Task object if access is granted

    Raises:
        HTTPException: 404 if task not found, 403 if access denied

    Usage:
        @app.put("/tasks/{task_id}")
        async def update_task(
            task_id: str,
            task_data: TaskUpdate,
            task = Depends(require_task_ownership(task_id)),
        ):
            # Task ownership verified, task object provided
            pass
    """

    async def check(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> models.Task:
        task = db.query(models.Task).filter(models.Task.id == task_id).first()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )

        if not ResourceOwnershipChecker.can_access_task(current_user, task):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        return task

    return check


# ============================================================================
# SUMMARY
# ============================================================================

"""
AVAILABLE DEPENDENCIES:

Basic Role Checks:
  - require_admin()

Permission Checks:
  - require_permission(perm)
  - require_any_permission(perms)
  - require_all_permissions(perms)

Compound Checks (Admin + Permission):
  - require_user_management()
  - require_user_deletion()
  - require_admin_management()
  - require_analytics_access()
  - require_moderation_access()

Resource Ownership:
  - require_note_ownership(note_id)
  - require_task_ownership(task_id)

All dependencies:
  ✅ Return 403 if authorization fails
  ✅ Return 404 if resource not found
  ✅ Handle None/invalid input gracefully
  ✅ Work seamlessly with FastAPI dependency injection
"""
