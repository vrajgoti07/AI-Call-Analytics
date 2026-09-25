# AI Call Analytics — Backend Architecture (Phase 10)

## 1. System Overview

The **AI Call Analytics Backend** is built with **FastAPI**, **SQLAlchemy**, **PostgreSQL + pgvector**, and **Redis + Celery**. It provides a production-grade, asynchronous, and decoupled runtime for orchestrating multi-stage conversational AI pipelines (Phases 1–9) and delivering clean REST endpoints for frontend consumption.

```
                    ┌─────────────────────────┐
                    │  React UI (Phase 12)    │
                    └───────────┬─────────────┘
                                │ HTTP / JSON
                                ▼
                    ┌─────────────────────────┐
                    │   FastAPI REST API      │
                    │   (/api/v1/...)         │
                    └───────────┬─────────────┘
                                │
               ┌────────────────┼────────────────┐
               │                │                │
               ▼                ▼                ▼
        PostgreSQL          Redis Queue    Audio Storage
        + pgvector           (Broker)      (Local / S3)
               │                │
               │                ▼
               │          Celery Worker
               │                │
               ▼                ▼
        Analysis Results ◄─ AI Pipeline
```

---

## 2. Layered Responsibilities

The architecture strictly separates concerns into clean, maintainable boundaries:

```
FastAPI Routing Layer (backend/app/api/v1/)
       ↓
Pydantic Schemas & DTOs (backend/app/schemas/)
       ↓
Application Service Layer (backend/app/services/)
       ↓
Background Workers & AI Orchestrator (backend/app/workers/)
       ↓
Repositories & Data Access (backend/app/repositories/)
       ↓
SQLAlchemy ORM Models (backend/app/models/)
       ↓
PostgreSQL 16 + pgvector Database
```

* **API Layer (`backend/app/api/v1/`)**: Pure route handlers, query parameter validation, status codes, and HTTP responses.
* **Schema Layer (`backend/app/schemas/`)**: Pydantic models for incoming requests, outgoing responses, pagination metadata, and error contracts.
* **Service Layer (`backend/app/services/`)**: Business logic, file upload constraints, temporary storage safety, and job dispatching.
* **Worker Layer (`backend/app/workers/`)**: Asynchronous Celery tasks executing the end-to-end AI pipeline outside the HTTP request/response cycle.
* **Repository Layer (`backend/app/repositories/`)**: Encapsulates database queries, eager loading, transactions, and session lifecycle.
* **Model Layer (`backend/app/models/`)**: Declarative SQLAlchemy models reflecting PostgreSQL tables and relations.

---

## 3. Configuration & Environment Separation

Centralized in `backend/app/core/config.py` using `pydantic-settings`:
* Supports `development`, `test`, and `production`.
* Enforces startup environment validation (`validate_environment()`) to prevent running in production with default secrets or wildcard CORS.
* Automatic fallback for local development outside Docker (e.g. resolving `redis://redis:` to `redis://localhost:`).

---

## 4. Observability & Security Foundations

* **Request Correlation**: `RequestCorrelationMiddleware` guarantees every request receives a unique `X-Request-ID` header.
* **Security Headers**: Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`.
* **Standardized Error Responses**: All application errors return a uniform schema:
  ```json
  {
    "error": {
      "code": "CALL_NOT_FOUND",
      "message": "Call record '...' was not found.",
      "request_id": "req_...",
      "details": null
    }
  }
  ```
* **Privacy By Default**: No transcript text, PII, or raw credit card data is logged to server output.
