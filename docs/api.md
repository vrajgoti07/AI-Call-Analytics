# AI Call Analytics — API Contract Reference (Phase 10)

Base Prefix: `/api/v1`

---

## 1. Health Endpoints

### `GET /health`
* **Summary**: Basic health status.
* **Response `200 OK`**:
  ```json
  {
    "status": "ok",
    "service": "ai-call-analytics-backend",
    "environment": "development",
    "version": "1.0.0"
  }
  ```

### `GET /health/live`
* **Summary**: Kubernetes / container liveness probe.
* **Response `200 OK`**: `{"status": "alive"}`

### `GET /health/ready`
* **Summary**: Readiness probe testing PostgreSQL and Redis connectivity.
* **Response `200 OK`** or **`503 Service Unavailable`**:
  ```json
  {
    "status": "ready",
    "dependencies": {
      "database": "connected",
      "redis": "connected"
    }
  }
  ```

---

## 2. Calls Endpoints

### `POST /api/v1/calls`
* **Summary**: Create a new Call record.
* **Request Body**:
  ```json
  {
    "external_id": "CRM-10492",
    "language": "en"
  }
  ```
* **Response `201 Created`**:
  ```json
  {
    "id": "e4b5239a-5694-4d87-bfbc-857c32bf28a4",
    "external_id": "CRM-10492",
    "status": "UPLOADED",
    "duration": null,
    "language": "en",
    "created_at": "2026-09-24T18:00:00Z",
    "updated_at": "2026-09-24T18:00:00Z",
    "audio_file": null
  }
  ```

### `POST /api/v1/calls/{call_id}/upload`
* **Summary**: Upload audio file for a call.
* **Multipart Form**: `file` (.wav, .mp3, .flac).
* **Response `200 OK`**: Returns CallResponse with attached AudioFile metadata.
* **Errors**: `404 Not Found`, `413 Payload Too Large`, `415 Unsupported Media Type`.

### `GET /api/v1/calls`
* **Summary**: List calls with filtering and pagination.
* **Query Params**:
  * `status`: Optional filter (`UPLOADED`, `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`)
  * `language`: Optional language filter
  * `page`: Default 1
  * `page_size`: Default 20 (max 100)
* **Response `200 OK`**:
  ```json
  {
    "items": [...],
    "pagination": {
      "total": 42,
      "page": 1,
      "page_size": 20,
      "total_pages": 3
    }
  }
  ```

### `GET /api/v1/calls/{call_id}`
* **Summary**: Retrieve detailed call metadata.
* **Response `200 OK`**: Returns CallDetailResponse with summary flags (`has_transcript`, `has_risk_analysis`, `latest_job_id`).

### `DELETE /api/v1/calls/{call_id}`
* **Summary**: Delete call and cascade delete audio, transcript, and risk records.
* **Response `204 No Content`**.

---

## 3. Analysis & Pipeline Endpoints

### `POST /api/v1/calls/{call_id}/analyze`
* **Summary**: Trigger background asynchronous analysis pipeline.
* **Request Body** (optional):
  ```json
  {
    "force_reprocess": false
  }
  ```
* **Response `202 Accepted`**:
  ```json
  {
    "call_id": "...",
    "status": "PENDING",
    "progress": 0,
    "current_stage": null,
    "stages": {
      "preprocessing": "PENDING",
      "transcription": "PENDING",
      "diarization": "PENDING",
      "nlp": "PENDING",
      "embeddings": "PENDING",
      "themes": "PENDING",
      "risk": "PENDING"
    },
    "job_id": "..."
  }
  ```

### `GET /api/v1/calls/{call_id}/analysis/status`
* **Summary**: Real-time progress and stage tracking.
* **Response `200 OK`**: Returns current stage, progress (0–100%), and stage dictionary.

### `GET /api/v1/calls/{call_id}/analysis`
* **Summary**: Consolidated call analytics overview.
* **Response `200 OK`**:
  ```json
  {
    "call_id": "...",
    "status": "COMPLETED",
    "duration": 18.5,
    "transcript_summary": "...",
    "speaker_count": 2,
    "dominant_sentiment": "POSITIVE",
    "primary_intent": "card_issues",
    "risk_level": "LOW",
    "risk_score": 16.03,
    "theme_count": 0,
    "themes": [],
    "created_at": "..."
  }
  ```

---

## 4. Transcript & Turns Endpoints

### `GET /api/v1/calls/{call_id}/transcript`
* **Summary**: Call-level transcript overview and turn count.

### `GET /api/v1/calls/{call_id}/transcript/turns`
* **Summary**: Paginated speaker turns with NLP enrichments.
* **Response `200 OK`**:
  ```json
  {
    "call_id": "...",
    "transcript_id": "...",
    "items": [
      {
        "id": "...",
        "speaker_id": "SPEAKER_01",
        "start_time": 3.5,
        "end_time": 9.0,
        "text": "Hi, I have an issue with my debit card...",
        "sequence_number": 2,
        "sentiment": {"label": "NEGATIVE", "score": 0.998},
        "intent": {"intent": "card_issues", "confidence": 0.272},
        "entities": []
      }
    ],
    "pagination": {"total": 3, "page": 1, "page_size": 50, "total_pages": 1}
  }
  ```

---

## 5. Risk & Search Endpoints

### `GET /api/v1/calls/{call_id}/risk`
* **Summary**: Retrieve persisted multi-modal escalation risk assessment.

### `POST /api/v1/search/semantic`
* **Summary**: Vector similarity search over transcript chunks.
* **Request Body**:
  ```json
  {
    "query": "card was declined at store",
    "top_k": 5,
    "similarity_threshold": 0.5
  }
  ```

### `GET /api/v1/themes`
* **Summary**: Discovered theme clusters and keyword statistics.

### `GET /api/v1/jobs/{job_id}`
* **Summary**: Background task state inspection.
