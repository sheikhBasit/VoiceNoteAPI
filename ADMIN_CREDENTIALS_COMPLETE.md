# 🔐 Admin Credentials Reference

**Date:** February 6, 2026  
**Status:** Ready to Create  

---

## 📋 Pre-Configured Admin Accounts

### Account 1: Super Admin (Full Access)

| Property | Value |
|----------|-------|
| **ID** | `admin_main` |
| **Name** | Super Admin |
| **Email** | admin@voicenote.app |
| **Device Token** | token_admin_main |
| **Role** | Full Admin |
| **Permissions** | All permissions |

**Permissions JSON:**
```json
{
  "can_manage_users": true,
  "can_manage_admins": true,
  "can_view_analytics": true,
  "can_moderate_content": true,
  "can_manage_system": true
}
```

---

### Account 2: Moderator (Limited Access)

| Property | Value |
|----------|-------|
| **ID** | admin_moderator |
| **Name** | Content Moderator |
| **Email** | moderator@voicenote.app |
| **Device Token** | token_admin_moderator |
| **Role** | Moderator |
| **Permissions** | Moderation only |

**Permissions JSON:**
```json
{
  "can_moderate_content": true,
  "can_view_analytics": false,
  "can_manage_admins": false
}
```

---

### Account 3: Analytics Viewer (Read-Only)

| Property | Value |
|----------|-------|
| **ID** | admin_viewer |
| **Name** | Analytics Viewer |
| **Email** | viewer@voicenote.app |
| **Device Token** | token_admin_viewer |
| **Role** | Viewer |
| **Permissions** | Analytics only |

**Permissions JSON:**
```json
{
  "can_view_analytics": true,
  "can_moderate_content": false,
  "can_manage_admins": false
}
```

---

## 🗄️ Database Insert Commands

### Create All Three Accounts

```sql
-- Account 1: Super Admin
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES (
    'admin_main',
    'Super Admin',
    'admin@voicenote.app',
    'token_admin_main',
    true,
    '{"can_manage_users": true, "can_manage_admins": true, "can_view_analytics": true, "can_moderate_content": true, "can_manage_system": true}',
    1707256800000,
    1707256800000,
    true
);

-- Account 2: Moderator
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES (
    'admin_moderator',
    'Content Moderator',
    'moderator@voicenote.app',
    'token_admin_moderator',
    true,
    '{"can_moderate_content": true, "can_view_analytics": false, "can_manage_admins": false}',
    1707256800000,
    1707256800000,
    true
);

-- Account 3: Viewer
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES (
    'admin_viewer',
    'Analytics Viewer',
    'viewer@voicenote.app',
    'token_admin_viewer',
    true,
    '{"can_view_analytics": true, "can_moderate_content": false, "can_manage_admins": false}',
    1707256800000,
    1707256800000,
    true
);

-- Verify all created
SELECT id, name, email, is_admin FROM users WHERE is_admin = true;
```

---

## 🚀 One-Command Setup

```bash
# Copy and run in your shell:
cat << 'EOF' | make db-shell
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES 
('admin_main', 'Super Admin', 'admin@voicenote.app', 'token_admin_main', true, '{"can_manage_users": true, "can_manage_admins": true, "can_view_analytics": true, "can_moderate_content": true}', 1707256800000, 1707256800000, true),
('admin_moderator', 'Content Moderator', 'moderator@voicenote.app', 'token_admin_moderator', true, '{"can_moderate_content": true}', 1707256800000, 1707256800000, true),
('admin_viewer', 'Analytics Viewer', 'viewer@voicenote.app', 'token_admin_viewer', true, '{"can_view_analytics": true}', 1707256800000, 1707256800000, true);

SELECT id, name, email, is_admin FROM users WHERE is_admin = true;
EOF
```

---

## 🧪 Testing Admin Credentials

### Test with cURL

```bash
# 1. Get token for admin_main
curl -X POST http://localhost:8000/api/v1/users/sync \
  -H "Content-Type: application/json" \
  -d '{
    "id": "admin_main",
    "name": "Super Admin",
    "email": "admin@voicenote.app",
    "token": "token_admin_main",
    "timezone": "UTC"
  }'

# Expected response includes access_token
# Copy that token for next request

# 2. Use token to access admin endpoints
curl -X GET http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"

# Expected: Admin statistics JSON
```

### Test with Swagger

```
1. Go to: http://localhost:8000/docs
2. Find: POST /api/v1/users/sync
3. Click "Try it out"
4. Fill:
   {
     "id": "admin_main",
     "token": "token_admin_main"
   }
5. Click "Execute"
6. Copy access_token
7. Click green "Authorize" button
8. Paste: Bearer <TOKEN>
9. Test: GET /api/v1/admin/stats
```

---

## 🔐 API Authentication

### Header Method
```bash
curl -H "X-User-ID: admin_main" \
     http://localhost:8000/api/v1/admin/stats
```

### Bearer Token Method
```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
     http://localhost:8000/api/v1/admin/stats
```

### Device Token Method (Mobile App)
```bash
curl -X POST http://localhost:8000/api/v1/users/sync \
  -d '{"id": "admin_main", "token": "token_admin_main"}'
```

---

## 📊 Admin Endpoints by Permission

### Full Admin Endpoints (All Permissions)
```
✅ GET    /api/v1/admin/users                    - List all users
✅ GET    /api/v1/admin/users/{id}               - Get user details
✅ POST   /api/v1/admin/users/{id}/make-admin    - Promote user
✅ POST   /api/v1/admin/users/{id}/remove-admin  - Demote user
✅ DELETE /api/v1/admin/users/{id}               - Delete user
✅ GET    /api/v1/admin/stats                    - System statistics
✅ GET    /api/v1/admin/action-logs              - Admin logs
✅ POST   /api/v1/admin/system/settings          - Update settings
```

### Moderator Endpoints (Moderation Only)
```
✅ GET /api/v1/admin/moderation/queue            - Pending reviews
✅ POST /api/v1/admin/moderation/{id}/approve    - Approve content
✅ POST /api/v1/admin/moderation/{id}/reject     - Reject content
❌ Can't access user management
❌ Can't access analytics
```

### Viewer Endpoints (Analytics Only)
```
✅ GET /api/v1/admin/stats                       - View statistics
✅ GET /api/v1/admin/analytics/users             - User analytics
✅ GET /api/v1/admin/analytics/content           - Content analytics
❌ Can't modify anything
❌ Can't access moderation
```

---

## 🔒 Security Checklist

- [ ] Admin accounts created
- [ ] Tokens are strong/unique
- [ ] Permissions set correctly
- [ ] No credentials in code
- [ ] No tokens committed to git
- [ ] Admin actions being logged
- [ ] Access verified via Swagger
- [ ] All tests passing

---

## 📝 Environment Variables

For production deployment via CI/CD, add to GitHub Secrets:

```
ADMIN_ID=admin_main
ADMIN_TOKEN=token_admin_main
ADMIN_EMAIL=admin@voicenote.app
```

Then reference in `.env.production`:
```bash
# Will be injected by CI/CD
ADMIN_ID=${ADMIN_ID}
ADMIN_TOKEN=${ADMIN_TOKEN}
```

---

## 🎯 Common Admin Tasks

### Promote Regular User to Admin
```bash
# Via Swagger: POST /api/v1/admin/users/{user_id}/make-admin
# Via SQL:
UPDATE users SET is_admin = true WHERE id = 'user_to_promote';
```

### Change Admin Permissions
```bash
# Via SQL:
UPDATE users 
SET admin_permissions = '{"can_view_analytics": true}'
WHERE id = 'admin_viewer';
```

### Remove Admin Status
```bash
# Via Swagger: POST /api/v1/admin/users/{user_id}/remove-admin
# Via SQL:
UPDATE users SET is_admin = false WHERE id = 'admin_moderator';
```

### View Admin Action Logs
```bash
# Via SQL:
SELECT admin_id, action, target_id, created_at 
FROM admin_action_logs 
ORDER BY created_at DESC LIMIT 20;

# Via API:
GET /api/v1/admin/action-logs
```

---

## 🆘 Troubleshooting

### "Admin not found" error
```bash
# Verify admin exists
make db-shell
SELECT * FROM users WHERE id='admin_main';

# If not found, create using INSERT command above
```

### "Permission denied" error
```bash
# Check permissions
make db-shell
SELECT admin_permissions FROM users WHERE id='admin_main';

# If empty, update:
UPDATE users 
SET admin_permissions = '{"can_manage_users": true, "can_manage_admins": true, ...}'
WHERE id = 'admin_main';
```

### Token not working
```bash
# Get fresh token
curl -X POST http://localhost:8000/api/v1/users/sync \
  -d '{
    "id": "admin_main",
    "token": "token_admin_main"
  }'

# Use the returned access_token
```

---

## 📚 Related Documentation

- Full Setup: `docs/ADMIN_SETUP_GUIDE.md`
- Quick Reference: `ADMIN_CREDENTIALS_QUICK_REF.md`
- Testing Guide: `docs/TESTING_CI_CD.md`
- API Reference: `docs/API_ARCHITECTURE.md`

---

## ✨ Summary

Your admin system is configured with:

✅ 3 pre-configured admin account templates  
✅ Database insert commands ready  
✅ Full permission system  
✅ Audit logging enabled  
✅ API endpoints protected  

**Next step:** Run the SQL insert commands to create your admins!

---

**Created:** February 6, 2026  
**Status:** Ready for deployment  
**Last Updated:** Feb 6, 2026

