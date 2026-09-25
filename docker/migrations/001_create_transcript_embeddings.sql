-- ============================================================================
-- Migration: 001_create_transcript_embeddings.sql
-- Description: Create transcript_embeddings table with HNSW vector index
-- ============================================================================

-- 1. Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create transcript_embeddings table
CREATE TABLE IF NOT EXISTS transcript_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id VARCHAR(128) NOT NULL,
    chunk_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    speaker_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    turn_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    embedding VECTOR(384) NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    model_version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    embedding_dimension INTEGER NOT NULL DEFAULT 384,
    extra_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_transcript_embeddings_call_chunk_model UNIQUE (call_id, chunk_id, model_name)
);

-- 3. Create metadata B-Tree indexes for fast lookup and filtering
CREATE INDEX IF NOT EXISTS ix_transcript_embeddings_call_id ON transcript_embeddings (call_id);
CREATE INDEX IF NOT EXISTS ix_transcript_embeddings_model_name ON transcript_embeddings (model_name);
CREATE INDEX IF NOT EXISTS ix_transcript_embeddings_created_at ON transcript_embeddings (created_at);

-- 4. Create HNSW Cosine Distance Vector Index
CREATE INDEX IF NOT EXISTS ix_transcript_embeddings_vector_hnsw 
ON transcript_embeddings 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
