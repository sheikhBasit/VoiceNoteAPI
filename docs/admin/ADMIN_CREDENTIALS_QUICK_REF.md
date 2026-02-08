# 🔐 Admin Credentials - Quick Setup

## ⚡ Create Admin in 30 Seconds

### Step 1: Open Database
```bash
make db-shell
```

### Step 2: Paste This Command
```sql
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES ('admin_main', 'Super Admin', 'admin@voicenote.app', 'token_admin_main', true, '{"can_manage_users": true, "can_manage_admins": true, "can_view_analytics": true, "can_moderate_content": true}', 1707256800000, 1707256800000, true);
```

### Step 3: Exit
```sql
\q
```

**Done!** ✅

---

## 🔑 Your Admin Credentials

```
ID:    admin_main
Name:  Super Admin
Email: admin@voicenote.app
Token: token_admin_main
```

---

## 🧪 Test Admin Access (5 minutes)

### 1. Open Swagger
```
http://localhost:8000/docs
```

### 2. Create Login Token
```
Find: POST /api/v1/users/sync
Click: "Try it out"
Fill in:
{
  "id": "admin_main",
  "name": "Super Admin",
  "email": "admin@voicenote.app",
  "token": "token_admin_main"
}
Click: "Execute"
Copy: access_token from response
```

### 3. Authorize in Swagger
```
Click: Green "Authorize" button
Paste: Bearer <YOUR_ACCESS_TOKEN>
Click: "Authorize"
```

### 4. Test Admin Endpoint
```
Find: GET /api/v1/admin/stats
Click: "Try it out"
Click: "Execute"
See: Admin statistics response ✅
```

---

## 🛠️ Admin Permissions

```json
{
  "can_manage_users": true,
  "can_manage_admins": true,
  "can_view_analytics": true,
  "can_moderate_content": true
}
```

---

## 📚 Admin Endpoints Available

```
GET    /api/v1/admin/users           - List users
POST   /api/v1/admin/users/{id}/make-admin     - Promote user
GET    /api/v1/admin/stats           - View statistics
GET    /api/v1/admin/action-logs     - View action logs
POST   /api/v1/admin/system/settings - Update settings
... and more
```

---

## 🔒 Important Notes

⚠️ **NEVER:**
- Share admin credentials
- Commit tokens to git
- Use weak passwords/tokens

✅ **DO:**
- Store credentials securely
- Use different admins per role
- Audit admin actions regularly

---

## 📞 Quick Commands

### Verify Admin Created
```bash
make db-shell
SELECT id, name, is_admin FROM users WHERE is_admin=true;
\q
```

### Check Admin Permissions
```bash
make db-shell
SELECT admin_permissions FROM users WHERE id='admin_main';
\q
```

### View Admin Actions
```bash
make db-shell
SELECT admin_id, action, created_at FROM admin_action_logs LIMIT 10;
\q
```

---

## ✨ You're All Set!

✅ Admin account created  
✅ Permissions assigned  
✅ Ready to manage system  

**Next:** See `docs/ADMIN_SETUP_GUIDE.md` for full documentation

