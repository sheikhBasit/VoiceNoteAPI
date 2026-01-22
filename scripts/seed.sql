-- Seed VoiceNote Database with Sample Data
-- This script runs after initialization on container startup

-- Insert Admin User
INSERT INTO users (id, name, email, token, device_id, device_model, last_login, is_deleted, is_admin, admin_created_at)
VALUES (
    'admin_user_001',
    'System Admin',
    'admin@voicenote.app',
    'admin_token_' || gen_random_uuid(),
    'admin_device_001',
    'Server',
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false,
    true,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000
) ON CONFLICT (email) DO NOTHING;

-- Insert Moderator User
INSERT INTO users (id, name, email, token, device_id, device_model, last_login, is_deleted, is_admin, admin_created_at)
VALUES (
    'moderator_user_001',
    'Content Moderator',
    'moderator@voicenote.app',
    'moderator_token_' || gen_random_uuid(),
    'moderator_device_001',
    'Server',
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false,
    true,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000
) ON CONFLICT (email) DO NOTHING;

-- Insert Viewer User (Analytics)
INSERT INTO users (id, name, email, token, device_id, device_model, last_login, is_deleted, is_admin, admin_created_at)
VALUES (
    'viewer_user_001',
    'Analytics Viewer',
    'viewer@voicenote.app',
    'viewer_token_' || gen_random_uuid(),
    'viewer_device_001',
    'Server',
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false,
    true,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000
) ON CONFLICT (email) DO NOTHING;

-- Insert Test Users
INSERT INTO users (id, name, email, token, device_id, device_model, last_login, is_deleted)
VALUES 
    ('test_user_001', 'Test User 1', 'test1@voicenote.app', 'token_' || gen_random_uuid(), 'device_001', 'iPhone', EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('test_user_002', 'Test User 2', 'test2@voicenote.app', 'token_' || gen_random_uuid(), 'device_002', 'Android', EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('test_user_003', 'Test User 3', 'test3@voicenote.app', 'token_' || gen_random_uuid(), 'device_003', 'iPad', EXTRACT(EPOCH FROM NOW())::bigint * 1000, false)
ON CONFLICT (email) DO NOTHING;

-- Verify seeded data
SELECT COUNT(*) as total_users FROM users;
SELECT COUNT(*) as admin_users FROM users WHERE is_admin = true;
