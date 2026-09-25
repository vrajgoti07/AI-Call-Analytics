-- ============================================================================
-- Migration: 003_create_escalation_risk_tables.sql
-- Description: Create escalation_risks table for Phase 8 Risk Detection
-- ============================================================================

CREATE TABLE IF NOT EXISTS escalation_risks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id VARCHAR(128) NOT NULL,
    model_type VARCHAR(32) NOT NULL DEFAULT 'heuristic',
    model_name VARCHAR(128) NOT NULL,
    model_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    feature_version VARCHAR(32) NOT NULL DEFAULT 'v1',
    threshold_version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    risk_score DOUBLE PRECISION NOT NULL,
    risk_probability DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(32) NOT NULL,
    top_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation TEXT NOT NULL DEFAULT '',
    feature_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    temporal_risk JSONB NOT NULL DEFAULT '[]'::jsonb,
    processing_time_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    metadata_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying by call, risk level, score, and timestamps
CREATE INDEX IF NOT EXISTS ix_escalation_risks_call_id ON escalation_risks (call_id);
CREATE INDEX IF NOT EXISTS ix_escalation_risks_risk_level ON escalation_risks (risk_level);
CREATE INDEX IF NOT EXISTS ix_escalation_risks_risk_score ON escalation_risks (risk_score);
CREATE INDEX IF NOT EXISTS ix_escalation_risks_created_at ON escalation_risks (created_at);
CREATE INDEX IF NOT EXISTS ix_escalation_risks_call_id_created_at ON escalation_risks (call_id, created_at);
CREATE INDEX IF NOT EXISTS ix_escalation_risks_risk_level_score ON escalation_risks (risk_level, risk_score);
