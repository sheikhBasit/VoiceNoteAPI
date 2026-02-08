-- Initialize VoiceNote Database Schema
-- This script runs automatically when the PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set search path
SET search_path TO public;

-- Verify extensions are loaded
SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');

-- ============================================================
-- API KEYS TABLE - For failover key rotation (Requirement #4)
-- ============================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(50) NOT NULL,  -- 'deepgram', 'groq', 'openai', etc.
    api_key TEXT NOT NULL,
    priority INTEGER DEFAULT 1,  -- Lower = higher priority (primary key = 1)
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_remaining INTEGER DEFAULT 1000,
    rate_limit_reset_at BIGINT,  -- Unix timestamp in ms
    last_used_at BIGINT,
    last_error_at BIGINT,
    error_count INTEGER DEFAULT 0,
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW()) * 1000,
    updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW()) * 1000,
    notes TEXT,
    UNIQUE(service_name, priority)
);

-- Index for fast key lookup by service
CREATE INDEX IF NOT EXISTS idx_api_keys_service_active 
    ON api_keys(service_name, is_active, priority);

-- ============================================================
-- HNSW INDEX for Vector Similarity Search (Requirement #4)
-- Enables <50ms search across 10,000+ notes
-- ============================================================
-- Note: This index will be created after the notes table exists
-- We use a DO block to check if the table/column exists first

DO $$
BEGIN
    -- Check if notes table and embedding column exist
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'notes' AND column_name = 'embedding'
    ) THEN
        -- Drop existing index if it exists (to recreate with optimal params)
        DROP INDEX IF EXISTS notes_embedding_hnsw_idx;
        
        -- Create HNSW index for fast approximate nearest neighbor search
        -- m = 16: Number of connections per layer (default, good balance)
        -- ef_construction = 64: Size of dynamic candidate list during build
        CREATE INDEX notes_embedding_hnsw_idx 
            ON notes 
            USING hnsw (embedding vector_l2_ops)
            WITH (m = 16, ef_construction = 64);
            
        RAISE NOTICE 'HNSW index created on notes.embedding';
    ELSE
        RAISE NOTICE 'notes.embedding column not found - HNSW index will be created by SQLAlchemy migration';
    END IF;
END $$;

-- ============================================================
-- ROW LEVEL SECURITY (RLS) Policies (Requirement #4)
-- Ensures User A cannot access User B's data at DB level
-- ============================================================

-- Enable RLS on notes table (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notes') THEN
        ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
        
        -- Drop existing policies if they exist
        DROP POLICY IF EXISTS notes_user_isolation ON notes;
        DROP POLICY IF EXISTS notes_admin_access ON notes;
        
        -- Policy: Users can only see their own notes
        CREATE POLICY notes_user_isolation ON notes
            FOR ALL
            USING (
                user_id = current_setting('app.current_user_id', true)
                OR current_setting('app.is_admin', true) = 'true'
            );
        
        RAISE NOTICE 'RLS enabled on notes table';
    END IF;
END $$;

-- Enable RLS on tasks table (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tasks') THEN
        ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
        
        -- Drop existing policies if they exist
        DROP POLICY IF EXISTS tasks_user_isolation ON tasks;
        
        -- Policy: Users can only access tasks from their own notes
        CREATE POLICY tasks_user_isolation ON tasks
            FOR ALL
            USING (
                note_id IN (
                    SELECT id FROM notes 
                    WHERE user_id = current_setting('app.current_user_id', true)
                )
                OR current_setting('app.is_admin', true) = 'true'
            );
        
        RAISE NOTICE 'RLS enabled on tasks table';
    END IF;
END $$;

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

-- Function to get next available API key with rotation
CREATE OR REPLACE FUNCTION get_active_api_key(p_service_name VARCHAR)
RETURNS TABLE(key_id UUID, api_key TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT ak.id, ak.api_key
    FROM api_keys ak
    WHERE ak.service_name = p_service_name
      AND ak.is_active = TRUE
      AND (ak.rate_limit_remaining > 0 OR ak.rate_limit_reset_at < EXTRACT(EPOCH FROM NOW()) * 1000)
    ORDER BY ak.priority ASC, ak.error_count ASC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to mark API key as rate-limited
CREATE OR REPLACE FUNCTION mark_key_rate_limited(
    p_key_id UUID,
    p_reset_at BIGINT
) RETURNS VOID AS $$
BEGIN
    UPDATE api_keys
    SET 
        rate_limit_remaining = 0,
        rate_limit_reset_at = p_reset_at,
        updated_at = EXTRACT(EPOCH FROM NOW()) * 1000
    WHERE id = p_key_id;
END;
$$ LANGUAGE plpgsql;

-- Function to record API key error
CREATE OR REPLACE FUNCTION record_key_error(p_key_id UUID) RETURNS VOID AS $$
BEGIN
    UPDATE api_keys
    SET 
        error_count = error_count + 1,
        last_error_at = EXTRACT(EPOCH FROM NOW()) * 1000,
        updated_at = EXTRACT(EPOCH FROM NOW()) * 1000,
        -- Auto-disable key if too many errors
        is_active = CASE WHEN error_count >= 10 THEN FALSE ELSE is_active END
    WHERE id = p_key_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- SEED DEFAULT API KEYS (Placeholders - replace in production)
-- ============================================================
INSERT INTO api_keys (service_name, api_key, priority, notes)
VALUES 
    ('deepgram', 'DEEPGRAM_KEY_PRIMARY', 1, 'Primary Deepgram key'),
    ('deepgram', 'DEEPGRAM_KEY_BACKUP', 2, 'Backup Deepgram key'),
    ('groq', 'GROQ_KEY_PRIMARY', 1, 'Primary Groq key'),
    ('groq', 'GROQ_KEY_BACKUP', 2, 'Backup Groq key'),
    ('openai', 'OPENAI_KEY_PRIMARY', 1, 'Primary OpenAI key for embeddings')
ON CONFLICT (service_name, priority) DO NOTHING;

RAISE NOTICE 'VoiceNote database initialization complete';
