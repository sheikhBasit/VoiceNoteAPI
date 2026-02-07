"""
User Role & Permission Utilities Module

A comprehensive, modular utility module for role-based access control (RBAC).
Provides clean, reusable functions for checking user roles and permissions.

Usage:
    from app.utils.user_roles import (
        UserRoleChecker, PermissionChecker, UserType
    )
    
    # Check if user is admin
    if UserRoleChecker.is_admin(user):
        # admin logic
    
    # Check if user is guest
    if UserRoleChecker.is_guest(user):
        # guest logic
    
    # Check specific permission
    if PermissionChecker.has_permission(user, "can_view_all_users"):
        # permission granted
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from app.db import models


# ============================================================================
# ENUMS - User Types and Roles
# ============================================================================

class UserType(str, Enum):
    """
    User type enumeration for clear role identification.
    
    Values:
        ADMIN: Full system access with all permissions
        MODERATOR: Content moderation permissions only
        VIEWER: Read-only analytics and statistics
        GUEST: Regular user with no special permissions
    """
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"
    VIEWER = "VIEWER"
    GUEST = "GUEST"


class PermissionName(str, Enum):
    """
    Standard permission names for RBAC.
    
    These permissions can be assigned to admin roles to control
    what actions they can perform in the system.
    """
    # User Management
    VIEW_ALL_USERS = "can_view_all_users"
    MANAGE_USERS = "can_manage_users"
    DELETE_USERS = "can_delete_users"
    GRANT_ADMIN = "can_manage_admins"
    
    # Content Management
    VIEW_ALL_NOTES = "can_view_all_notes"
    DELETE_NOTES = "can_delete_notes"
    MODERATE_CONTENT = "can_moderate_content"
    
    # Analytics
    VIEW_ANALYTICS = "can_view_analytics"
    EXPORT_DATA = "can_export_data"
    
    # System
    MODIFY_SETTINGS = "can_modify_system_settings"
    MANAGE_ROLES = "can_manage_roles"


# ============================================================================
# PERMISSION SETS - Predefined role-based permission groups
# ============================================================================

# Predefined permission sets for common admin roles.
# These can be assigned to users when granting admin access.
PERMISSION_SETS: Dict[UserType, Dict[str, bool]] = {
    UserType.ADMIN: {
        PermissionName.VIEW_ALL_USERS.value: True,
        PermissionName.MANAGE_USERS.value: True,
        PermissionName.DELETE_USERS.value: True,
        PermissionName.GRANT_ADMIN.value: True,
        PermissionName.VIEW_ALL_NOTES.value: True,
        PermissionName.DELETE_NOTES.value: True,
        PermissionName.MODERATE_CONTENT.value: True,
        PermissionName.VIEW_ANALYTICS.value: True,
        PermissionName.EXPORT_DATA.value: True,
        PermissionName.MODIFY_SETTINGS.value: True,
        PermissionName.MANAGE_ROLES.value: True,
    },
    
    UserType.MODERATOR: {
        PermissionName.VIEW_ALL_NOTES.value: True,
        PermissionName.DELETE_NOTES.value: True,
        PermissionName.MODERATE_CONTENT.value: True,
    },
    
    UserType.VIEWER: {
        PermissionName.VIEW_ALL_USERS.value: True,
        PermissionName.VIEW_ALL_NOTES.value: True,
        PermissionName.VIEW_ANALYTICS.value: True,
    },
    
    UserType.GUEST: {},
}


# ============================================================================
# MAIN UTILITY CLASSES
# ============================================================================

class UserRoleChecker:
    """
    Utility class for checking user role and type.
    
    Provides simple, clean methods to determine if a user is:
    - Admin (full access)
    - Moderator (content moderation)
    - Viewer (read-only)
    - Guest (regular user)
    
    All methods are safe - they handle None/invalid inputs gracefully.
    
    Example:
        >>> user = db.query(models.User).first()
        >>> if UserRoleChecker.is_admin(user):
        ...     # Grant admin access
        ...
        >>> if UserRoleChecker.is_guest(user):
        ...     # Show guest-only features
        ...
    """
    
    @staticmethod
    def is_admin(user: Optional[models.User]) -> bool:
        """
        Check if user has admin role.
        
        Args:
            user: User model instance or None
            
        Returns:
            bool: True if user is admin, False otherwise
            
        Safety:
            - Returns False if user is None
            - Returns False if is_admin attribute missing
            - Safe for all input types
        """
        if user is None:
            return False
        return getattr(user, "is_admin", False) is True
    
    @staticmethod
    def is_guest(user: Optional[models.User]) -> bool:
        """
        Check if user is a guest (not admin).
        
        A guest is any user without admin privileges.
        This is the opposite of is_admin().
        
        Args:
            user: User model instance or None
            
        Returns:
            bool: True if user is NOT admin, False if admin or None
            
        Note:
            A None user is considered guest (not admin).
        """
        if user is None:
            return True
        return not UserRoleChecker.is_admin(user)
    
    @staticmethod
    def get_user_type(user: Optional[models.User]) -> UserType:
        """
        Get the user type (ADMIN, MODERATOR, VIEWER, or GUEST).
        
        Determines user type based on admin status and permissions.
        
        Args:
            user: User model instance or None
            
        Returns:
            UserType: The user's role type
            
        Examples:
            >>> user_type = UserRoleChecker.get_user_type(user)
            >>> if user_type == UserType.ADMIN:
            ...     # User is admin
            ...
        """
        if user is None:
            return UserType.GUEST
        
        if not UserRoleChecker.is_admin(user):
            return UserType.GUEST
        
        # User is admin - determine which type based on permissions
        perms = getattr(user, "admin_permissions", {}) or {}
        
        # Check permission counts to determine admin level
        if perms.get(PermissionName.MANAGE_USERS.value):
            return UserType.ADMIN  # Full admin
        elif perms.get(PermissionName.MODERATE_CONTENT.value):
            return UserType.MODERATOR  # Content moderator
        elif perms.get(PermissionName.VIEW_ANALYTICS.value):
            return UserType.VIEWER  # Analytics viewer
        
        return UserType.ADMIN  # Default to admin if is_admin but no specific perms
    
    @staticmethod
    def is_moderator(user: Optional[models.User]) -> bool:
        """
        Check if user is a moderator.
        
        Args:
            user: User model instance or None
            
        Returns:
            bool: True if user is moderator, False otherwise
        """
        return UserRoleChecker.get_user_type(user) == UserType.MODERATOR
    
    @staticmethod
    def is_viewer(user: Optional[models.User]) -> bool:
        """
        Check if user is an analytics viewer.
        
        Args:
            user: User model instance or None
            
        Returns:
            bool: True if user is viewer, False otherwise
        """
        return UserRoleChecker.get_user_type(user) == UserType.VIEWER


class PermissionChecker:
    """
    Utility class for checking user permissions.
    
    Provides methods to verify if a user (or admin) has specific permissions.
    
    Supports:
    - Single permission checks
    - Multiple permission checks (ANY or ALL)
    - Permission validation
    
    Example:
        >>> if PermissionChecker.has_permission(user, "can_view_all_users"):
        ...     # User has permission
        ...
        >>> if PermissionChecker.has_any(user, ["can_delete_users", "can_manage_admins"]):
        ...     # User has at least one permission
        ...
        >>> if PermissionChecker.has_all(user, ["can_view_all_users", "can_view_analytics"]):
        ...     # User has all permissions
        ...
    """
    
    @staticmethod
    def has_permission(
        user: Optional[models.User], 
        permission: str
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Only admins can have permissions. Regular guests return False.
        
        Args:
            user: User model instance or None
            permission: Permission name to check (e.g., "can_view_all_users")
            
        Returns:
            bool: True if user has permission, False otherwise
            
        Safety:
            - Returns False if user is not admin
            - Returns False if user is None
            - Returns False if permission not found
            
        Examples:
            >>> if PermissionChecker.has_permission(user, "can_delete_users"):
            ...     # Can delete users
            ...
        """
        # Non-admins have no permissions
        if not UserRoleChecker.is_admin(user):
            return False
        
        # Get admin permissions dict
        permissions = getattr(user, "admin_permissions", {}) or {}
        
        # Check if permission exists and is True
        return permissions.get(permission, False) is True
    
    @staticmethod
    def has_any(
        user: Optional[models.User], 
        permissions: List[str]
    ) -> bool:
        """
        Check if user has ANY of the specified permissions.
        
        Returns True if user has at least one of the permissions.
        
        Args:
            user: User model instance or None
            permissions: List of permission names
            
        Returns:
            bool: True if user has at least one permission
            
        Examples:
            >>> if PermissionChecker.has_any(user, ["can_delete_users", "can_manage_admins"]):
            ...     # Has delete OR manage permissions
            ...
        """
        return any(
            PermissionChecker.has_permission(user, perm) 
            for perm in permissions
        )
    
    @staticmethod
    def has_all(
        user: Optional[models.User], 
        permissions: List[str]
    ) -> bool:
        """
        Check if user has ALL of the specified permissions.
        
        Returns True only if user has every permission listed.
        
        Args:
            user: User model instance or None
            permissions: List of permission names
            
        Returns:
            bool: True if user has all permissions
            
        Examples:
            >>> if PermissionChecker.has_all(user, ["can_delete_users", "can_manage_admins"]):
            ...     # Has both delete AND manage permissions
            ...
        """
        return all(
            PermissionChecker.has_permission(user, perm) 
            for perm in permissions
        )
    
    @staticmethod
    def get_permissions(user: Optional[models.User]) -> Dict[str, bool]:
        """
        Get all permissions for a user.
        
        Args:
            user: User model instance or None
            
        Returns:
            dict: Dictionary of permission name -> granted (bool)
                  Empty dict if user is not admin
                  
        Examples:
            >>> perms = PermissionChecker.get_permissions(user)
            >>> for perm_name, granted in perms.items():
            ...     if granted:
            ...         print(f"User has: {perm_name}")
            ...
        """
        if not UserRoleChecker.is_admin(user):
            return {}
        
        return getattr(user, "admin_permissions", {}) or {}


class ResourceOwnershipChecker:
    """
    Utility class for verifying resource ownership.
    
    Provides methods to check if a user owns or has access to a resource.
    
    Rules:
    - Admins can access any resource
    - Regular users can only access their own resources
    
    Example:
        >>> # Check note ownership
        >>> if ResourceOwnershipChecker.can_access_note(user, note):
        ...     # User can read/modify this note
        ...
        >>> # Check task ownership
        >>> if ResourceOwnershipChecker.can_access_task(user, task):
        ...     # User can read/modify this task
        ...
    """
    
    @staticmethod
    def can_access_note(
        user: Optional[models.User], 
        note: Optional[models.Note]
    ) -> bool:
        """
        Check if user can access a note.
        
        Rules:
        - Admins can access any note
        - Regular users can only access notes they own
        
        Args:
            user: User model instance
            note: Note model instance
            
        Returns:
            bool: True if user can access note
        """
        if user is None or note is None:
            return False
        
        # Admins can access any note
        if UserRoleChecker.is_admin(user):
            return True
        
        # Regular users can only access their own notes
        return note.user_id == user.id
    
    @staticmethod
    def can_access_task(
        user: Optional[models.User], 
        task: Optional[models.Task]
    ) -> bool:
        """
        Check if user can access a task.
        
        Rules:
        - Admins can access any task
        - Regular users can only access tasks they own
        
        Args:
            user: User model instance
            task: Task model instance
            
        Returns:
            bool: True if user can access task
        """
        if user is None or task is None:
            return False
        
        # Admins can access any task
        if UserRoleChecker.is_admin(user):
            return True
        
        # Regular users can only access their own tasks
        return task.user_id == user.id
    
    @staticmethod
    def is_owner(
        user: Optional[models.User], 
        resource_owner_id: Optional[str]
    ) -> bool:
        """
        Generic method to check if user is the owner of a resource.
        
        Args:
            user: User model instance
            resource_owner_id: The ID of the resource owner
            
        Returns:
            bool: True if user owns the resource
        """
        if user is None or resource_owner_id is None:
            return False
        
        # Admins are considered owners of all resources
        if UserRoleChecker.is_admin(user):
            return True
        
        # Regular users own resource if IDs match
        return user.id == resource_owner_id


# ============================================================================
# CONVENIENCE FUNCTIONS - For direct import and use
# ============================================================================

def is_admin(user: Optional[models.User]) -> bool:
    """
    Quick check: Is user an admin?
    
    Convenience function equivalent to UserRoleChecker.is_admin()
    
    Args:
        user: User model instance or None
        
    Returns:
        bool: True if user is admin, False otherwise
    """
    return UserRoleChecker.is_admin(user)


def is_guest(user: Optional[models.User]) -> bool:
    """
    Quick check: Is user a guest (not admin)?
    
    Convenience function equivalent to UserRoleChecker.is_guest()
    
    Args:
        user: User model instance or None
        
    Returns:
        bool: True if user is NOT admin, False if admin or None
    """
    return UserRoleChecker.is_guest(user)


def has_permission(user: Optional[models.User], permission: str) -> bool:
    """
    Quick check: Does user have a specific permission?
    
    Convenience function equivalent to PermissionChecker.has_permission()
    
    Args:
        user: User model instance or None
        permission: Permission name to check
        
    Returns:
        bool: True if user has permission
    """
    return PermissionChecker.has_permission(user, permission)


def get_user_type(user: Optional[models.User]) -> UserType:
    """
    Quick check: What type of user is this?
    
    Returns the user's role type (ADMIN, MODERATOR, VIEWER, or GUEST)
    
    Args:
        user: User model instance or None
        
    Returns:
        UserType: The user's role type
    """
    return UserRoleChecker.get_user_type(user)


# ============================================================================
# MODULE DOCSTRING EXAMPLES
# ============================================================================

"""
USAGE EXAMPLES:

1. Check if user is admin:
   >>> from app.utils.user_roles import is_admin, is_guest
   >>> if is_admin(current_user):
   ...     # Grant admin access
   ...
   >>> if is_guest(current_user):
   ...     # Show guest features

2. Check specific permissions:
   >>> from app.utils.user_roles import PermissionChecker
   >>> if PermissionChecker.has_permission(user, "can_delete_users"):
   ...     # Allow delete operation

3. Check multiple permissions:
   >>> if PermissionChecker.has_any(user, ["can_delete_users", "can_manage_admins"]):
   ...     # Has at least one permission
   >>> if PermissionChecker.has_all(user, ["can_view_analytics", "can_export_data"]):
   ...     # Has all permissions

4. Get user type:
   >>> from app.utils.user_roles import UserRoleChecker, UserType
   >>> user_type = UserRoleChecker.get_user_type(user)
   >>> if user_type == UserType.ADMIN:
   ...     # Is full admin
   >>> elif user_type == UserType.MODERATOR:
   ...     # Is content moderator

5. Check resource ownership:
   >>> from app.utils.user_roles import ResourceOwnershipChecker
   >>> if ResourceOwnershipChecker.can_access_note(user, note):
   ...     # User can read/modify note
   >>> if ResourceOwnershipChecker.can_access_task(user, task):
   ...     # User can read/modify task

6. In FastAPI endpoints:
   >>> from fastapi import Depends
   >>> from app.utils.user_roles import is_admin, PermissionChecker
   >>> 
   >>> @app.delete("/api/v1/users/{user_id}")
   >>> async def delete_user(
   ...     user_id: str,
   ...     current_user = Depends(get_current_user),
   ... ):
   ...     # Only admins with delete permission can call this
   ...     if not is_admin(current_user):
   ...         raise HTTPException(status_code=403, detail="Admin only")
   ...     
   ...     if not PermissionChecker.has_permission(current_user, "can_delete_users"):
   ...         raise HTTPException(status_code=403, detail="Missing permission")
   ...     
   ...     # Proceed with deletion
"""
