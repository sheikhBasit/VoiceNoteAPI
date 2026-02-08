# 🔐 User Roles & Permissions Module Documentation

**Module:** `app/utils/user_roles.py`  
**Version:** 1.0  
**Date:** February 6, 2026  
**Status:** Production Ready ✅

---

## 📋 Overview

The User Roles & Permissions module provides **clean, modular, and well-documented utilities** for role-based access control (RBAC) in the VoiceNote API.

### Key Features

✅ **Simple API** - Easy to understand, minimal code  
✅ **Safe** - Handles None/invalid inputs gracefully  
✅ **Modular** - Use individual utilities or classes  
✅ **Well-Documented** - Extensive docstrings and examples  
✅ **Type-Safe** - Full type hints throughout  
✅ **Tested** - Ready for production use  

---

## 🎯 Core Components

### 1. **UserRoleChecker** Class

Provides methods to determine user role and type.

```python
from app.utils.user_roles import UserRoleChecker, UserType

# Check if user is admin
if UserRoleChecker.is_admin(user):
    # Grant admin access

# Check if user is guest (not admin)
if UserRoleChecker.is_guest(user):
    # Show guest features

# Get user type
user_type = UserRoleChecker.get_user_type(user)
if user_type == UserType.ADMIN:
    # Show admin features
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `is_admin(user)` | `bool` | True if user is admin |
| `is_guest(user)` | `bool` | True if user is NOT admin |
| `is_moderator(user)` | `bool` | True if user is moderator |
| `is_viewer(user)` | `bool` | True if user is viewer |
| `get_user_type(user)` | `UserType` | Returns ADMIN, MODERATOR, VIEWER, or GUEST |

#### Safety Features

- ✅ Returns `False` if user is `None`
- ✅ Handles missing attributes gracefully
- ✅ Never raises exceptions
- ✅ Safe for all input types

---

### 2. **PermissionChecker** Class

Check if user has specific permissions.

```python
from app.utils.user_roles import PermissionChecker

# Check single permission
if PermissionChecker.has_permission(user, "can_delete_users"):
    # Allow deletion

# Check if user has ANY permission
if PermissionChecker.has_any(user, [
    "can_delete_users",
    "can_manage_admins"
]):
    # Has at least one permission

# Check if user has ALL permissions
if PermissionChecker.has_all(user, [
    "can_view_analytics",
    "can_export_data"
]):
    # Has both permissions
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `has_permission(user, perm)` | `bool` | Check single permission |
| `has_any(user, perms)` | `bool` | Check if has ANY permission |
| `has_all(user, perms)` | `bool` | Check if has ALL permissions |
| `get_permissions(user)` | `dict` | Get all permissions |

#### Supported Permissions

```python
"can_view_all_users"      # View all users
"can_manage_users"        # Create/update/delete users
"can_delete_users"        # Delete users
"can_manage_admins"       # Grant/revoke admin status
"can_view_all_notes"      # View all notes
"can_delete_notes"        # Delete notes
"can_moderate_content"    # Review and moderate content
"can_view_analytics"      # View analytics and statistics
"can_export_data"         # Export system data
"can_modify_system_settings"  # Change system configuration
"can_manage_roles"        # Manage user roles
```

---

### 3. **ResourceOwnershipChecker** Class

Verify if user can access a resource.

```python
from app.utils.user_roles import ResourceOwnershipChecker

# Check note access
if ResourceOwnershipChecker.can_access_note(user, note):
    # User owns note or is admin

# Check task access
if ResourceOwnershipChecker.can_access_task(user, task):
    # User owns task or is admin

# Generic ownership check
if ResourceOwnershipChecker.is_owner(user, resource_owner_id):
    # User owns resource
```

#### Rules

- **Admins** can access any resource
- **Regular users** can only access their own resources
- Returns `False` if user or resource is `None`

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `can_access_note(user, note)` | `bool` | Can user access note? |
| `can_access_task(user, task)` | `bool` | Can user access task? |
| `is_owner(user, owner_id)` | `bool` | Is user the owner? |

---

### 4. **UserType** Enum

Defines user role types.

```python
from app.utils.user_roles import UserType

class UserType(str, Enum):
    ADMIN = "ADMIN"           # Full system access
    MODERATOR = "MODERATOR"   # Content moderation
    VIEWER = "VIEWER"         # Analytics/read-only
    GUEST = "GUEST"           # Regular user (no special access)
```

---

### 5. **Convenience Functions**

Quick functions for direct import.

```python
from app.utils.user_roles import (
    is_admin,           # UserRoleChecker.is_admin()
    is_guest,           # UserRoleChecker.is_guest()
    has_permission,     # PermissionChecker.has_permission()
    get_user_type,      # UserRoleChecker.get_user_type()
)

if is_admin(user):
    # ...

if has_permission(user, "can_delete_users"):
    # ...

user_type = get_user_type(user)
```

---

## 📖 Usage Examples

### Example 1: Admin-Only Endpoint

```python
from fastapi import HTTPException, status
from app.utils.user_roles import is_admin

@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(get_current_user),
):
    """Delete a user (admin only)"""
    
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )
    
    # Delete user...
    return {"message": "User deleted"}
```

### Example 2: Permission-Based Access

```python
from app.utils.user_roles import PermissionChecker

@app.get("/api/v1/admin/analytics")
async def get_analytics(
    current_user = Depends(get_current_user),
):
    """Get analytics (requires permission)"""
    
    if not PermissionChecker.has_permission(
        current_user, 
        "can_view_analytics"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission"
        )
    
    # Return analytics...
```

### Example 3: Multiple Permissions

```python
from app.utils.user_roles import PermissionChecker

@app.post("/api/v1/admin/moderate")
async def moderate_content(
    content_id: str,
    current_user = Depends(get_current_user),
):
    """Moderate content (needs moderation OR management)"""
    
    # Check if has ANY permission
    if not PermissionChecker.has_any(current_user, [
        "can_moderate_content",
        "can_manage_admins"
    ]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing permissions"
        )
    
    # Moderate...
```

### Example 4: Reusable Dependencies

```python
from fastapi import Depends

def require_admin(current_user = Depends(get_current_user)):
    """Dependency: Check admin role"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin required"
        )
    return current_user

def require_permission(perm: str):
    """Dependency: Check specific permission"""
    def check(current_user = Depends(get_current_user)):
        if not PermissionChecker.has_permission(current_user, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{perm}' required"
            )
        return current_user
    return check

# Usage:
@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),
):
    # Admin check automatic
    pass

@app.get("/api/v1/admin/export")
async def export_data(
    current_user = Depends(require_permission("can_export_data")),
):
    # Permission check automatic
    pass
```

### Example 5: Type-Based Logic

```python
from app.utils.user_roles import UserRoleChecker, UserType

@app.get("/api/v1/dashboard")
async def get_dashboard(current_user = Depends(get_current_user)):
    """Get dashboard (varies by user type)"""
    
    user_type = UserRoleChecker.get_user_type(current_user)
    
    if user_type == UserType.ADMIN:
        return {"data": get_admin_dashboard()}
    elif user_type == UserType.MODERATOR:
        return {"data": get_moderator_dashboard()}
    elif user_type == UserType.VIEWER:
        return {"data": get_viewer_dashboard()}
    else:  # GUEST
        return {"data": get_guest_dashboard()}
```

---

## 🏗️ Architecture & Design

### Principle: Separation of Concerns

- **UserRoleChecker** - Determines user role/type
- **PermissionChecker** - Checks specific permissions
- **ResourceOwnershipChecker** - Verifies resource access

### Principle: Safety First

All functions:
- ✅ Handle `None` input gracefully
- ✅ Never raise unexpected exceptions
- ✅ Return sensible defaults
- ✅ Have full type hints

### Principle: Readability

Code using these utilities is:
- ✅ Self-documenting
- ✅ Easy to understand
- ✅ Minimal boilerplate
- ✅ Consistent

---

## 🧪 Testing

All utilities are thoroughly tested and production-ready.

```python
# Example tests

def test_is_admin():
    admin_user = User(is_admin=True)
    guest_user = User(is_admin=False)
    
    assert UserRoleChecker.is_admin(admin_user) == True
    assert UserRoleChecker.is_admin(guest_user) == False
    assert UserRoleChecker.is_admin(None) == False

def test_has_permission():
    admin_user = User(
        is_admin=True,
        admin_permissions={"can_delete_users": True}
    )
    
    assert PermissionChecker.has_permission(
        admin_user, "can_delete_users"
    ) == True
    
    assert PermissionChecker.has_permission(
        admin_user, "can_manage_admins"
    ) == False
```

---

## ✨ Best Practices

### DO ✅

```python
# Clear, readable code
if is_admin(current_user):
    # Make sense of intent

# Use dependencies for common checks
@app.delete("/users/{id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),
):
    # Permission checked automatically

# Use user types for conditional logic
user_type = get_user_type(user)
if user_type == UserType.ADMIN:
    # Specific admin logic
```

### DON'T ❌

```python
# Unclear intent
if current_user.is_admin and user.admin_permissions.get("can_delete"):
    # Redundant, hard to maintain

# Repetitive checks
if not current_user.is_admin:
    raise HTTPException(403)
# ... (repeated in 10 endpoints)

# Fragile code
if current_user.admin_permissions["can_delete"]:  # Crashes if None!
    # ...
```

---

## 🔄 Migration Guide

### From Direct Attribute Access

**Before:**
```python
if current_user.is_admin:
    # ...
```

**After:**
```python
from app.utils.user_roles import is_admin

if is_admin(current_user):
    # ...
```

### From Manual Permission Checks

**Before:**
```python
if current_user.is_admin and current_user.admin_permissions.get("x"):
    # ...
```

**After:**
```python
from app.utils.user_roles import PermissionChecker

if PermissionChecker.has_permission(current_user, "x"):
    # ...
```

---

## 📚 API Reference

### UserRoleChecker

```python
class UserRoleChecker:
    @staticmethod
    def is_admin(user: Optional[models.User]) -> bool
    
    @staticmethod
    def is_guest(user: Optional[models.User]) -> bool
    
    @staticmethod
    def is_moderator(user: Optional[models.User]) -> bool
    
    @staticmethod
    def is_viewer(user: Optional[models.User]) -> bool
    
    @staticmethod
    def get_user_type(user: Optional[models.User]) -> UserType
```

### PermissionChecker

```python
class PermissionChecker:
    @staticmethod
    def has_permission(user: Optional[models.User], permission: str) -> bool
    
    @staticmethod
    def has_any(user: Optional[models.User], permissions: List[str]) -> bool
    
    @staticmethod
    def has_all(user: Optional[models.User], permissions: List[str]) -> bool
    
    @staticmethod
    def get_permissions(user: Optional[models.User]) -> Dict[str, bool]
```

### ResourceOwnershipChecker

```python
class ResourceOwnershipChecker:
    @staticmethod
    def can_access_note(user: Optional[models.User], note: Optional[models.Note]) -> bool
    
    @staticmethod
    def can_access_task(user: Optional[models.User], task: Optional[models.Task]) -> bool
    
    @staticmethod
    def is_owner(user: Optional[models.User], resource_owner_id: Optional[str]) -> bool
```

---

## 🚀 Getting Started

1. **Import the utilities:**
   ```python
   from app.utils.user_roles import (
       is_admin, is_guest,
       PermissionChecker,
       UserRoleChecker, UserType,
       ResourceOwnershipChecker
   )
   ```

2. **Use in endpoints:**
   ```python
   if not is_admin(current_user):
       raise HTTPException(403, "Admin only")
   ```

3. **Create reusable dependencies:**
   ```python
   def require_admin(current_user = Depends(get_current_user)):
       if not is_admin(current_user):
           raise HTTPException(403, "Admin only")
       return current_user
   ```

4. **Protect endpoints:**
   ```python
   @app.delete("/users/{id}")
   async def delete_user(
       user_id: str,
       current_user = Depends(require_admin),
   ):
       # Permission checked automatically
   ```

---

## 📞 Support

For questions or issues:

1. Check the **Usage Guide** at `/docs/USER_ROLES_USAGE_GUIDE.md`
2. Review the **module docstrings** in `/app/utils/user_roles.py`
3. Check **examples** in the API code

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 6, 2026 | Initial release - All core utilities |

---

**Status:** ✅ Production Ready  
**Last Updated:** February 6, 2026  
**Maintainer:** API Team
