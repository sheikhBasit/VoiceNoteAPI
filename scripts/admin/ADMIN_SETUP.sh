#!/bin/bash

# Admin Account Setup Script
# Creates pre-configured admin accounts in database

echo "🔐 VoiceNote Admin Account Setup"
echo "=================================="
echo ""

# Connect to database and create admins
make db-shell << SQL
-- Create Super Admin Account
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES (
    'admin_main',
    'Super Admin',
    'admin@voicenote.app',
    'token_admin_main',
    true,
    '{"can_manage_users": true, "can_manage_admins": true, "can_view_analytics": true, "can_moderate_content": true}',
    extract(epoch from now()) * 1000,
    extract(epoch from now()) * 1000,
    true
);

-- Create Moderator Account
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES (
    'admin_moderator',
    'Content Moderator',
    'moderator@voicenote.app',
    'token_admin_moderator',
    true,
    '{"can_moderate_content": true}',
    extract(epoch from now()) * 1000,
    extract(epoch from now()) * 1000,
    true
);

-- Create Viewer Account
INSERT INTO users (id, name, email, device_token, is_admin, admin_permissions, admin_created_at, created_at, is_active)
VALUES (
    'admin_viewer',
    'Analytics Viewer',
    'viewer@voicenote.app',
    'token_admin_viewer',
    true,
    '{"can_view_analytics": true}',
    extract(epoch from now()) * 1000,
    extract(epoch from now()) * 1000,
    true
);

-- Verify
SELECT id, name, email, is_admin FROM users WHERE is_admin = true;
SQL

echo ""
echo "✅ Admin accounts created successfully!"
echo ""
echo "Admin Credentials:"
echo "  1. admin_main        - super@voicenote.app      (Full Access)"
echo "  2. admin_moderator   - moderator@voicenote.app  (Moderation Only)"
echo "  3. admin_viewer      - viewer@voicenote.app     (Analytics Only)"
echo ""
echo "Next: Test with Swagger UI at http://localhost:8000/docs"
