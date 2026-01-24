-- Comprehensive Database Seeding for VoiceNoteAPI
-- This script creates test data for Users, Notes, Tasks, and System Settings

-- ==================== USERS ====================

-- Admin Users with Full Permissions
INSERT INTO users (id, name, email, token, device_id, device_model, last_login, is_deleted, is_admin, admin_created_at, admin_permissions, password_hash)
VALUES 
    ('admin_user_001', 'System Admin', 'admin@voicenote.app', 'admin_token_001', 'admin_device_001', 'Server', 
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     '{"can_modify_system_settings": true, "can_manage_admins": true, "can_view_audit_logs": true, "can_view_users": true}'::jsonb,
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MET7iC'), -- password: admin123
    ('moderator_001', 'Content Moderator', 'moderator@voicenote.app', 'mod_token_001', 'mod_device_001', 'Server',
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     '{"can_view_audit_logs": true, "can_view_users": true}'::jsonb,
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MET7iC')
ON CONFLICT (email) DO UPDATE SET 
    is_admin = EXCLUDED.is_admin,
    admin_permissions = EXCLUDED.admin_permissions;

-- Regular Test Users
INSERT INTO users (id, name, email, token, device_id, device_model, primary_role, system_prompt, work_start_hour, work_end_hour, work_days, jargons, last_login, is_deleted)
VALUES 
    ('user_dev_001', 'Alice Developer', 'alice@test.com', 'token_alice_001', 'device_alice', 'iPhone 14', 'DEVELOPER', 
     'You are a helpful coding assistant.', 9, 18, '[1,2,3,4,5]'::json, '["Python", "FastAPI", "Docker"]'::json,
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('user_student_001', 'Bob Student', 'bob@test.com', 'token_bob_001', 'device_bob', 'Android', 'STUDENT',
     'You are a study companion.', 8, 16, '[1,2,3,4,5]'::json, '["Math", "Physics", "Chemistry"]'::json,
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('user_business_001', 'Carol Business', 'carol@test.com', 'token_carol_001', 'device_carol', 'iPad', 'BUSINESS_MAN',
     'You are a business advisor.', 9, 17, '[1,2,3,4,5]'::json, '["Sales", "Marketing", "Revenue"]'::json,
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('user_teacher_001', 'David Teacher', 'david@test.com', 'token_david_001', 'device_david', 'MacBook', 'TEACHER',
     'You are an educational assistant.', 7, 15, '[1,2,3,4,5]'::json, '["Curriculum", "Lesson Plan", "Assessment"]'::json,
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('user_deleted_001', 'Eve Deleted', 'eve@test.com', 'token_eve_001', 'device_eve', 'Android', 'GENERIC',
     '', 9, 17, '[1,2,3,4,5]'::json, '[]'::json,
     EXTRACT(EPOCH FROM NOW())::bigint * 1000, true)
ON CONFLICT (email) DO NOTHING;

-- ==================== NOTES ====================

-- Notes for Alice (Developer)
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted, is_pinned, is_liked, is_archived)
VALUES
    ('note_alice_001', 'user_dev_001', 'FastAPI Best Practices', 
     'Discussion about async/await patterns, dependency injection, and error handling in FastAPI applications.',
     'We need to implement proper async await patterns in our FastAPI application. The dependency injection system is really powerful and we should use it for database sessions and authentication. Error handling should be centralized using HTTPException with proper status codes.',
     'We need to implement proper async await patterns in our FastAPI application. The dependency injection system is really powerful and we should use it for database sessions and authentication. Error handling should be centralized using HTTPException with proper status codes.',
     'HIGH', 'DONE', EXTRACT(EPOCH FROM NOW() - INTERVAL '2 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     false, true, true, false),
    ('note_alice_002', 'user_dev_001', 'Docker Optimization',
     'Notes on multi-stage builds, layer caching, and reducing image size for production deployments.',
     'Multi-stage Docker builds can significantly reduce image size. We should separate build dependencies from runtime dependencies. Use .dockerignore to exclude unnecessary files. Alpine images are smaller but may have compatibility issues.',
     'Multi-stage Docker builds can significantly reduce image size. We should separate build dependencies from runtime dependencies. Use .dockerignore to exclude unnecessary files. Alpine images are smaller but may have compatibility issues.',
     'MEDIUM', 'DONE', EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     false, false, true, false),
    ('note_alice_003', 'user_dev_001', 'Database Migration Strategy',
     'Planning for Alembic migrations, version control, and rollback procedures.',
     'Alembic provides powerful database migration capabilities. Always test migrations in staging first. Keep migrations small and focused. Document breaking changes clearly. Have a rollback plan for every migration.',
     'Alembic provides powerful database migration capabilities. Always test migrations in staging first. Keep migrations small and focused. Document breaking changes clearly. Have a rollback plan for every migration.',
     'HIGH', 'PROCESSING', EXTRACT(EPOCH FROM NOW() - INTERVAL '3 hours')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000,
     false, true, false, false);

-- Notes for Bob (Student)
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted)
VALUES
    ('note_bob_001', 'user_student_001', 'Calculus Lecture Notes',
     'Derivatives, integrals, and fundamental theorem of calculus with examples.',
     'The derivative represents the rate of change. The integral is the area under the curve. The fundamental theorem connects these two concepts. Practice problems: find derivative of x squared, integral of 2x.',
     'The derivative represents the rate of change. The integral is the area under the curve. The fundamental theorem connects these two concepts. Practice problems: find derivative of x squared, integral of 2x.',
     'HIGH', 'DONE', EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('note_bob_002', 'user_student_001', 'Physics Lab Report',
     'Experiment on projectile motion, data collection, and analysis.',
     'Measured the trajectory of a projectile at different angles. Collected data on range and height. Analyzed results using kinematic equations. Conclusion: 45 degrees gives maximum range in ideal conditions.',
     'Measured the trajectory of a projectile at different angles. Collected data on range and height. Analyzed results using kinematic equations. Conclusion: 45 degrees gives maximum range in ideal conditions.',
     'MEDIUM', 'DONE', EXTRACT(EPOCH FROM NOW() - INTERVAL '2 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false);

-- Notes for Carol (Business)
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted)
VALUES
    ('note_carol_001', 'user_business_001', 'Q1 Sales Strategy',
     'Planning for first quarter sales targets, new markets, and customer acquisition.',
     'Focus on enterprise clients in Q1. Target healthcare and finance sectors. Increase marketing budget by 20%. Hire two new sales reps. Launch referral program.',
     'Focus on enterprise clients in Q1. Target healthcare and finance sectors. Increase marketing budget by 20%. Hire two new sales reps. Launch referral program.',
     'HIGH', 'PENDING', EXTRACT(EPOCH FROM NOW() - INTERVAL '6 hours')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('note_carol_002', 'user_business_001', 'Client Meeting - Acme Corp',
     'Discussion about contract renewal, pricing, and new feature requests.',
     'Acme Corp wants to renew for 2 years. Requesting 15% discount. Need custom reporting dashboard. Timeline: 3 months for implementation. Budget approved.',
     'Acme Corp wants to renew for 2 years. Requesting 15% discount. Need custom reporting dashboard. Timeline: 3 months for implementation. Budget approved.',
     'HIGH', 'DONE', EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false);

-- Notes for David (Teacher)
INSERT INTO notes (id, user_id, title, summary, transcript_groq, transcript_deepgram, priority, status, timestamp, updated_at, is_deleted)
VALUES
    ('note_david_001', 'user_teacher_001', 'Lesson Plan - World War II',
     'Comprehensive lesson plan covering causes, major events, and consequences of WWII.',
     'Week 1: Causes of WWII. Week 2: Major battles and turning points. Week 3: Holocaust and war crimes. Week 4: Aftermath and formation of UN. Include documentary clips and primary source analysis.',
     'Week 1: Causes of WWII. Week 2: Major battles and turning points. Week 3: Holocaust and war crimes. Week 4: Aftermath and formation of UN. Include documentary clips and primary source analysis.',
     'MEDIUM', 'DONE', EXTRACT(EPOCH FROM NOW() - INTERVAL '3 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('note_david_002', 'user_teacher_001', 'Student Assessment Ideas',
     'Alternative assessment methods beyond traditional exams.',
     'Consider project-based assessments. Peer review exercises. Oral presentations. Portfolio submissions. Group projects with individual accountability. Rubrics for consistent grading.',
     'Consider project-based assessments. Peer review exercises. Oral presentations. Portfolio submissions. Group projects with individual accountability. Rubrics for consistent grading.',
     'LOW', 'PENDING', EXTRACT(EPOCH FROM NOW() - INTERVAL '12 hours')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false);

-- ==================== TASKS ====================

-- Tasks for Alice's Notes
INSERT INTO tasks (id, note_id, description, is_done, deadline, priority, created_at, updated_at, is_deleted, notification_enabled)
VALUES
    ('task_alice_001', 'note_alice_001', 'Refactor authentication middleware to use dependency injection', 
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '3 days')::bigint * 1000, 'HIGH',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '2 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true),
    ('task_alice_002', 'note_alice_001', 'Add comprehensive error handling to all API endpoints',
     true, EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, 'HIGH',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '2 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true),
    ('task_alice_003', 'note_alice_002', 'Optimize Docker image size using multi-stage builds',
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '5 days')::bigint * 1000, 'MEDIUM',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true),
    ('task_alice_004', 'note_alice_003', 'Create Alembic migration for new system_settings table',
     true, EXTRACT(EPOCH FROM NOW() - INTERVAL '2 hours')::bigint * 1000, 'HIGH',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '3 hours')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false, true);

-- Tasks for Bob's Notes
INSERT INTO tasks (id, note_id, description, is_done, deadline, priority, created_at, updated_at, is_deleted)
VALUES
    ('task_bob_001', 'note_bob_001', 'Complete calculus problem set chapter 5',
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '2 days')::bigint * 1000, 'HIGH',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('task_bob_002', 'note_bob_001', 'Review derivative rules and practice',
     true, EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, 'MEDIUM',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('task_bob_003', 'note_bob_002', 'Write physics lab report conclusion',
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '1 day')::bigint * 1000, 'HIGH',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '2 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false);

-- Tasks for Carol's Notes
INSERT INTO tasks (id, note_id, description, is_done, deadline, priority, created_at, updated_at, is_deleted, assigned_entities)
VALUES
    ('task_carol_001', 'note_carol_001', 'Prepare Q1 sales presentation for board meeting',
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '7 days')::bigint * 1000, 'HIGH',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '6 hours')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false,
     '[{"name": "Marketing Team", "email": "marketing@company.com"}]'::jsonb),
    ('task_carol_002', 'note_carol_001', 'Interview candidates for sales rep positions',
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '10 days')::bigint * 1000, 'MEDIUM',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '6 hours')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false,
     '[{"name": "HR Department", "email": "hr@company.com"}]'::jsonb),
    ('task_carol_003', 'note_carol_002', 'Draft contract renewal proposal for Acme Corp',
     true, EXTRACT(EPOCH FROM NOW() - INTERVAL '12 hours')::bigint * 1000, 'HIGH',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false,
     '[{"name": "Legal Team", "email": "legal@company.com"}]'::jsonb);

-- Tasks for David's Notes
INSERT INTO tasks (id, note_id, description, is_done, deadline, priority, created_at, updated_at, is_deleted)
VALUES
    ('task_david_001', 'note_david_001', 'Find documentary clips for WWII lesson',
     true, EXTRACT(EPOCH FROM NOW() - INTERVAL '2 days')::bigint * 1000, 'MEDIUM',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '3 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('task_david_002', 'note_david_001', 'Create quiz for WWII unit',
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '4 days')::bigint * 1000, 'MEDIUM',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '3 days')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false),
    ('task_david_003', 'note_david_002', 'Design rubric for project-based assessment',
     false, EXTRACT(EPOCH FROM NOW() + INTERVAL '6 days')::bigint * 1000, 'LOW',
     EXTRACT(EPOCH FROM NOW() - INTERVAL '12 hours')::bigint * 1000, EXTRACT(EPOCH FROM NOW())::bigint * 1000, false);

-- ==================== SYSTEM SETTINGS ====================

INSERT INTO system_settings (id, llm_model, llm_fast_model, temperature, max_tokens, top_p, stt_engine, groq_whisper_model, deepgram_model, updated_at, updated_by)
VALUES (1, 'llama-3.1-70b-versatile', 'llama-3.1-8b-instant', 3, 4096, 9, 'deepgram', 'whisper-large-v3-turbo', 'nova-3',
        EXTRACT(EPOCH FROM NOW())::bigint * 1000, 'admin_user_001')
ON CONFLICT (id) DO UPDATE SET
    llm_model = EXCLUDED.llm_model,
    llm_fast_model = EXCLUDED.llm_fast_model,
    temperature = EXCLUDED.temperature,
    max_tokens = EXCLUDED.max_tokens,
    top_p = EXCLUDED.top_p,
    stt_engine = EXCLUDED.stt_engine,
    groq_whisper_model = EXCLUDED.groq_whisper_model,
    deepgram_model = EXCLUDED.deepgram_model;

-- ==================== VERIFICATION ====================

SELECT 'Users' as table_name, COUNT(*) as count FROM users WHERE is_deleted = false
UNION ALL
SELECT 'Admin Users', COUNT(*) FROM users WHERE is_admin = true
UNION ALL
SELECT 'Notes', COUNT(*) FROM notes WHERE is_deleted = false
UNION ALL
SELECT 'Tasks', COUNT(*) FROM tasks WHERE is_deleted = false
UNION ALL
SELECT 'System Settings', COUNT(*) FROM system_settings;
