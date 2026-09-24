# AI Call Analytics

AI-powered customer support call analytics platform — Final-Year Project.

## Overview

This system accepts customer-support call recordings and processes them through an AI/ML pipeline to produce transcriptions, speaker diarization, sentiment analysis, intent classification, NER, semantic search, theme discovery, escalation-risk prediction, AI-generated summaries, and analytics dashboards.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React, TypeScript, Vite, Tailwind CSS v4, Recharts, TanStack Query, Zustand, Lucide React |
| **Backend** | Python 3.11, FastAPI, Pydantic, SQLAlchemy (async), Alembic, JWT |
| **AI/ML** | faster-whisper, pyannote.audio, Transformers, spaCy, Sentence Transformers, scikit-learn, UMAP, HDBSCAN, XGBoost |
| **Infrastructure** | PostgreSQL 16 + pgvector, Redis 7, Celery, Docker, Docker Compose |
| **Storage** | S3-compatible object storage |
| **Audio** | FFmpeg, librosa, soundfile |

## Project Structure

```
AI-Call-Analytics/
├── frontend/                # React + TypeScript + Vite
│   └── src/
│       ├── components/      # Reusable UI components
│       ├── pages/           # Page-level components
│       ├── layouts/         # Layout wrappers
│       ├── charts/          # Recharts chart components
│       ├── hooks/           # Custom React hooks
│       ├── services/        # API client functions
│       ├── store/           # Zustand state stores
│       ├── types/           # TypeScript type definitions
│       └── utils/           # Utility functions
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/             # Route handlers
│   │   ├── core/            # Config, logging, security
│   │   ├── database/        # DB connection & sessions
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   ├── workers/         # Celery task definitions
│   │   └── utils/           # Helper utilities
│   └── tests/               # Backend tests
├── ai_service/              # AI/ML processing modules
│   ├── audio/               # Audio preprocessing (FFmpeg, librosa)
│   ├── asr/                 # Speech-to-text (faster-whisper)
│   ├── diarization/         # Speaker diarization (pyannote.audio)
│   ├── sentiment/           # Sentiment analysis
│   ├── intent/              # Intent / issue classification
│   ├── ner/                 # Named Entity Recognition (spaCy)
│   ├── embeddings/          # Semantic embeddings (Sentence Transformers)
│   ├── clustering/          # Theme discovery (UMAP + HDBSCAN)
│   ├── risk/                # Escalation-risk prediction (XGBoost)
│   ├── pipeline/            # End-to-end processing pipeline
│   ├── evaluation/          # Model evaluation utilities
│   ├── datasets/            # Dataset loading & preparation
│   └── models/              # Model management & loading
├── data/
│   ├── raw/                 # Original call recordings
│   ├── processed/           # Preprocessed audio files
│   ├── training/            # Training datasets
│   ├── validation/          # Validation datasets
│   └── evaluation/          # Evaluation / test datasets
├── models/                  # Saved model weights & artifacts
├── notebooks/               # Jupyter notebooks for exploration
├── tests/                   # Integration / E2E tests
├── scripts/                 # Utility scripts
├── docs/                    # Documentation
├── docker/                  # Dockerfiles
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── docker-compose.yml       # Docker Compose services
└── README.md                # This file
```

## Local Development Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 20+** and npm
- **Docker** and **Docker Compose** (for PostgreSQL, Redis)
- **Git**

### 1. Clone & Configure

```bash
git clone <repository-url>
cd AI-Call-Analytics

# Create your environment file
cp .env.example .env
# Edit .env and set your own JWT_SECRET, database password, etc.
```

### 2. Start Infrastructure (PostgreSQL with pgvector + Redis)

```bash
docker compose up -d postgres redis
```

#### Confirming the pgvector Extension:
The PostgreSQL service uses the official `pgvector/pgvector:pg16` image and runs [`docker/init-pgvector.sql`](docker/init-pgvector.sql) on initial startup (`CREATE EXTENSION IF NOT EXISTS vector;`).

To confirm that the extension is enabled:
```bash
docker compose exec postgres psql -U postgres -d ai_call_analytics -c "\dx"
```

Expected output:
```text
                                  List of installed extensions
  Name   | Version |   Schema   |                          Description                           
---------+---------+------------+----------------------------------------------------------------
 plpgsql | 1.0     | pg_catalog | PL/pgSQL procedural language
 vector  | 0.7.x   | public     | vector data type and ivfflat and hnsw access methods
```

### 3. Backend Setup

```bash
# Create virtual environment
cd backend
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the backend (from the project root)
cd ..
uvicorn backend.app.main:app --reload --port 8000
```

### 4. Verify Backend

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"ai-call-analytics-backend"}
```

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at `http://localhost:5173` and display the backend health status.

### Full Docker Setup (All Services)

```bash
# Build and start everything
docker compose up --build

# Frontend → http://localhost:5173
# Backend  → http://localhost:8000
# Health   → http://localhost:8000/health
```

## Current Status

- **Phase 0** — Project Foundation ✅
  - Directory structure created
  - Backend health endpoint working
  - Frontend app shell working
  - Docker Compose configured
  - Environment variables templated

## License

This project is part of a final-year academic project.
