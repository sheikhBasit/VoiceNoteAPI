# 🔧 Refactoring Guide: Updating Existing Endpoints with User Roles Module

**Guide Version:** 1.0  
**Date:** February 6, 2026  
**Status:** Ready for Implementation

---

## 📖 Overview

This guide shows **step-by-step** how to refactor existing endpoints to use the new modular user roles utilities.

### Benefits of Refactoring

✅ **Cleaner Code** - Less boilerplate  
✅ **Consistency** - Same patterns everywhere  
✅ **Maintainability** - Easy to update permission logic  
✅ **Safety** - Handles None gracefully  
✅ **Readability** - Self-documenting code  

---

## 🎯 Pattern 1: Admin-Only Endpoints

### Problem: Repeated Admin Checks

Many endpoints check `current_user.is_admin`:

```python
# In 15 different endpoints...
if not current_user.is_admin:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only admins can perform this action"
    )
```

### Solution: Reusable Dependency

**Step 1:** Create the dependency once (in a utilities file):

```python
from fastapi import Depends, HTTPException, status
from app.utils.user_roles import is_admin

def require_admin(current_user = Depends(get_current_user)):
    """
    Dependency: Verify user is admin.
    Raises 403 if not admin.
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
```

**Step 2:** Use the dependency in endpoints:

```python
# Before (verbose)
@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(403, "Admin only")
    # ... rest of logic

# After (clean)
@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),
):
    # Admin check already done! Just implement logic
    # ... rest of logic
```

---

## 🎯 Pattern 2: Permission-Based Endpoints

### Problem: Complex Permission Checks

```python
# Hard to understand, fragile if is_admin is None
if current_user.is_admin and current_user.admin_permissions.get("can_delete_users"):
    # ...

# Repeated in many places
```

### Solution: Use PermissionChecker

**Step 1:** Create a generic permission dependency:

```python
from fastapi import Depends, HTTPException, status
from app.utils.user_roles import PermissionChecker

def require_permission(permission_name: str):
    """
    Dependency factory: Verify user has permission.
    
    Usage:
        @app.delete("/...")
        async def delete_users(
            current_user = Depends(require_permission("can_delete_users")),
        ):
            ...
    """
    def check(current_user = Depends(get_current_user)):
        if not PermissionChecker.has_permission(current_user, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' required"
            )
        return current_user
    return check
```

**Step 2:** Use in endpoints:

```python
# Before (unclear)
@app.delete("/api/v1/users")
async def delete_users(
    current_user = Depends(get_current_user),
):
    if not current_user.is_admin or not current_user.admin_permissions.get("can_delete_users"):
        raise HTTPException(403)
    # ...

# After (crystal clear)
@app.delete("/api/v1/users")
async def delete_users(
    current_user = Depends(require_permission("can_delete_users")),
):
    # Permission automatically verified
    # ...
```

---

## 🎯 Pattern 3: Resource Ownership Checks

### Problem: Scattered Ownership Logic

```python
# In endpoint 1
if current_user.is_admin or note.user_id == current_user.user_id:
    # Allow access

# In endpoint 2
if current_user.is_admin or task.user_id == str(current_user.user_id):
    # Allow access

# In endpoint 3
if not (current_user.is_admin or resource.created_by == current_user.user_id):
    raise HTTPException(403)
    # ...
```

### Solution: Use ResourceOwnershipChecker

**Step 1:** Use the checker in endpoints:

```python
from app.utils.user_roles import ResourceOwnershipChecker

@app.get("/api/v1/notes/{note_id}")
async def get_note(
    note_id: str,
    current_user = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id).first()
    
    if not note:
        raise HTTPException(404, "Not found")
    
    # Simple, consistent check
    if not ResourceOwnershipChecker.can_access_note(current_user, note):
        raise HTTPException(403, "Access denied")
    
    return note
```

**Step 2:** Create reusable dependencies for resources:

```python
def require_note_ownership(note_id: str):
    """Verify user can access note"""
    async def check(
        current_user = Depends(get_current_user),
        session: Session = Depends(get_db),
    ):
        note = session.query(Note).filter(Note.id == note_id).first()
        
        if not note:
            raise HTTPException(404, "Note not found")
        
        if not ResourceOwnershipChecker.can_access_note(current_user, note):
            raise HTTPException(403, "Access denied")
        
        return note
    return check

# Usage:
@app.put("/api/v1/notes/{note_id}")
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    current_user = Depends(get_current_user),
    note = Depends(require_note_ownership(note_id)),
):
    # Note access already verified!
    # ...
```

---

## 🎯 Pattern 4: Type-Based Logic

### Problem: Conditional Logic Everywhere

```python
# In endpoint logic
if current_user.is_admin:
    if current_user.admin_permissions.get("can_view_analytics"):
        # Show analytics
    else:
        # Show limited view
else:
    # Show guest view
```

### Solution: Use UserRoleChecker.get_user_type()

**Step 1:** Use UserType for clean conditionals:

```python
from app.utils.user_roles import UserRoleChecker, UserType

@app.get("/api/v1/dashboard")
async def get_dashboard(current_user = Depends(get_current_user)):
    user_type = UserRoleChecker.get_user_type(current_user)
    
    # Clear intent
    if user_type == UserType.ADMIN:
        return admin_dashboard()
    elif user_type == UserType.MODERATOR:
        return moderator_dashboard()
    elif user_type == UserType.VIEWER:
        return viewer_dashboard()
    else:  # GUEST
        return guest_dashboard()
```

---

## 📋 Refactoring Checklist

### For Admin-Only Endpoints

- [ ] Identify all endpoints that check `current_user.is_admin`
- [ ] Create `require_admin` dependency
- [ ] Replace check with `Depends(require_admin)`
- [ ] Remove manual admin check from endpoint
- [ ] Test the endpoint
- [ ] Update endpoint docstring if needed

### For Permission-Based Endpoints

- [ ] Identify all permission checks
- [ ] List all unique permissions used
- [ ] Create `require_permission(perm)` dependency
- [ ] Replace checks with `Depends(require_permission(...))`
- [ ] Test each endpoint
- [ ] Document permissions in endpoint docstring

### For Resource Access

- [ ] Identify all ownership checks
- [ ] Create resource-specific dependencies
- [ ] Replace manual checks with dependencies
- [ ] Ensure admin bypass works
- [ ] Test ownership logic

### For User Type Logic

- [ ] Identify conditional logic based on admin/guest
- [ ] Replace with `UserRoleChecker.get_user_type()`
- [ ] Use clear switch/if-elif logic
- [ ] Add comments for clarity

---

## 📝 Complete Refactoring Example

### Before: Mixed, Hard to Maintain

```python
# users.py endpoint
@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a user"""
    
    # Admin check (duplicated in 10+ endpoints)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete users"
        )
    
    # Permission check (inconsistent logic)
    if not current_user.admin_permissions or \
       not current_user.admin_permissions.get("can_delete_users"):
        raise HTTPException(
            status_code=403,
            detail="No permission"
        )
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Delete
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted"}
```

### After: Clean, Maintainable

```python
# dependencies.py
from app.utils.user_roles import is_admin, PermissionChecker

def require_admin(current_user = Depends(get_current_user)):
    """Verify user is admin"""
    if not is_admin(current_user):
        raise HTTPException(403, "Admin required")
    return current_user

def require_permission(perm: str):
    """Verify user has permission"""
    def check(current_user = Depends(get_current_user)):
        if not PermissionChecker.has_permission(current_user, perm):
            raise HTTPException(403, f"Permission '{perm}' required")
        return current_user
    return check

# users.py endpoint
@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),  # Admin verified
    current_user = Depends(require_permission("can_delete_users")),  # Permission verified
    db: Session = Depends(get_db),
):
    """Delete a user (admin only, requires can_delete_users permission)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted"}
```

**Changes:**
- ✅ Admin check moved to dependency
- ✅ Permission check centralized
- ✅ Logic is clear and maintainable
- ✅ Can reuse dependencies in other endpoints
- ✅ Endpoint focuses on business logic, not security

---

## 🚀 Implementation Steps

### Phase 1: Foundation (1-2 hours)

1. Review the user roles module at `/app/utils/user_roles.py`
2. Create `/app/api/dependencies.py` with reusable dependencies
3. Document all permissions in use

### Phase 2: High-Impact Endpoints (2-3 hours)

1. Refactor admin-only endpoints (10-15 endpoints)
2. Replace with `Depends(require_admin)`
3. Test each endpoint

### Phase 3: Permission-Based Endpoints (3-4 hours)

1. Identify unique permissions
2. Create permission dependencies
3. Refactor endpoints using permissions
4. Test thoroughly

### Phase 4: Resource Access (2-3 hours)

1. Create resource ownership dependencies
2. Refactor resource access checks
3. Verify admin bypass works
4. Test edge cases

### Phase 5: Polish (1-2 hours)

1. Review all endpoints
2. Update docstrings
3. Final testing
4. Update documentation

---

## ✅ Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Lines per endpoint** | 10-15 lines | 1-2 lines |
| **Permission checks** | Duplicated | Centralized |
| **Admin checks** | Inconsistent | Consistent |
| **Error handling** | Manual | Automatic |
| **Type safety** | Limited | Full |
| **Readability** | Low | High |
| **Maintainability** | Hard | Easy |
| **Test coverage** | Low | High |

---

## 📚 Related Documentation

- **Module Documentation:** `/docs/USER_ROLES_MODULE.md`
- **Usage Guide:** `/docs/USER_ROLES_USAGE_GUIDE.md`
- **Module Source:** `/app/utils/user_roles.py`

---

## ❓ FAQ

**Q: Will this refactoring break existing endpoints?**  
A: No. We're keeping the same security logic, just organizing it better.

**Q: How do I test the changes?**  
A: Run the existing curl tests in `/curl_all_tests_final.py` - they verify all endpoints.

**Q: Can I do this gradually?**  
A: Yes! Refactor one feature area at a time.

**Q: What if an endpoint has complex logic?**  
A: Dependencies handle all standard cases. For complex cases, use the utility classes directly.

**Q: How do I handle multiple permissions?**  
A: Use `PermissionChecker.has_any()` or `has_all()` for multiple checks.

---

**Status:** ✅ Ready for Implementation  
**Last Updated:** February 6, 2026
