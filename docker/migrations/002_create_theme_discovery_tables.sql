-- ============================================================================
-- Migration: 002_create_theme_discovery_tables.sql
-- Description: Create theme_discovery_runs, themes, and theme_memberships tables
-- ============================================================================

-- 1. Table: theme_discovery_runs
CREATE TABLE IF NOT EXISTS theme_discovery_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_name VARCHAR(128) NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    embedding_dimension INTEGER NOT NULL DEFAULT 384,
    umap_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    hdbscan_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_hash VARCHAR(32) NOT NULL,
    dataset_size INTEGER NOT NULL,
    num_clusters INTEGER NOT NULL,
    noise_count INTEGER NOT NULL,
    noise_percentage DOUBLE PRECISION NOT NULL,
    silhouette_score DOUBLE PRECISION,
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_theme_discovery_runs_config_hash ON theme_discovery_runs (config_hash);
CREATE INDEX IF NOT EXISTS ix_theme_discovery_runs_created_at ON theme_discovery_runs (created_at);

-- 2. Table: themes
CREATE TABLE IF NOT EXISTS themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES theme_discovery_runs(id) ON DELETE CASCADE,
    cluster_id INTEGER NOT NULL,
    label VARCHAR(256) NOT NULL,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    size INTEGER NOT NULL,
    percentage DOUBLE PRECISION NOT NULL,
    call_count INTEGER NOT NULL,
    speaker_count INTEGER NOT NULL,
    intent_distribution JSONB NOT NULL DEFAULT '{}'::jsonb,
    sentiment_distribution JSONB NOT NULL DEFAULT '{}'::jsonb,
    representative_chunks JSONB NOT NULL DEFAULT '[]'::jsonb,
    extra_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_run_cluster UNIQUE (run_id, cluster_id)
);

CREATE INDEX IF NOT EXISTS ix_themes_run_id ON themes (run_id);
CREATE INDEX IF NOT EXISTS ix_themes_label ON themes (label);

-- 3. Table: theme_memberships
CREATE TABLE IF NOT EXISTS theme_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES theme_discovery_runs(id) ON DELETE CASCADE,
    theme_id UUID REFERENCES themes(id) ON DELETE CASCADE,
    call_id VARCHAR(128) NOT NULL,
    chunk_id INTEGER NOT NULL,
    cluster_id INTEGER NOT NULL,
    membership_probability DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    outlier_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_run_call_chunk UNIQUE (run_id, call_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS ix_theme_memberships_run_id ON theme_memberships (run_id);
CREATE INDEX IF NOT EXISTS ix_theme_memberships_theme_id ON theme_memberships (theme_id);
CREATE INDEX IF NOT EXISTS ix_theme_memberships_call_id ON theme_memberships (call_id);
CREATE INDEX IF NOT EXISTS ix_theme_memberships_cluster_id ON theme_memberships (cluster_id);
