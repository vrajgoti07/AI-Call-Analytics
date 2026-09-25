# AI Call Analytics — Database Architecture & Migrations (Phase 10)

## 1. Database Schema Overview

The relational database is **PostgreSQL 16** with **pgvector** support. The data model centers on the `Call` aggregate root:

```
                    ┌─────────────────────────┐
                    │          calls          │
                    └────────────┬────────────┘
         ┌───────────────────────┼────────────────────────┐
         │ 1:1                   │ 1:1                    │ 1:N
         ▼                       ▼                        ▼
┌──────────────────┐    ┌──────────────────┐     ┌──────────────────┐
│   audio_files    │    │   transcripts    │     │ processing_jobs  │
└──────────────────┘    └────────┬─────────┘     └──────────────────┘
                                 │ 1:N
                                 ▼
                        ┌──────────────────┐
                        │ transcript_turns │
                        └──────────────────┘

Auxiliary Tables (Phases 6–8):
• transcript_embeddings (Phase 6 pgvector HNSW index)
• theme_discovery_runs, themes, theme_memberships (Phase 7 UMAP+HDBSCAN)
• escalation_risks (Phase 8 Multi-modal Risk Scores & Explainability)
```

---

## 2. Table Specifications

### `calls`
* `id`: UUID (Primary Key)
* `external_id`: VARCHAR(128), Indexed (CRM / telephony reference ID)
* `status`: VARCHAR(32), Indexed (`UPLOADED`, `QUEUED`, `PROCESSING`, `COMPLETED`, `PARTIAL`, `FAILED`)
* `duration`: DOUBLE PRECISION (Call duration in seconds)
* `language`: VARCHAR(16)
* `created_at`: TIMESTAMP WITH TIME ZONE, Indexed
* `updated_at`: TIMESTAMP WITH TIME ZONE

### `audio_files`
* `id`: UUID (Primary Key)
* `call_id`: UUID, Foreign Key (`calls.id`, ON DELETE CASCADE), Unique
* `filename`: VARCHAR(255)
* `storage_key`: VARCHAR(512) (Path or object storage URI)
* `mime_type`: VARCHAR(64)
* `size`: INTEGER (Bytes)
* `sample_rate`: INTEGER (Hz, e.g. 16000)
* `channels`: INTEGER (e.g. 1)

### `transcripts`
* `id`: UUID (Primary Key)
* `call_id`: UUID, Foreign Key (`calls.id`, ON DELETE CASCADE), Unique
* `language`: VARCHAR(16)
* `text`: TEXT
* `duration`: DOUBLE PRECISION
* `model`: VARCHAR(64) (e.g. 'whisper')
* `model_version`: VARCHAR(32) (e.g. 'base')

### `transcript_turns`
* `id`: UUID (Primary Key)
* `transcript_id`: UUID, Foreign Key (`transcripts.id`, ON DELETE CASCADE)
* `speaker_id`: VARCHAR(64), Indexed (e.g. 'SPEAKER_00')
* `start_time`: DOUBLE PRECISION
* `end_time`: DOUBLE PRECISION
* `text`: TEXT
* `sequence_number`: INTEGER, Indexed
* `sentiment`: JSONB (`{"label": "NEGATIVE", "score": 0.998}`)
* `intent`: JSONB (`{"intent": "card_issues", "confidence": 0.272}`)
* `entities`: JSONB (`[{"entity_type": "...", "masked_text": "..."}]`)

### `processing_jobs`
* `id`: UUID (Primary Key)
* `call_id`: UUID, Foreign Key (`calls.id`, ON DELETE CASCADE)
* `task_id`: VARCHAR(128), Indexed (Celery task ID)
* `job_type`: VARCHAR(64) (`FULL_CALL_ANALYSIS`)
* `status`: VARCHAR(32), Indexed (`PENDING`, `STARTED`, `PROCESSING`, `SUCCESS`, `FAILURE`, `RETRY`)
* `progress`: INTEGER (0 to 100)
* `current_stage`: VARCHAR(64)
* `stages`: JSONB (Dictionary mapping stage names to statuses)
* `error_code`: VARCHAR(64)
* `error_message`: TEXT

---

## 3. Database Migrations

Migration files located in `docker/migrations/`:
1. `001_create_transcript_embeddings.sql` — pgvector extension and `transcript_embeddings` table.
2. `002_create_theme_discovery_tables.sql` — `theme_discovery_runs`, `themes`, `theme_memberships`.
3. `003_create_escalation_risk_tables.sql` — `escalation_risks`.
4. `004_create_core_backend_tables.sql` — `calls`, `audio_files`, `transcripts`, `transcript_turns`, `processing_jobs`.
