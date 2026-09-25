-- ============================================================================
-- Migration: 004_create_core_backend_tables.sql
-- Description: Create core backend tables: calls, audio_files, transcripts,
--              transcript_turns, processing_jobs
-- ============================================================================

-- 1. Calls Table
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'UPLOADED',
    duration DOUBLE PRECISION,
    language VARCHAR(16) DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_calls_external_id ON calls (external_id);
CREATE INDEX IF NOT EXISTS ix_calls_status ON calls (status);
CREATE INDEX IF NOT EXISTS ix_calls_created_at ON calls (created_at);
CREATE INDEX IF NOT EXISTS ix_calls_status_created_at ON calls (status, created_at);

-- 2. Audio Files Table
CREATE TABLE IF NOT EXISTS audio_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    mime_type VARCHAR(64) NOT NULL DEFAULT 'audio/wav',
    size INTEGER NOT NULL DEFAULT 0,
    duration DOUBLE PRECISION,
    sample_rate INTEGER NOT NULL DEFAULT 16000,
    channels INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_audio_files_call_id ON audio_files (call_id);

-- 3. Transcripts Table
CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    language VARCHAR(16) NOT NULL DEFAULT 'en',
    text TEXT NOT NULL DEFAULT '',
    duration DOUBLE PRECISION,
    model VARCHAR(64) NOT NULL DEFAULT 'whisper',
    model_version VARCHAR(32) NOT NULL DEFAULT 'base',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_transcripts_call_id ON transcripts (call_id);
CREATE INDEX IF NOT EXISTS ix_transcripts_created_at ON transcripts (created_at);

-- 4. Transcript Turns Table
CREATE TABLE IF NOT EXISTS transcript_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    speaker_id VARCHAR(64) NOT NULL DEFAULT 'SPEAKER_00',
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    text TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    sentiment JSONB,
    intent JSONB,
    entities JSONB,
    alignment_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_transcript_turns_transcript_id ON transcript_turns (transcript_id);
CREATE INDEX IF NOT EXISTS ix_transcript_turns_speaker_id ON transcript_turns (speaker_id);
CREATE INDEX IF NOT EXISTS ix_transcript_turns_sequence_number ON transcript_turns (sequence_number);
CREATE INDEX IF NOT EXISTS ix_transcript_turns_transcript_seq ON transcript_turns (transcript_id, sequence_number);

-- 5. Processing Jobs Table
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    task_id VARCHAR(128),
    job_type VARCHAR(64) NOT NULL DEFAULT 'FULL_CALL_ANALYSIS',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    progress INTEGER NOT NULL DEFAULT 0,
    current_stage VARCHAR(64),
    stages JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code VARCHAR(64),
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_processing_jobs_call_id ON processing_jobs (call_id);
CREATE INDEX IF NOT EXISTS ix_processing_jobs_status ON processing_jobs (status);
CREATE INDEX IF NOT EXISTS ix_processing_jobs_task_id ON processing_jobs (task_id);
CREATE INDEX IF NOT EXISTS ix_processing_jobs_created_at ON processing_jobs (created_at);
CREATE INDEX IF NOT EXISTS ix_processing_jobs_call_status ON processing_jobs (call_id, status);
