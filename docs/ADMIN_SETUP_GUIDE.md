# 🔐 Admin Account Setup Guide

**Purpose:** Create and manage admin credentials for your VoiceNote API  
**Time Required:** 5 minutes  
**Difficulty:** Easy  

---

## 🚀 Quick Admin Account Creation

### Option 1: Via SQL (Fastest - Recommended)

```bash
# 1. Open database shell
make db-shell

# 2. Run these SQL commands one by one:

-- Create admin user
INSERT INTO users (
    id,
    name,
    email,
    device_token,
    is_admin,
    admin_permissions,
    admin_created_at,
    created_at,
    is_active
)
VALUES (
    'admin_main',
    'Super Admin',
    'admin@voicenote.app',
    'token_admin_main',
    true,
    '{"can_manage_users": true, "can_manage_admins": true, "can_view_analytics": true, "can_moderate_content": true}',
    1707256800000,
    1707256800000,
    true
);

-- Verify it was created
SELECT id, name, email, is_admin FROM users WHERE is_admin = true;

# 3. Exit database
\q
```

### Option 2: Via API (For Testing)

```bash
# 1. Register a regular account
curl -X POST http://localhost:8000/api/v1/users/sync \
  -H "Content-Type: application/json" \
  -d '{
    "id": "admin_user",
    "name": "Administrator",
    "email": "admin@example.com",
    "token": "token_admin_user",
    "timezone": "UTC"
  }'

# Expected response:
# {
#   "user": {
#     "id": "admin_user",
#     "name": "Administrator",
#     "email": "admin@example.com",
#     "is_admin": false
#   },
#   "access_token": "..."
# }

# 2. Manually upgrade to admin via SQL (see Option 1)
```

### Option 3: Via Database GUI (pgAdmin)

```
1. Open: http://localhost:5050
2. Server: localhost:5432
3. Username: dev
4. Password: dev
5. Database: voicenote_dev
6. Table: users
7. Insert Row with:
   - id: admin_main
   - name: Super Admin
   - email: admin@voicenote.app
   - device_token: token_admin_main
   - is_admin: true
   - admin_permissions: {"can_manage_users": true, ...}
```

---

## 📋 Admin Credentials

### Default Admin Account (After Creation)

```
ID:    admin_main
Name:  Super Admin
Email: admin@voicenote.app
Token: token_admin_main
Permissions: Full (all operations)
```

### Alternative Admin Account (For Testing)

```
ID:    admin_test
Name:  Test Admin
Email: test_admin@voicenote.app
Token: token_admin_test
Permissions: Moderator (limited operations)
```

---

## 🔑 Admin Permissions

### Full Admin (can_manage_admins=true)
```json
{
  "can_manage_users": true,
  "can_manage_admins": true,
  "can_view_analytics": true,
  "can_moderate_content": true,
  "can_manage_system": true
}
```

### Moderator (limited)
```json
{
  "can_moderate_content": true,
  "can_view_analytics": false,
  "can_manage_admins": false
}
```

### Viewer (read-only)
```json
{
  "can_view_analytics": true,
  "can_moderate_content": false,
  "can_manage_admins": false
}
```

---

## 🧪 Test Admin Access via Swagger

### Step 1: Get Admin Token

```bash
# In Swagger: http://localhost:8000/docs

# Find: POST /api/v1/users/sync
# Click "Try it out"
# Fill in:
{
  "id": "admin_main",
  "name": "Super Admin",
  "email": "admin@voicenote.app",
  "token": "token_admin_main"
}
# Click Execute

# Copy the access_token from response
```

### Step 2: Authorize in Swagger

```
1. Click green "Authorize" button
2. Paste: Bearer <YOUR_ACCESS_TOKEN>
3. Click "Authorize"
```

### Step 3: Test Admin Endpoints

```
In Swagger, find "Admin" section:

GET /api/v1/admin/users - List all users
POST /api/v1/admin/users/{user_id}/make-admin - Promote user
GET /api/v1/admin/stats - View analytics
POST /api/v1/admin/system/settings - Manage settings
... and more
```

---

## 🛠️ Create Additional Admins

### Promote Existing User to Admin

```bash
# Via Swagger:
# 1. Get admin token (see above)
# 2. Find: POST /api/v1/admin/users/{user_id}/make-admin
# 3. Click "Try it out"
# 4. Enter user_id: "user_to_promote"
# 5. Select level: "full" or "moderator"
# 6. Click Execute

# Via SQL:
make db-shell
UPDATE users 
SET is_admin = true, 
    admin_permissions = '{"can_manage_users": true, ...}'
WHERE id = 'user_to_promote';
\q
```

### Remove Admin Rights

```bash
# Via SQL:
make db-shell
UPDATE users 
SET is_admin = false, 
    admin_permissions = '{}'
WHERE id = 'admin_to_remove';
\q

# Via Swagger:
# POST /api/v1/admin/users/{user_id}/remove-admin
```

---

## 📊 Admin Actions Tracked

All admin actions are logged in `admin_action_logs` table:

```
- User management (create, modify, delete)
- Permission changes
- Content moderation
- System settings changes
- Security actions
- Financial transactions
```

View logs via:
```bash
# Via SQL:
make db-shell
SELECT admin_id, action, target_id, created_at FROM admin_action_logs 
ORDER BY created_at DESC LIMIT 10;

# Via Admin API:
GET /api/v1/admin/action-logs
```

---

## 🔐 Admin Login Methods

Your system supports multiple authentication methods:

### Method 1: Device Token (App)
```bash
curl -X POST http://localhost:8000/api/v1/users/sync \
  -H "Content-Type: application/json" \
  -d '{
    "id": "admin_main",
    "token": "token_admin_main"
  }'
```

### Method 2: Web UI Login (Optional)
- Requires: `password_hash` field set on user
- Implementation: Separate admin dashboard (if built)

### Method 3: OAuth (Optional)
- Can integrate Google, GitHub, etc.
- Not currently implemented

---

## 🚀 Admin Endpoints Overview

### User Management
```
GET    /api/v1/admin/users           - List all users
GET    /api/v1/admin/users/{id}      - Get user details
POST   /api/v1/admin/users/{id}/make-admin    - Promote user
POST   /api/v1/admin/users/{id}/remove-admin  - Demote user
DELETE /api/v1/admin/users/{id}      - Delete user
```

### Analytics & Reporting
```
GET /api/v1/admin/stats              - System statistics
GET /api/v1/admin/analytics/users    - User analytics
GET /api/v1/admin/analytics/content  - Content analytics
GET /api/v1/admin/action-logs        - Admin action logs
```

### System Management
```
GET    /api/v1/admin/system/health   - System health check
GET    /api/v1/admin/system/settings - Get system settings
POST   /api/v1/admin/system/settings - Update settings
GET    /api/v1/admin/system/cache    - Cache statistics
```

### Content Moderation
```
GET /api/v1/admin/moderation/queue   - Pending reviews
POST /api/v1/admin/moderation/{id}/approve   - Approve content
POST /api/v1/admin/moderation/{id}/reject    - Reject content
```

---

## 📝 Admin User Schema

When viewing admin users in database:

```json
{
  "id": "admin_main",
  "name": "Super Admin",
  "email": "admin@voicenote.app",
  "device_token": "token_admin_main",
  "is_admin": true,
  "admin_permissions": {
    "can_manage_users": true,
    "can_manage_admins": true,
    "can_view_analytics": true,
    "can_moderate_content": true,
    "can_manage_system": true
  },
  "admin_created_at": 1707256800000,
  "admin_last_action": 1707256800000,
  "created_at": 1707256800000,
  "is_active": true
}
```

---

## ✅ Setup Checklist

- [ ] Decide on admin account details
- [ ] Create admin account (via SQL option 1)
- [ ] Verify creation: `SELECT * FROM users WHERE is_admin=true`
- [ ] Test via Swagger: POST /api/v1/users/sync
- [ ] Get access token
- [ ] Authorize in Swagger
- [ ] Test admin endpoint: GET /api/v1/admin/stats
- [ ] Create additional admins as needed
- [ ] Document credentials securely

---

## 🔒 Security Best Practices

### DO:
✅ Use strong, unique device tokens  
✅ Log all admin actions  
✅ Audit admin permissions regularly  
✅ Use different admins for different tasks  
✅ Revoke access when admin leaves  
✅ Keep email addresses secure  

### DON'T:
❌ Share admin credentials  
❌ Use weak tokens (like "admin123")  
❌ Store credentials in code  
❌ Grant unnecessary permissions  
❌ Ignore action logs  
❌ Leave inactive admins  

---

## 🆘 Troubleshooting

### "Permission denied" error
```bash
# Check admin permissions in database
make db-shell
SELECT id, is_admin, admin_permissions FROM users WHERE id='admin_main';

# If is_admin is false or permissions empty:
UPDATE users 
SET is_admin = true,
    admin_permissions = '{"can_manage_users": true, "can_manage_admins": true, ...}'
WHERE id = 'admin_main';
```

### "Invalid token" error
```bash
# Make sure token is included in request:
curl -H "X-User-ID: admin_main" http://localhost:8000/api/v1/admin/stats

# Or use Bearer token:
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/admin/stats
```

### Admin endpoint not found
```bash
# Check if admin router is loaded
curl http://localhost:8000/docs
# Should show "Admin" section with endpoints

# If not showing, restart services:
make restart
```

---

## 📚 Related Files

- **Admin utilities:** `app/utils/admin_utils.py`
- **Admin API:** `app/api/admin.py`
- **Database models:** `app/db/models.py`
- **Auth service:** `app/services/auth_service.py`

---

## 🎉 You're Ready!

Your admin system is ready to use:

✅ Admin database structure in place  
✅ Admin endpoints available  
✅ Permission system working  
✅ Audit logging enabled  

**Next steps:**
1. Create your first admin account (via SQL)
2. Test via Swagger UI
3. Start managing your system!

---

## 📞 Quick Reference

### Create Admin (SQL)
```sql
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES ('admin_main', 'Super Admin', 'admin@voicenote.app', 'token_admin_main', true, '{"can_manage_users": true, "can_manage_admins": true, "can_view_analytics": true, "can_moderate_content": true}', 1707256800000, 1707256800000, true);
```

### Verify Admin
```bash
make db-shell
SELECT id, name, is_admin FROM users WHERE is_admin=true;
\q
```

### Test Admin Access
```bash
# In Swagger: http://localhost:8000/docs
# POST /api/v1/users/sync with id: admin_main
# GET /api/v1/admin/stats to verify
```

---

**Created:** February 6, 2026  
**Status:** Ready for admin setup  
**Next:** Create your first admin account  

