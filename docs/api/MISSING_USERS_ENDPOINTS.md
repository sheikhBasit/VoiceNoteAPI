# 🚨 MISSING USERS & ADMIN ENDPOINTS ANALYSIS

**Date:** February 6, 2026  
**Status:** Critical Issues Found

---

## 📋 PROBLEM SUMMARY

Your concerns are **100% VALID**:

1. ✅ **DELETE /me exists** - BUT has **hard & soft delete options** (should only soft-delete)
2. ❌ **NO DELETE /users/{user_id} for admin** - MISSING (currently only soft-deletes)
3. ❌ **NO pure LIST users endpoint** - MISSING (only admin panel exists)
4. ❌ **Missing critical user management endpoints**

---

## 🔴 CRITICAL ISSUES FOUND

### ISSUE #1: DELETE /me Has Hard Delete (DANGEROUS)
**Location:** `/app/api/users.py` lines 292-323

```python
@router.delete("/me")
def delete_user_account(
    hard: bool = False,        # ⚠️ ALLOWS HARD DELETE!
    admin_id: Optional[str] = None,
    ...
):
    if hard:
        # Performs HARD DELETE (irreversible!)
        result = DeletionService.hard_delete_user(db, user_id, admin_id=admin_id)
    else:
        # Soft delete only
        result = DeletionService.soft_delete_user(db, user_id, ...)
```

**Problem:** Users can request hard deletion of their own account
- Should NEVER allow hard delete via `/me` endpoint
- Hard delete should be ADMIN-ONLY with approval process
- Current implementation compromises data integrity

**Fix:** Remove `hard` parameter from DELETE /me endpoint

---

### ISSUE #2: Missing Admin User Deletion Endpoint
**Status:** Partially Implemented (Soft Delete Only)

**Current:**
- ✅ `DELETE /admin/users/{user_id}` EXISTS in admin.py (line 298)
- ✅ Performs soft-delete only (correct!)
- ❌ Missing hard-delete for admins

**Missing:**
- ❌ No hard-delete endpoint for admins
- ❌ No restoration endpoint for soft-deleted users
- ❌ No bulk user deletion

**Recommendation:** Add hard-delete admin endpoint

---

### ISSUE #3: Missing List Users Endpoints
**Current Endpoints:**

| Endpoint | Location | Purpose |
|----------|----------|---------|
| ✅ GET /admin/users | admin.py:117 | List all users (admin only, paginated) |
| ❌ GET /users (public) | MISSING | List active users (public, paginated) |
| ✅ GET /users/search | users.py:191 | Search users by name/email |
| ❌ GET /users/{user_id} | MISSING | Get specific user profile |
| ❌ GET /admin/users/{user_id} | MISSING | Admin view of user details |

**Problem:** No public list endpoint for users (e.g., for team collaboration features)

---

### ISSUE #4: Missing User Detail Endpoints

**Missing Endpoints:**
```
GET    /api/v1/users/{user_id}                  Get user by ID (public)
GET    /api/v1/admin/users/{user_id}            Admin view user details
GET    /api/v1/admin/users/{user_id}/devices    View user's devices
GET    /api/v1/admin/users/{user_id}/audit      View user's audit log
DELETE /api/v1/admin/users/{user_id}/hard       Hard delete user (admin only)
PATCH  /api/v1/admin/users/{user_id}/restore    Restore soft-deleted user
PATCH  /api/v1/admin/users/{user_id}/block      Block/unblock user
```

---

## 📊 ENDPOINT COMPARISON

### Users Endpoints Currently Implemented

```
✅ POST   /api/v1/users/sync                      Authentication
✅ POST   /api/v1/users/logout                    Logout
✅ GET    /api/v1/users/verify-device             Email device verification
✅ GET    /api/v1/users/me                        Get current user profile
✅ GET    /api/v1/users/search                    Search users
✅ PATCH  /api/v1/users/me                        Update user settings
❌ DELETE /api/v1/users/me                        Delete account (HAS HARD DELETE BUG)
✅ PATCH  /api/v1/users/{user_id}/restore         Restore soft-deleted user
✅ PATCH  /api/v1/users/{user_id}/role            Update user role (admin)
```

### Admin Endpoints Currently Implemented

```
✅ POST   /api/v1/admin/users/{user_id}/make-admin      Promote to admin
✅ POST   /api/v1/admin/users/{user_id}/remove-admin    Demote admin
✅ GET    /api/v1/admin/users                           List all users
✅ GET    /api/v1/admin/users/stats                     User statistics
✅ GET    /api/v1/admin/admins                          List all admins
❌ DELETE /api/v1/admin/users/{user_id}/hard           Hard delete (MISSING)
❌ GET    /api/v1/admin/users/{user_id}                 User details (MISSING)
❌ GET    /api/v1/admin/users/{user_id}/devices         User devices (MISSING)
```

---

## 🎯 REQUIRED ENDPOINTS (PRIORITY ORDER)

### PRIORITY 1: CRITICAL (Fix Immediately)
```
1. FIX: DELETE /api/v1/users/me
   - Remove hard parameter
   - Only allow soft-delete
   - Prevent user self-destruction

2. ADD: DELETE /api/v1/admin/users/{user_id}/hard
   - Hard delete with admin approval
   - Audit trail required
   - Cannot be reversed
```

### PRIORITY 2: HIGH (Add Soon)
```
3. ADD: GET /api/v1/users/{user_id}
   - Get specific user profile
   - Public (only active, non-deleted users)
   - Basic info only

4. ADD: GET /api/v1/admin/users/{user_id}
   - Admin detailed view
   - Include audit logs
   - Include device list

5. ADD: PATCH /api/v1/admin/users/{user_id}/restore
   - Restore soft-deleted user
   - Reactivate account
   - Restore soft-deleted notes
```

### PRIORITY 3: MEDIUM (Add Later)
```
6. ADD: GET /api/v1/admin/users/{user_id}/devices
   - List user's authorized devices
   - Show device history
   - Allow device removal

7. ADD: GET /api/v1/admin/users/{user_id}/audit
   - View user action audit trail
   - Show login history
   - Show content created/deleted

8. ADD: PATCH /api/v1/admin/users/{user_id}/block
   - Block/unblock user
   - Prevent login without deletion
   - Keep data intact
```

---

## 🛠️ IMPLEMENTATION GUIDE

### FIX 1: Remove Hard Delete from DELETE /me

**File:** `/app/api/users.py` line 292

**Current (WRONG):**
```python
@router.delete("/me")
def delete_user_account(
    hard: bool = False,  # ⚠️ REMOVE THIS
    admin_id: Optional[str] = None,  # ⚠️ REMOVE THIS
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user),
    _sig: bool = Depends(verify_device_signature)
):
```

**Should Be (CORRECT):**
```python
@router.delete("/me")
def delete_user_account(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user),
    _sig: bool = Depends(verify_device_signature)
):
    """DELETE /me: Soft-delete user account (reversible)"""
    user_id = current_user.id
    result = DeletionService.soft_delete_user(
        db, user_id, 
        deleted_by=user_id, 
        reason="User self-deletion"
    )
    # ... rest of code
```

---

### ADD 1: GET /users/{user_id} (Public Profile)

**File:** `/app/api/users.py` (add after line 191)

```python
@router.get("/{user_id}", response_model=user_schema.UserResponse)
@limiter.limit("60/minute")
def get_user_profile_by_id(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    GET /{user_id}: Get public user profile
    
    Returns basic info about a user (if active)
    Only includes public fields (name, email, created_at)
    """
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.is_deleted == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found"
        )
    
    return user
```

---

### ADD 2: DELETE /admin/users/{user_id}/hard (Admin Hard Delete)

**File:** `/app/api/admin.py` (add after line 350)

```python
@router.delete("/users/{user_id}/hard")
async def hard_delete_user_as_admin(
    user_id: str,
    confirmation: str = Query("", description="Must equal user_id for confirmation"),
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
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
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_delete_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_delete_users' is missing"
        )
    
    # Safety check: require confirmation
    if confirmation != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation mismatch: confirmation must equal user_id"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID '{user_id}' not found"
        )
    
    # Perform hard delete via service
    result = DeletionService.hard_delete_user(
        db=db, 
        user_id=user_id, 
        admin_id=admin_user.id
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hard delete failed: {result.get('error', 'Unknown error')}"
        )
    
    AdminManager.log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="HARD_DELETE_USER",
        target_id=user_id,
        details={
            "reason": reason,
            "notes_deleted": result.get("notes_deleted", 0),
            "tasks_deleted": result.get("tasks_deleted", 0)
        }
    )
    
    return {
        "status": "success",
        "message": "User permanently deleted (irreversible)",
        "user_id": user_id,
        "deleted_items": {
            "notes": result.get("notes_deleted", 0),
            "tasks": result.get("tasks_deleted", 0),
            "deleted_at": int(time.time() * 1000)
        }
    }
```

---

### ADD 3: GET /admin/users/{user_id} (Admin Detailed View)

**File:** `/app/api/admin.py` (add after line 175)

```python
@router.get("/users/{user_id}")
async def get_user_details_admin(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
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
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_view_all_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_view_all_users' is missing"
        )
    
    from sqlalchemy.orm import joinedload
    
    user = db.query(models.User).options(
        joinedload(models.User.wallet),
        joinedload(models.User.plan)
    ).filter(models.User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found"
        )
    
    # Count user content
    notes_count = db.query(models.Note).filter(
        models.Note.user_id == user_id
    ).count()
    tasks_count = db.query(models.Task).filter(
        models.Task.user_id == user_id
    ).count()
    
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": user.is_admin,
            "admin_permissions": user.admin_permissions if user.is_admin else None,
            "is_deleted": user.is_deleted,
            "deleted_at": user.deleted_at if user.is_deleted else None,
            "created_at": user.created_at,
            "last_login": user.last_login,
        },
        "subscription": {
            "plan": user.plan.name if user.plan else "NONE",
            "tier": user.tier.value if user.tier else "GUEST",
            "balance": user.wallet.balance if user.wallet else 0,
            "monthly_limit": user.wallet.monthly_limit if user.wallet else 0,
            "used_this_month": user.wallet.used_this_month if user.wallet else 0
        },
        "devices": user.authorized_devices or [],
        "content": {
            "notes_count": notes_count,
            "tasks_count": tasks_count
        },
        "usage": user.usage_stats or {},
        "timestamp": int(time.time() * 1000)
    }
```

---

### ADD 4: PATCH /admin/users/{user_id}/restore (Admin Restore)

**File:** `/app/api/admin.py` (add after hard delete endpoint)

```python
@router.patch("/users/{user_id}/restore")
async def restore_user_as_admin(
    user_id: str,
    reason: str = Query(""),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_active_admin)
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
            detail="Permission denied: Administrative privileges required"
        )
    
    if not AdminManager.has_permission(admin_user, "can_manage_admins"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: Required permission 'can_manage_admins' is missing"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found"
        )
    
    if not user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not deleted"
        )
    
    # Restore user
    user.is_deleted = False
    user.deleted_at = None
    
    # Restore user's notes
    db.query(models.Note).filter(
        models.Note.user_id == user_id,
        models.Note.is_deleted == True
    ).update(
        {"is_deleted": False, "deleted_at": None}
    )
    
    db.commit()
    
    AdminManager.log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="RESTORE_USER",
        target_id=user_id,
        details={"reason": reason}
    )
    
    return {
        "status": "success",
        "message": "User account restored",
        "user_id": user_id,
        "restored_at": int(time.time() * 1000)
    }
```

---

## 📋 IMPLEMENTATION CHECKLIST

- [ ] **CRITICAL 1:** Remove `hard` parameter from DELETE /me
- [ ] **CRITICAL 2:** Add DELETE /admin/users/{user_id}/hard endpoint
- [ ] **HIGH 1:** Add GET /users/{user_id} endpoint
- [ ] **HIGH 2:** Add GET /admin/users/{user_id} endpoint
- [ ] **HIGH 3:** Add PATCH /admin/users/{user_id}/restore endpoint
- [ ] **MEDIUM 1:** Add GET /admin/users/{user_id}/devices endpoint
- [ ] **MEDIUM 2:** Add GET /admin/users/{user_id}/audit endpoint
- [ ] **MEDIUM 3:** Add PATCH /admin/users/{user_id}/block endpoint

---

## 🧪 TEST ENDPOINTS (After Implementation)

```bash
# Fix: Remove hard delete from /me
curl -X DELETE "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN"

# Test: Get user by ID
curl "http://localhost:8000/api/v1/users/user_001"

# Test: Admin get user details
curl "http://localhost:8000/api/v1/admin/users/user_001" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Test: Admin hard delete
curl -X DELETE "http://localhost:8000/api/v1/admin/users/user_001/hard?confirmation=user_001&reason=test" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Test: Admin restore
curl -X PATCH "http://localhost:8000/api/v1/admin/users/user_001/restore" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 🎯 SUMMARY

| Issue | Status | Priority | Fix |
|-------|--------|----------|-----|
| DELETE /me has hard delete | 🔴 Critical | URGENT | Remove hard parameter |
| Missing admin hard delete | 🔴 Critical | URGENT | Add /admin/users/{id}/hard |
| Missing user detail GET | 🟡 High | Soon | Add /users/{id} |
| Missing admin detail GET | 🟡 High | Soon | Add /admin/users/{id} |
| Missing restore endpoint | 🟡 High | Soon | Add /admin/users/{id}/restore |
| Missing devices list | 🟠 Medium | Later | Add /admin/users/{id}/devices |
| Missing audit log view | 🟠 Medium | Later | Add /admin/users/{id}/audit |
| Missing block endpoint | 🟠 Medium | Later | Add /admin/users/{id}/block |

---

## ✅ READY TO IMPLEMENT?

All code templates are provided above. You can:
1. Apply the fixes/additions directly
2. Test each endpoint
3. Update tests accordingly

Would you like me to implement all these endpoints now?
