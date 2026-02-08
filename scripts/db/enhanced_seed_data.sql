-- Enhanced Database Seeding for VoiceNoteAPI
-- This script creates EXTENSIVE test data for Users, Notes, Tasks, and System Settings
-- TARGET: 25+ Users, 50+ Notes, 75+ Tasks

TRUNCATE TABLE users, notes, tasks, system_settings, api_keys RESTART IDENTITY CASCADE;

-- ==================== USERS (25+) ====================

-- 1. Admin Users (3)
INSERT INTO users (id, name, email, token, device_id, device_model, last_login, is_deleted, is_admin, admin_created_at, admin_permissions, password_hash)
VALUES 
    ('admin_main', 'Super Admin', 'admin@voicenote.app', 'token_admin_main', 'dev_admin_main', 'Server', 
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     '{"can_modify_system_settings": true, "can_manage_admins": true, "can_view_audit_logs": true, "can_view_all_users": true, "can_manage_users": true, "can_view_analytics": true, "can_view_all_notes": true, "can_delete_users": true, "can_delete_notes": true}'::jsonb,
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MET7iC'),
    ('admin_content', 'Content Mod', 'mod@voicenote.app', 'token_mod', 'dev_mod', 'Server',
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     '{"can_view_audit_logs": true, "can_view_users": true, "can_view_notes": true}'::jsonb,
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MET7iC'),
    ('admin_audit', 'Auditor', 'audit@voicenote.app', 'token_audit', 'dev_audit', 'Server',
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     '{"can_view_audit_logs": true}'::jsonb,
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MET7iC')
ON CONFLICT (email) DO UPDATE SET is_admin = true;

-- 2. Developers (5)
INSERT INTO users (id, name, email, token, device_id, device_model, primary_role, system_prompt, work_start_hour, work_end_hour, work_days, jargons, last_login, is_deleted)
VALUES 
    ('dev_python', 'Py Developer', 'python@dev.com', 'token_py', 'dev_id_py', 'MacBook Pro', 'DEVELOPER', 
     'You are a Python expert.', 9, 17, '[1,2,3,4,5]'::json, '["FastAPI", "Django", "Flask"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('dev_js', 'JS Developer', 'js@dev.com', 'token_js', 'dev_id_js', 'MacBook Air', 'DEVELOPER', 
     'You are a JS expert.', 10, 18, '[1,2,3,4,5]'::json, '["React", "Node", "Vue"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('dev_go', 'Go Developer', 'go@dev.com', 'token_go', 'dev_id_go', 'Linux Workstation', 'DEVELOPER', 
     'You are a Go expert.', 8, 16, '[1,2,3,4,5]'::json, '["Gin", "Echo", "Goroutines"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('dev_rust', 'Rust Developer', 'rust@dev.com', 'token_rust', 'dev_id_rust', 'Windows PC', 'DEVELOPER', 
     'You are a Rust expert.', 9, 17, '[1,2,3,4,5]'::json, '["Tokio", "Actix", "Rocket"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('dev_mobile', 'Mobile Dev', 'mobile@dev.com', 'token_mob', 'dev_id_mob', 'iPhone 15', 'DEVELOPER', 
     'You are a mobile dev.', 11, 19, '[1,2,3,4,5]'::json, '["Flutter", "Swift", "Kotlin"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false)
ON CONFLICT (email) DO NOTHING;

-- 3. Students (5)
INSERT INTO users (id, name, email, token, device_id, device_model, primary_role, system_prompt, work_start_hour, work_end_hour, work_days, jargons, last_login, is_deleted)
VALUES 
    ('stu_math', 'Math Student', 'math@edu.com', 'token_math', 'dev_id_math', 'iPad', 'STUDENT', 
     'Math tutor.', 8, 20, '[0,1,2,3,4,5,6]'::json, '["Calculus", "Algebra", "Geometry"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('stu_bio', 'Bio Student', 'bio@edu.com', 'token_bio', 'dev_id_bio', 'Surface Pro', 'STUDENT', 
     'Biology helper.', 8, 20, '[1,2,3,4,5]'::json, '["Anatomy", "Genetics", "Cells"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('stu_lit', 'Lit Student', 'lit@edu.com', 'token_lit', 'dev_id_lit', 'Kindle', 'STUDENT', 
     'Literature expert.', 10, 22, '[1,2,3,4,5]'::json, '["Shakespeare", "Poetry", "Prose"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('stu_hist', 'History Student', 'hist@edu.com', 'token_hist', 'dev_id_hist', 'Chromebook', 'STUDENT', 
     'History buff.', 9, 21, '[1,2,3,4,5]'::json, '["WWII", "Rome", "Revolution"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('stu_cs', 'CS Student', 'cs@edu.com', 'token_cs', 'dev_id_cs', 'Gaming Laptop', 'STUDENT', 
     'CS major.', 12, 24, '[1,2,3,4,5,6,0]'::json, '["Algorithms", "Data Structures", "OS"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false)
ON CONFLICT (email) DO NOTHING;

-- 4. Business Professionals (5)
INSERT INTO users (id, name, email, token, device_id, device_model, primary_role, system_prompt, work_start_hour, work_end_hour, work_days, jargons, last_login, is_deleted)
VALUES 
    ('biz_ce', 'CEO', 'ceo@corp.com', 'token_ceo', 'dev_id_ceo', 'iPhone 15 Pro', 'BUSINESS_MAN', 
     'Strategic advisor.', 6, 20, '[1,2,3,4,5,6]'::json, '["ROI", "EBITDA", "Synergy"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('biz_sales', 'Sales VP', 'sales@corp.com', 'token_sales', 'dev_id_sales', 'iPad Pro', 'BUSINESS_MAN', 
     'Sales coach.', 8, 18, '[1,2,3,4,5]'::json, '["Pipeline", "Closing", "Lead"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('biz_mkt', 'Marketing Lead', 'mkt@corp.com', 'token_mkt', 'dev_id_mkt', 'MacBook', 'BUSINESS_MAN', 
     'Marketing guru.', 9, 17, '[1,2,3,4,5]'::json, '["SEO", "PPC", "Brand"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('biz_pm', 'Product Manager', 'pm@corp.com', 'token_pm', 'dev_id_pm', 'ThinkPad', 'BUSINESS_MAN', 
     'Product owner.', 9, 18, '[1,2,3,4,5]'::json, '["Agile", "Scrum", "Roadmap"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('biz_hr', 'HR Director', 'hr@corp.com', 'token_hr', 'dev_id_hr', 'Dell XPS', 'BUSINESS_MAN', 
     'HR specialist.', 9, 17, '[1,2,3,4,5]'::json, '["Benefits", "Culture", "Hiring"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false)
ON CONFLICT (email) DO NOTHING;

-- 5. Creative/Others (7)
INSERT INTO users (id, name, email, token, device_id, device_model, primary_role, system_prompt, work_start_hour, work_end_hour, work_days, jargons, last_login, is_deleted)
VALUES 
    ('cre_art', 'Artist', 'art@studio.com', 'token_art', 'dev_id_art', 'Wacom', 'GENERIC', 
     'Creative muse.', 10, 22, '[1,2,3,4,5]'::json, '["Color", "Composition", "Sketch"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('cre_music', 'Musician', 'music@studio.com', 'token_music', 'dev_id_music', 'Mac Mini', 'GENERIC', 
     'Music theorist.', 12, 24, '[1,2,3,4,5,6,0]'::json, '["Harmony", "Rhythm", "Tempo"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('cre_writer', 'Writer', 'writer@studio.com', 'token_write', 'dev_id_write', 'Typewriter', 'GENERIC', 
     'Editor.', 8, 16, '[1,2,3,4,5]'::json, '["Plot", "Character", "Draft"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('med_doc', 'Doctor', 'doc@hosp.com', 'token_doc', 'dev_id_doc', 'Pager', 'GENERIC', 
     'Medical assistant.', 0, 24, '[1,2,3,4,5,6,0]'::json, '["Diagnosis", "Treatment", "Patient"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('med_nurse', 'Nurse', 'nurse@hosp.com', 'token_nurse', 'dev_id_nurse', 'Phone', 'GENERIC', 
     'Care helper.', 0, 24, '[1,2,3,4,5,6,0]'::json, '["Vitals", "Medication", "Care"]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('usr_del1', 'Deleted User 1', 'del1@test.com', 'token_del1', 'dev_del1', 'Old Phone', 'GENERIC', '', 9, 17, '[]'::json, '[]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, true),
    ('usr_del2', 'Deleted User 2', 'del2@test.com', 'token_del2', 'dev_del2', 'Old Laptop', 'GENERIC', '', 9, 17, '[]'::json, '[]'::json, EXTRACT(EPOCH FROM NOW())::bigint * 1000, true)
ON CONFLICT (email) DO NOTHING;

-- ==================== NOTES (50+) ====================

-- Developers (15 notes) - Distributed
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted, is_pinned, is_liked)
SELECT 
    'note_dev_' || i, 
    CASE WHEN i % 5 = 0 THEN 'dev_python' WHEN i % 5 = 1 THEN 'dev_js' WHEN i % 5 = 2 THEN 'dev_go' WHEN i % 5 = 3 THEN 'dev_rust' ELSE 'dev_mobile' END,
    'Dev Meeting ' || i, 
    'Technical discussion about architecture and code quality.',
    'We discussed key architectural decisions for the new microservice. We need to ensure high availability and proper error handling. Code quality metrics should be tracked in CI/CD.',
    'We discussed key architectural decisions for the new microservice. We need to ensure high availability and proper error handling. Code quality metrics should be tracked in CI/CD.',
    CASE WHEN i % 3 = 0 THEN 'HIGH' WHEN i % 3 = 1 THEN 'MEDIUM' ELSE 'LOW' END::priority,
    CASE WHEN i % 4 = 0 THEN 'DONE' WHEN i % 4 = 1 THEN 'PENDING' WHEN i % 4 = 2 THEN 'PROCESSING' ELSE 'DELAYED' END::notestatus,
    EXTRACT(EPOCH FROM NOW() - (i || ' days')::INTERVAL)::bigint * 1000,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    CASE WHEN i > 12 THEN true ELSE false END, -- Some deleted notes
    CASE WHEN i % 5 = 0 THEN true ELSE false END, -- Some pinned
    CASE WHEN i % 3 = 0 THEN true ELSE false END  -- Some liked
FROM generate_series(1, 15) AS i;

-- Students (15 notes)
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted)
SELECT 
    'note_stu_' || i, 
    CASE WHEN i % 5 = 0 THEN 'stu_math' WHEN i % 5 = 1 THEN 'stu_bio' WHEN i % 5 = 2 THEN 'stu_lit' WHEN i % 5 = 3 THEN 'stu_hist' ELSE 'stu_cs' END,
    'Lecture Notes ' || i, 
    'Class notes covering key topics for the exam.',
    'Professor emphasized the importance of understanding the core concepts. The exam will cover chapters 1 through 5. Make sure to review the problem sets.',
    'Professor emphasized the importance of understanding the core concepts. The exam will cover chapters 1 through 5. Make sure to review the problem sets.',
    CASE WHEN i % 3 = 0 THEN 'HIGH' WHEN i % 3 = 1 THEN 'MEDIUM' ELSE 'LOW' END::priority,
    'DONE'::notestatus,
    EXTRACT(EPOCH FROM NOW() - (i || ' days')::INTERVAL)::bigint * 1000,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false
FROM generate_series(1, 15) AS i;

-- Business (15 notes)
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted)
SELECT 
    'note_biz_' || i, 
    CASE WHEN i % 5 = 0 THEN 'biz_ce' WHEN i % 5 = 1 THEN 'biz_sales' WHEN i % 5 = 2 THEN 'biz_mkt' WHEN i % 5 = 3 THEN 'biz_pm' ELSE 'biz_hr' END,
    'Strategy Session ' || i, 
    'Business planning and quarterly goals review.',
    'Q3 goals are ambitious but achievable. We need to focus on customer retention and upselling. Validated the new pricing model with key stakeholders.',
    'Q3 goals are ambitious but achievable. We need to focus on customer retention and upselling. Validated the new pricing model with key stakeholders.',
    'HIGH'::priority,
    'PENDING'::notestatus,
    EXTRACT(EPOCH FROM NOW() - (i || ' hours')::INTERVAL)::bigint * 1000,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false
FROM generate_series(1, 15) AS i;

-- Creative/Medical (10 notes)
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted)
SELECT 
    'note_mix_' || i, 
    CASE WHEN i % 5 = 0 THEN 'cre_art' WHEN i % 5 = 1 THEN 'cre_music' WHEN i % 5 = 2 THEN 'med_doc' WHEN i % 5 = 3 THEN 'med_nurse' ELSE 'cre_writer' END,
    'Daily Log ' || i, 
    'Daily observations and tasks.',
    'Recorded patient vitals and updated charts. Creating a new sketch for the upcoming exhibition. Drafting the next chapter.',
    'Recorded patient vitals and updated charts. Creating a new sketch for the upcoming exhibition. Drafting the next chapter.',
    'MEDIUM'::priority,
    'DONE'::notestatus,
    EXTRACT(EPOCH FROM NOW() - (i || ' days')::INTERVAL)::bigint * 1000,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false
FROM generate_series(1, 10) AS i;

-- ==================== TASKS (75+) ====================

-- Tasks linked to Developer Notes (25 tasks)
INSERT INTO tasks (id, note_id, description, is_done, deadline, priority, created_at, updated_at, is_deleted)
SELECT 
    'task_dev_' || i, 
    'note_dev_' || (i % 15 + 1),
    'Implement feature request from meeting ' || i,
    CASE WHEN i % 2 = 0 THEN true ELSE false END,
    EXTRACT(EPOCH FROM NOW() + (CASE WHEN i % 2 = 0 THEN -1 ELSE 1 END * i || ' days')::INTERVAL)::bigint * 1000, -- Mix of future and past deadlines
    CASE WHEN i % 3 = 0 THEN 'HIGH' WHEN i % 3 = 1 THEN 'MEDIUM' ELSE 'LOW' END::priority,
    EXTRACT(EPOCH FROM NOW() - '5 days'::INTERVAL)::bigint * 1000,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false
FROM generate_series(1, 25) AS i;

-- Tasks linked to Business Notes (25 tasks)
INSERT INTO tasks (id, note_id, description, is_done, deadline, priority, created_at, updated_at, is_deleted, assigned_entities)
SELECT 
    'task_biz_' || i, 
    'note_biz_' || (i % 15 + 1),
    'Follow up on action item ' || i,
    CASE WHEN i % 3 = 0 THEN true ELSE false END,
    EXTRACT(EPOCH FROM NOW() + (CASE WHEN i % 4 = 0 THEN 0 ELSE i END || ' days')::INTERVAL)::bigint * 1000, -- Some due today (0 days)
    'HIGH'::priority,
    EXTRACT(EPOCH FROM NOW() - '2 days'::INTERVAL)::bigint * 1000,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    false,
    '[{"name": "Team", "email": "team@corp.com"}]'::jsonb
FROM generate_series(1, 25) AS i;

-- General Tasks (25 tasks) - Some orphaned/deleted
INSERT INTO tasks (id, note_id, description, is_done, deadline, priority, created_at, updated_at, is_deleted)
SELECT 
    'task_gen_' || i, 
    'note_stu_' || (i % 15 + 1),
    'Study task ' || i,
    false,
    EXTRACT(EPOCH FROM NOW() + (i || ' days')::INTERVAL)::bigint * 1000,
    'MEDIUM'::priority,
    EXTRACT(EPOCH FROM NOW() - '1 day'::INTERVAL)::bigint * 1000,
    EXTRACT(EPOCH FROM NOW())::bigint * 1000,
    CASE WHEN i > 20 THEN true ELSE false END
FROM generate_series(1, 25) AS i;

-- ==================== SYSTEM SETTINGS ====================

INSERT INTO system_settings (id, llm_model, llm_fast_model, temperature, max_tokens, top_p, stt_engine, groq_whisper_model, deepgram_model, updated_at, updated_by)
VALUES (1, 'llama-3.1-70b-versatile', 'llama-3.1-8b-instant', 5, 4096, 9, 'deepgram', 'whisper-large-v3-turbo', 'nova-3',
        EXTRACT(EPOCH FROM NOW())::bigint * 1000, 'admin_main')
ON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at;

-- ==================== VERIFICATION ====================

-- Fix defaults for admin users seeded via SQL (which bypasses SQLAlchemy defaults)
UPDATE users 
SET work_start_hour = 9, 
    work_end_hour = 17, 
    work_days = '[1,2,3,4,5]'::json, 
    jargons = '[]'::json 
WHERE work_start_hour IS NULL;

-- Fix defaults for NOTES (transcript_groq, is_archived, is_encrypted, etc.)
UPDATE notes
SET transcript_groq = COALESCE(transcript_groq, ''),
    transcript_deepgram = COALESCE(transcript_deepgram, ''),
    document_urls = COALESCE(document_urls, '[]'::json),
    links = COALESCE(links, '[]'::json),
    is_archived = COALESCE(is_archived, false),
    is_encrypted = COALESCE(is_encrypted, false),
    is_liked = COALESCE(is_liked, false),
    is_pinned = COALESCE(is_pinned, false),
    summary = COALESCE(summary, 'Summary not available')
WHERE transcript_groq IS NULL OR document_urls IS NULL;

-- Fix defaults for TASKS (image_urls, document_urls, external_links, assigned_entities)
UPDATE tasks
SET image_urls = COALESCE(image_urls, '[]'::jsonb),
    document_urls = COALESCE(document_urls, '[]'::jsonb),
    external_links = COALESCE(external_links, '[]'::jsonb),
    assigned_entities = COALESCE(assigned_entities, '[]'::jsonb),
    is_action_approved = COALESCE(is_action_approved, false)
WHERE image_urls IS NULL OR document_urls IS NULL;

-- Fix defaults for System Settings (Update decommissioned LLM model)
UPDATE system_settings
SET llm_model = 'llama-3.3-70b-versatile'
WHERE id = 1;

SELECT 'Users' as table_name, COUNT(*) as count FROM users WHERE is_deleted = false
UNION ALL
SELECT 'Notes', COUNT(*) FROM notes WHERE is_deleted = false
UNION ALL
SELECT 'Tasks', COUNT(*) FROM tasks WHERE is_deleted = false;
