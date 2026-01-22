-- Initialize VoiceNote Database Schema
-- This script runs automatically when the PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set search path
SET search_path TO public;

-- Verify extensions are loaded
SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');
