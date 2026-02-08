# 🎯 User Roles Module - Quick Reference Card

**Keeping this in your editor toolbar for instant reference!**

---

## 🔐 Basic Usage

```python
from app.utils.user_roles import is_admin, is_guest

# Check if admin
if is_admin(user):
    # Grant admin access

# Check if guest (not admin)
if is_guest(user):
    # Show public features
```

---

## ✅ Common Patterns

### Pattern A: Admin-Only Endpoint

```python
@app.delete("/users/{id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),  # ← Checks admin
):
    # Admin verified, do the work
    pass
```

### Pattern B: Permission-Based

```python
@app.post("/admin/manage-roles")
async def manage_roles(
    current_user = Depends(require_permission("can_manage_roles")),
):
    # Permission verified
    pass
```

### Pattern C: Resource Ownership

```python
from app.utils.user_roles import ResourceOwnershipChecker

if not ResourceOwnershipChecker.can_access_note(user, note):
    raise HTTPException(403)
```

### Pattern D: Type-Based Logic

```python
from app.utils.user_roles import UserRoleChecker, UserType

user_type = UserRoleChecker.get_user_type(user)
if user_type == UserType.ADMIN:
    # Admin logic
```

---

## 📚 All Functions at a Glance

### UserRoleChecker (Determine User Type)

```python
UserRoleChecker.is_admin(user)        # → bool
UserRoleChecker.is_guest(user)        # → bool
UserRoleChecker.is_moderator(user)    # → bool
UserRoleChecker.is_viewer(user)       # → bool
UserRoleChecker.get_user_type(user)   # → UserType enum
```

### PermissionChecker (Check Permissions)

```python
PermissionChecker.has_permission(user, "can_delete_users")  # → bool
PermissionChecker.has_any(user, ["perm1", "perm2"])        # → bool
PermissionChecker.has_all(user, ["perm1", "perm2"])        # → bool
PermissionChecker.get_permissions(user)                     # → dict
```

### ResourceOwnershipChecker (Check Access)

```python
ResourceOwnershipChecker.can_access_note(user, note)       # → bool
ResourceOwnershipChecker.can_access_task(user, task)       # → bool
ResourceOwnershipChecker.is_owner(user, owner_id)          # → bool
```

### Convenience Functions

```python
from app.utils.user_roles import (
    is_admin,           # Quick admin check
    is_guest,           # Quick guest check
    has_permission,     # Quick permission check
    get_user_type,      # Get user type enum
)
```

---

## 🎯 User Types (UserType Enum)

```python
UserType.ADMIN       # Full system access
UserType.MODERATOR   # Content moderation
UserType.VIEWER      # Read-only analytics
UserType.GUEST       # Regular user (no special access)
```

---

## 🔑 All Available Permissions

```python
"can_view_all_users"        # View all users
"can_manage_users"          # Create/update/delete users
"can_delete_users"          # Delete users
"can_manage_admins"         # Grant/revoke admin status
"can_view_all_notes"        # View all notes
"can_delete_notes"          # Delete notes
"can_moderate_content"      # Review and moderate
"can_view_analytics"        # View analytics
"can_export_data"           # Export system data
"can_modify_system_settings"  # Change configuration
"can_manage_roles"          # Manage user roles
```

---

## 🚀 Create Reusable Dependencies

```python
# In dependencies.py
from app.utils.user_roles import is_admin, PermissionChecker

def require_admin(current_user = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(403, "Admin required")
    return current_user

def require_permission(perm: str):
    def check(current_user = Depends(get_current_user)):
        if not PermissionChecker.has_permission(current_user, perm):
            raise HTTPException(403, f"Permission '{perm}' required")
        return current_user
    return check

# Use anywhere:
@app.delete("/users/{id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),
):
    # Admin verified, do work
    pass
```

---

## ☑️ Safety Features

✅ **None-Safe** - Returns False/GUEST if user is None  
✅ **Graceful** - Never raises exceptions (except in Depends)  
✅ **Type-Safe** - Full type hints throughout  
✅ **Tested** - Production ready  

---

## 📖 Full Documentation

| Doc | Purpose | Location |
|-----|---------|----------|
| **Module** | Full API reference | `/docs/USER_ROLES_MODULE.md` |
| **Usage Guide** | 6+ detailed examples | `/docs/USER_ROLES_USAGE_GUIDE.md` |
| **Refactoring** | How to update endpoints | `/docs/REFACTORING_GUIDE.md` |
| **Source Code** | Implementation + comments | `/app/utils/user_roles.py` |

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: cannot import user_roles` | Check path is `/app/utils/user_roles.py` |
| `TypeError: is_admin() missing argument` | Pass user: `is_admin(current_user)` |
| `False when should be True` | Check user.is_admin = True in database |
| `Permission not working` | Verify permission name in `user.admin_permissions` |

---

## ⚡ Most Common Use Cases

```python
# 1. Admin-only endpoint
@app.delete("/users/{id}")
async def delete(user_id: str, current_user = Depends(require_admin)):
    pass

# 2. Permission-based endpoint
@app.post("/roles/manage")
async def manage(current_user = Depends(require_permission("can_manage_roles"))):
    pass

# 3. Owner-only endpoint
@app.put("/notes/{id}")
async def update(note_id: str, current_user = Depends(get_current_user)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not ResourceOwnershipChecker.can_access_note(current_user, note):
        raise HTTPException(403)
    # Update note...

# 4. Type-based logic
@app.get("/dashboard")
async def dashboard(current_user = Depends(get_current_user)):
    match UserRoleChecker.get_user_type(current_user):
        case UserType.ADMIN: return admin_view()
        case UserType.MODERATOR: return mod_view()
        case _: return guest_view()
```

---

## 🎓 Learning Path

1. **Start Here:** Read this quick reference (5 min)
2. **Understand:** Read `/docs/USER_ROLES_MODULE.md` (10 min)
3. **Practice:** Look at examples in `/docs/USER_ROLES_USAGE_GUIDE.md` (15 min)
4. **Implement:** Use refactoring guide in `/docs/REFACTORING_GUIDE.md` (varies)
5. **Reference:** Keep this card in your editor (forever)

---

## 💡 Pro Tips

1. **Always use dependencies** for standard checks (admin, permission)
2. **Create project-wide dependencies** in `/app/api/dependencies.py`
3. **Use utility classes** directly for complex scenarios
4. **Test ownership** with `ResourceOwnershipChecker.can_access_note()`
5. **Keep permissions simple** - one permission = one action
6. **Handle None gracefully** - all functions are None-safe
7. **Document permissions** in endpoint docstrings

---

## 📞 Support

- **API Reference:** Check `USER_ROLES_MODULE.md`
- **Examples:** Check `USER_ROLES_USAGE_GUIDE.md`
- **Refactoring:** Check `REFACTORING_GUIDE.md`
- **Source Code:** Check `app/utils/user_roles.py` with docstrings

---

**Created:** February 6, 2026  
**Status:** ✅ Quick Reference Ready  
**Keep this in your editor toolbar!**
