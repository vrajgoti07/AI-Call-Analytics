# AI Call Analytics — Background Jobs Architecture (Phase 10)

## 1. Asynchronous Task Design

Long-running speech and AI processing operations (such as Whisper transcription, diarization, and transformer inference) must never block synchronous HTTP request threads.

The system uses **Redis** as a distributed message broker and **Celery** workers to execute the complete AI pipeline.

```
FastAPI (Client Request)
      ↓
JobRepository.create_job()  -> ProcessingJob (Status: PENDING)
      ↓
analyze_call_task.delay()   -> Redis Broker Queue
      ↓
HTTP 202 Accepted (Return job_id to client immediately)
```

---

## 2. Pipeline Execution Stages

The Celery task `pipeline.analyze_call` coordinates Phases 1–8:

| Stage | Progress | Description | Reused Module |
| :--- | :--- | :--- | :--- |
| `preprocessing` | 5% → 15% | Audio format validation, 16kHz mono normalization | `ai_service.audio.preprocessor` |
| `transcription` | 25% → 40% | Whisper ASR speech-to-text with segment timestamps | `ai_service.asr.transcriber` |
| `diarization` | 50% → 60% | Speaker turn alignment and turn persistence | `ai_service.diarization` |
| `nlp` | 65% → 75% | Turn sentiment, MInDS-14 intent, and masked NER | `ai_service.pipeline.nlp_analyzer` |
| `embeddings` | 80% → 85% | SentenceTransformer vectors and vector indexing | `ai_service.embeddings` |
| `themes` | 88% → 90% | Cluster discovery and theme matching | `ai_service.clustering` |
| `risk` | 92% → 98% | Multi-modal escalation risk scoring & explainability | `ai_service.risk.service` |
| `COMPLETED` | 100% | Finalizes Call and ProcessingJob status | `CallRepository` & `JobRepository` |

---

## 3. Idempotency & Fault Tolerance

1. **Idempotent Execution**: If a call is already marked `COMPLETED` and `force_reprocess=False`, the task terminates immediately without duplicating database records.
2. **Transient vs Permanent Failures**:
   * Transient connection or timeout errors trigger controlled exponential backoff retries (`max_retries=3`).
   * Deterministic errors (e.g. invalid audio format, corrupt file) mark the `ProcessingJob` as `FAILURE` with specific `error_code` and `error_message`, and set `Call.status = FAILED`.
3. **No Duplicate Relational Records**: Existing transcript turns and risk records are updated or cleared on re-processing, preventing duplicate database entries.

---

## 4. Running Workers Locally

To run the Celery worker locally:

```bash
# Windows
python -m celery -A backend.app.workers.celery_app.celery_app worker -l info -P solo

# Linux / Docker
celery -A backend.app.workers.celery_app.celery_app worker -l info -c 2
```
