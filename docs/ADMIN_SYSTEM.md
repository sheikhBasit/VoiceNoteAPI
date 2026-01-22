# Admin Role & Permission System Documentation

## Overview

VoiceNote includes a comprehensive admin role system that allows administrators to:
- Manage users and their roles
- Moderate content across the platform
- View analytics and system statistics
- Export and analyze data
- Configure system-wide settings
- Control granular permissions for other admins

## Admin Features

### 1. User Management
- View all users in the system
- Promote/demote users to/from admin role
- Delete user accounts and associated data
- View user statistics and activity
- Search and filter users

### 2. Content Moderation
- View all notes across all users
- Delete inappropriate or policy-violating content
- Review and manage tasks
- Soft-delete content (preserves data for compliance)

### 3. Analytics & Reporting
- User count and activity metrics
- Content distribution analysis
- System health monitoring
- Admin activity audit logs

### 4. Permission Management
- Create custom admin roles with specific permissions
- Grant/revoke admin access
- Modify permissions dynamically
- Three predefined permission levels:
  - **Full Admin**: All permissions
  - **Moderator**: Content moderation only
  - **Viewer**: Read-only analytics access

## Admin Roles & Permission Levels

### Full Admin
```json
{
  "can_view_all_users": true,
  "can_delete_users": true,
  "can_view_all_notes": true,
  "can_delete_notes": true,
  "can_manage_admins": true,
  "can_view_analytics": true,
  "can_modify_system_settings": true,
  "can_moderate_content": true,
  "can_manage_roles": true,
  "can_export_data": true
}
```

### Moderator
```json
{
  "can_view_all_notes": true,
  "can_moderate_content": true,
  "can_delete_notes": true
}
```

### Viewer (Analytics Only)
```json
{
  "can_view_all_users": true,
  "can_view_all_notes": true,
  "can_view_analytics": true
}
```

## Admin API Endpoints

### User Management

#### Promote User to Admin
```http
POST /api/v1/admin/users/{user_id}/make-admin?level=full&current_admin_id=admin_001
```

**Permission Required:** `can_manage_admins`

**Query Parameters:**
- `user_id` (path): User to promote
- `level` (query): "full", "moderator", or "viewer"
- `current_admin_id` (query): Admin making the change

**Example Response:**
```json
{
  "status": "success",
  "message": "User promoted to full admin",
  "user": {
    "id": "user_001",
    "name": "John Doe",
    "email": "john@example.com",
    "is_admin": true,
    "admin_permissions": {
      "can_view_all_users": true,
      "can_delete_users": true,
      ...
    },
    "admin_created_at": 1705881600000
  }
}
```

#### Revoke Admin Role
```http
POST /api/v1/admin/users/{user_id}/remove-admin?current_admin_id=admin_001
```

**Permission Required:** `can_manage_admins`

**Response:**
```json
{
  "status": "success",
  "message": "Admin role revoked",
  "user": {
    "id": "user_001",
    "is_admin": false,
    "admin_permissions": {}
  }
}
```

#### List All Users
```http
GET /api/v1/admin/users?current_admin_id=admin_001&skip=0&limit=20
```

**Permission Required:** `can_view_all_users`

**Query Parameters:**
- `current_admin_id`: Admin requesting the list
- `skip`: Number of records to skip (pagination)
- `limit`: Number of records to return (max 100)

**Response:**
```json
{
  "total": 450,
  "skip": 0,
  "limit": 20,
  "users": [
    {
      "id": "user_001",
      "name": "John Doe",
      "email": "john@example.com",
      "is_admin": false,
      "primary_role": "STUDENT",
      "last_login": 1705881600000
    }
  ]
}
```

#### Get User Statistics
```http
GET /api/v1/admin/users/stats?current_admin_id=admin_001
```

**Permission Required:** `can_view_analytics`

**Response:**
```json
{
  "total_users": 1250,
  "admin_count": 5,
  "active_users": 1200,
  "deleted_users": 50,
  "timestamp": 1705881600000
}
```

### Content Moderation

#### View All Notes
```http
GET /api/v1/admin/notes?current_admin_id=admin_001&skip=0&limit=20
```

**Permission Required:** `can_view_all_notes`

**Response:**
```json
{
  "total": 5432,
  "skip": 0,
  "limit": 20,
  "notes": [
    {
      "id": "note_001",
      "user_id": "user_001",
      "title": "Meeting Notes",
      "timestamp": 1705881600000,
      "status": "PENDING",
      "is_deleted": false
    }
  ]
}
```

#### Delete Note (Content Moderation)
```http
DELETE /api/v1/admin/notes/{note_id}?current_admin_id=admin_001&reason=policy_violation
```

**Permission Required:** `can_delete_notes`

**Query Parameters:**
- `note_id` (path): Note to delete
- `current_admin_id`: Admin deleting the note
- `reason`: Reason for deletion (optional)

**Response:**
```json
{
  "status": "success",
  "message": "Note deleted",
  "note_id": "note_001"
}
```

#### Delete User Account
```http
DELETE /api/v1/admin/users/{user_id}?current_admin_id=admin_001&reason=policy_violation
```

**Permission Required:** `can_delete_users`

**Note:** This soft-deletes the user and all associated notes

**Response:**
```json
{
  "status": "success",
  "message": "User deleted",
  "user_id": "user_001"
}
```

### Permission Management

#### Update Admin Permissions
```http
PUT /api/v1/admin/permissions/{user_id}?current_admin_id=admin_001
```

**Permission Required:** `can_manage_admins`

**Request Body:**
```json
{
  "can_view_all_notes": true,
  "can_delete_notes": false,
  "can_manage_admins": false
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Permissions updated",
  "user": {
    "id": "user_001",
    "is_admin": true,
    "admin_permissions": {
      "can_view_all_notes": true,
      "can_delete_notes": false,
      ...
    }
  }
}
```

#### List All Admins
```http
GET /api/v1/admin/admins?current_admin_id=admin_001
```

**Permission Required:** `can_manage_admins`

**Response:**
```json
{
  "total": 5,
  "admins": [
    {
      "id": "admin_001",
      "name": "Super Admin",
      "email": "admin@voicenote.com",
      "admin_created_at": 1705881600000,
      "admin_permissions": { ... }
    }
  ]
}
```

### System Info

#### Get Admin Panel Status
```http
GET /api/v1/admin/status?current_admin_id=admin_001
```

**Permission Required:** `is_admin`

**Response:**
```json
{
  "status": "operational",
  "admin_id": "admin_001",
  "admin_name": "Super Admin",
  "permissions": {
    "can_view_all_users": true,
    ...
  },
  "last_action": 1705881600000,
  "created_at": 1705881600000,
  "timestamp": 1705881600000
}
```

## Creating the First Admin

### Method 1: Direct Database Update
```sql
UPDATE users 
SET is_admin = true, 
    admin_permissions = '{
      "can_view_all_users": true,
      "can_delete_users": true,
      "can_view_all_notes": true,
      "can_delete_notes": true,
      "can_manage_admins": true,
      "can_view_analytics": true,
      "can_modify_system_settings": true,
      "can_moderate_content": true,
      "can_manage_roles": true,
      "can_export_data": true,
      "created_at": ' || extract(epoch from now())::bigint || ',
      "granted_by": "system",
      "level": "full"
    }'::json,
    admin_created_at = extract(epoch from now())::bigint * 1000
WHERE id = 'your_user_id';
```

### Method 2: Using Python CLI
```python
from app.db.session import SessionLocal
from app.db import models
from app.utils.admin_utils import AdminManager

db = SessionLocal()
user = db.query(models.User).filter(models.User.id == "your_user_id").first()
AdminManager.grant_admin_role(db, "your_user_id", "system", "full")
print("✅ Admin role granted!")
```

## Admin Audit Logging

All admin actions are logged with:
- Admin ID
- Action type (CREATE, READ, UPDATE, DELETE, MANAGE)
- Target ID (user/note/task ID)
- Timestamp
- Additional details

**Future: Dedicated AdminAuditLog table**

```sql
CREATE TABLE admin_audit_logs (
  id SERIAL PRIMARY KEY,
  admin_id VARCHAR NOT NULL,
  action VARCHAR NOT NULL,
  target_id VARCHAR,
  details JSONB,
  timestamp BIGINT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Permission Verification Flow

```
Request with admin_id
    ↓
Check if user exists
    ↓
Check if is_admin = true
    ↓
Check admin_permissions for specific permission
    ↓
Execute action if authorized
    ↓
Log action to audit trail
```

## Security Best Practices

1. **Limited Admin Creation**
   - Only existing admins can promote new admins
   - First admin created via database or CLI
   - Regular reviews of admin list

2. **Permission Isolation**
   - Granular permissions prevent privilege escalation
   - Different levels for different roles
   - Never grant all permissions to moderators

3. **Audit Logging**
   - All admin actions logged
   - Can't be deleted or modified
   - Used for compliance and investigation

4. **Rate Limiting**
   - Admin endpoints have rate limiting
   - Prevents brute force and DoS attacks
   - Different limits for different actions

5. **Data Protection**
   - Soft deletes preserve data for compliance
   - Admin deletions logged with reason
   - 30-day retention before hard delete

## Error Handling

### 403 Forbidden
```json
{
  "detail": "Admin access required" | "Permission '{permission}' required"
}
```

### 404 Not Found
```json
{
  "detail": "User not found" | "Note not found"
}
```

### 400 Bad Request
```json
{
  "detail": "User {user_id} is not an admin" | "Invalid permission level"
}
```

## Testing Admin Features

### Example Test Scenario
```python
# Test 1: Create admin
admin = AdminManager.grant_admin_role(
    db=db,
    user_id="test_user_001",
    granted_by="system",
    permission_level="full"
)
assert admin.is_admin == True

# Test 2: Check permission
has_perm = AdminManager.has_permission(admin, "can_delete_users")
assert has_perm == True

# Test 3: Remove admin
revoked = AdminManager.revoke_admin_role(db, "test_user_001")
assert revoked.is_admin == False

# Test 4: Delete user as admin
response = client.delete(
    "/api/v1/admin/users/user_001?current_admin_id=admin_001"
)
assert response.status_code == 200
```

## Future Enhancements

1. **Admin Dashboard UI** - React/Vue frontend
2. **Advanced Analytics** - User behavior, content trends
3. **Automated Moderation** - ML-based content flagging
4. **Two-Factor Authentication** - For admin accounts
5. **Webhook Notifications** - Real-time admin alerts
6. **Bulk Operations** - Delete/export multiple items
7. **Admin Sessions** - Track login/logout activity
8. **Scheduled Tasks** - Automated maintenance jobs
9. **API Rate Limiting** - Per-admin quotas
10. **Data Export** - CSV/JSON export functionality

