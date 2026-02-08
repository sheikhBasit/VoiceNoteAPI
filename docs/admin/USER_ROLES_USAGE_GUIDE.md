"""
USAGE GUIDE - User Roles & Permissions Utilities

This guide shows how to use the new user_roles module in your API endpoints
for clean, modular, and readable role-based access control.

Author: Your API Team
Date: February 6, 2026
"""

# ============================================================================
# QUICK START - Common Use Cases
# ============================================================================

"""
EXAMPLE 1: Simple Admin Check
─────────────────────────────
Check if user is admin before allowing action.
"""

from fastapi import HTTPException, status
from app.utils.user_roles import is_admin

@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(get_current_user),
):
    """Delete a user (admin only)"""
    
    # Simple, readable permission check
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )
    
    # Proceed with deletion
    # ...


"""
EXAMPLE 2: Permission-Based Access
──────────────────────────────────
Check specific permissions for granular access control.
"""

from app.utils.user_roles import PermissionChecker

@app.get("/api/v1/admin/analytics")
async def get_analytics(
    current_user = Depends(get_current_user),
):
    """Get system analytics (requires permission)"""
    
    # Check for specific permission
    if not PermissionChecker.has_permission(current_user, "can_view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view analytics"
        )
    
    # Return analytics
    # ...


"""
EXAMPLE 3: Multiple Permission Checks
─────────────────────────────────────
Check if user has ANY or ALL of multiple permissions.
"""

@app.post("/api/v1/admin/moderate")
async def moderate_content(
    content_id: str,
    current_user = Depends(get_current_user),
):
    """Moderate content (requires moderation OR management permission)"""
    
    # Check if user has ANY of these permissions
    if not PermissionChecker.has_any(current_user, [
        "can_moderate_content",
        "can_manage_admins"
    ]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have moderation permissions"
        )
    
    # Proceed with moderation
    # ...


@app.post("/api/v1/admin/system-settings")
async def update_system_settings(
    settings: dict,
    current_user = Depends(get_current_user),
):
    """Update system settings (requires ALL permissions)"""
    
    # Check if user has ALL of these permissions
    if not PermissionChecker.has_all(current_user, [
        "can_modify_system_settings",
        "can_manage_roles"
    ]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for system settings"
        )
    
    # Update settings
    # ...


"""
EXAMPLE 4: Resource Ownership Check
───────────────────────────────────
Verify user owns or has admin access to a resource.
"""

from app.utils.user_roles import ResourceOwnershipChecker

@app.patch("/api/v1/notes/{note_id}")
async def update_note(
    note_id: str,
    update_data: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a note (owner or admin only)"""
    
    # Get note from database
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Check ownership
    if not ResourceOwnershipChecker.can_access_note(current_user, note):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this note"
        )
    
    # Update note
    # ...


"""
EXAMPLE 5: User Type-Based Logic
────────────────────────────────
Perform different logic based on user type.
"""

from app.utils.user_roles import UserRoleChecker, UserType

@app.get("/api/v1/dashboard")
async def get_dashboard(
    current_user = Depends(get_current_user),
):
    """Get dashboard (content varies by user type)"""
    
    user_type = UserRoleChecker.get_user_type(current_user)
    
    if user_type == UserType.ADMIN:
        # Return admin dashboard with system stats
        return {
            "type": "admin",
            "stats": get_admin_stats(),
            "users": get_all_users(),
            "logs": get_admin_logs(),
        }
    
    elif user_type == UserType.MODERATOR:
        # Return moderator dashboard with moderation queue
        return {
            "type": "moderator",
            "pending_reviews": get_pending_reviews(),
            "recent_actions": get_moderator_actions(),
        }
    
    elif user_type == UserType.VIEWER:
        # Return viewer dashboard with analytics only
        return {
            "type": "viewer",
            "analytics": get_analytics(),
            "reports": get_reports(),
        }
    
    else:  # GUEST
        # Return guest dashboard with user notes
        return {
            "type": "guest",
            "notes": get_user_notes(current_user.id),
            "tasks": get_user_tasks(current_user.id),
        }


"""
EXAMPLE 6: Dependency Helper for Admin-Only Endpoints
─────────────────────────────────────────────────────
Create a reusable dependency for admin-only routes.
"""

from fastapi import Depends

def require_admin(current_user = Depends(get_current_user)):
    """Dependency: Require admin role"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
    )
    return current_user


def require_permission(permission: str):
    """Dependency: Require specific permission"""
    def check_permission(current_user = Depends(get_current_user)):
        if not PermissionChecker.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return check_permission


# Usage in endpoints
@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),  # Auto-checks admin
):
    """Delete user (auto-protected by dependency)"""
    # ...


@app.get("/api/v1/analytics/export")
async def export_analytics(
    current_user = Depends(require_permission("can_export_data")),
):
    """Export analytics (auto-checks permission)"""
    # ...


# ============================================================================
# BEST PRACTICES
# ============================================================================

"""
1. USE CLEAR, READABLE CODE
───────────────────────────

✅ Good:
    if PermissionChecker.has_permission(user, "can_delete_users"):
        # Clear intent - checking specific permission

❌ Bad:
    if user.admin_permissions.get("can_delete_users"):
        # Unclear if None handling is correct
    if user.is_admin and user.id in ADMIN_IDS:
        # Redundant checks, hard to maintain


2. USE DEPENDENCIES FOR COMMON CHECKS
─────────────────────────────────────

✅ Good:
    async def delete_user(
        user_id: str,
        current_user = Depends(require_admin),
    ):
        # Admin check automatic, cleaner code

❌ Bad:
    async def delete_user(
        user_id: str,
        current_user = Depends(get_current_user),
    ):
        if not current_user.is_admin:
            raise HTTPException(...)
        # Repetitive permission checks


3. USE USER TYPES FOR CONDITIONAL LOGIC
───────────────────────────────────────

✅ Good:
    user_type = UserRoleChecker.get_user_type(user)
    if user_type == UserType.ADMIN:
        # Admin logic
    elif user_type == UserType.MODERATOR:
        # Moderator logic
    # Clear, easy to understand roles

❌ Bad:
    if user.is_admin and has_perm(user, "can_manage_users"):
        # Admin logic
    elif user.is_admin and has_perm(user, "can_moderate_content"):
        # Moderator logic
    # Confusing permission combinations


4. ALWAYS USE SAFE FUNCTIONS
───────────────────────────

✅ Safe (handles None):
    is_admin(current_user)  # Returns False if None
    PermissionChecker.has_permission(user, "perm")  # Safe with None

❌ Unsafe (will crash if None):
    current_user.is_admin  # Crashes if None
    user.admin_permissions.get("perm")  # Crashes if None


5. LOG PERMISSION DENIALS
────────────────────────

from app.utils.json_logger import JLogger

if not PermissionChecker.has_permission(user, "can_delete_users"):
    JLogger.warning(
        "Permission denied",
        user_id=user.id,
        required_permission="can_delete_users",
        action="delete_user"
    )
    raise HTTPException(...)


6. GROUP RELATED PERMISSIONS
────────────────────────────

✅ Good - Use has_any/has_all for related perms:
    if PermissionChecker.has_any(user, [
        "can_manage_users",
        "can_delete_users",
    ]):
        # User can do user management

❌ Bad - Checking multiple times:
    if PermissionChecker.has_permission(user, "can_manage_users") \
       or PermissionChecker.has_permission(user, "can_delete_users"):
        # Repetitive
"""


# ============================================================================
# COMPLETE ENDPOINT EXAMPLE
# ============================================================================

"""
Example: Complete Admin Management Endpoint
──────────────────────────────────────────

This example shows a complete endpoint using all best practices.
"""

from sqlalchemy.orm import Session
from app.utils.user_roles import (
    is_admin, PermissionChecker, UserRoleChecker, UserType
)
from app.utils.json_logger import JLogger

@app.post("/api/v1/admin/users/{user_id}/promote")
async def promote_user_to_admin(
    user_id: str,
    role: str = "moderator",  # "full", "moderator", "viewer"
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Promote a user to admin role.
    
    Requires: can_manage_admins permission
    
    Args:
        user_id: User to promote
        role: Admin role (full, moderator, viewer)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Updated user info
        
    Raises:
        403: If user lacks permission
        404: If user not found
        400: If invalid role
    """
    
    # 1. PERMISSION CHECK - Use clear, modular check
    if not PermissionChecker.has_permission(current_user, "can_manage_admins"):
        JLogger.warning(
            "Promotion denied - insufficient permission",
            promoter_id=current_user.id,
            target_user_id=user_id,
            required_perm="can_manage_admins"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage admins"
        )
    
    # 2. VALIDATE ROLE
    valid_roles = {"full", "moderator", "viewer"}
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {valid_roles}"
        )
    
    # 3. GET TARGET USER
    target_user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # 4. PERFORM PROMOTION (simplified)
    if role == "full":
        perms = {
            "can_view_all_users": True,
            "can_manage_users": True,
            "can_manage_admins": True,
            "can_view_all_notes": True,
            "can_moderate_content": True,
            "can_view_analytics": True,
        }
    elif role == "moderator":
        perms = {
            "can_view_all_notes": True,
            "can_moderate_content": True,
        }
    else:  # viewer
        perms = {
            "can_view_analytics": True,
        }
    
    target_user.is_admin = True
    target_user.admin_permissions = perms
    db.commit()
    
    # 5. LOG ACTION
    JLogger.info(
        "User promoted to admin",
        admin_id=current_user.id,
        promoted_user_id=user_id,
        role=role
    )
    
    # 6. RETURN RESULT
    return {
        "id": target_user.id,
        "name": target_user.name,
        "email": target_user.email,
        "is_admin": target_user.is_admin,
        "role": role,
        "permissions": perms,
    }


# ============================================================================
# MIGRATION GUIDE - From Old Code to New
# ============================================================================

"""
OLD WAY:
    if not current_user.is_admin:
        raise HTTPException(403, "Admin only")

NEW WAY:
    if not is_admin(current_user):
        raise HTTPException(403, "Admin only")
    
✓ Safer (handles None)
✓ More readable
✓ Consistent with codebase


OLD WAY:
    if current_user.admin_permissions.get("can_view_analytics"):
        ...

NEW WAY:
    if PermissionChecker.has_permission(current_user, "can_view_analytics"):
        ...
    
✓ Clearer intent
✓ Better error handling
✓ Reusable


OLD WAY:
    if current_user.is_admin and current_user.admin_permissions.get("x"):
        ...
    elif current_user.is_admin and current_user.admin_permissions.get("y"):
        ...

NEW WAY:
    user_type = UserRoleChecker.get_user_type(current_user)
    if user_type == UserType.ADMIN:
        ...
    elif user_type == UserType.MODERATOR:
        ...
    
✓ Much cleaner
✓ Easier to understand
✓ Better maintainability
"""
