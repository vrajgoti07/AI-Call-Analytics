# 🎙️ AI Call Analytics — Enterprise Intelligence & Conversation Platform

<p align="center">
  <img src="frontend/src/assets/hero.png" alt="AI Call Analytics Banner" width="100%" style="max-height: 400px; object-fit: cover; border-radius: 12px;" />
</p>

<p align="center">
  <strong>End-to-End Full-Stack Platform for Voice Ingestion, Speech-to-Text, Speaker Diarization, Sentiment Telemetry, and Semantic Search.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19.2-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-6.0-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS v4" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11" />
  <img src="https://img.shields.io/badge/PostgreSQL_16-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL pgvector" />
  <img src="https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose" />
</p>

---

## 📌 Executive Summary

**AI Call Analytics** is a production-oriented, full-stack intelligence platform engineered to turn raw call recordings into actionable operational insights. By combining a **reactive, high-performance TypeScript frontend**, an **asynchronous FastAPI backend**, a **distributed Celery task queue**, and state-of-the-art **Audio AI & NLP pipelines**, this system extracts rich conversational metrics in near real-time.

Key capabilities include:
- **Whisper ASR & PyAnnote Diarization**: Multi-speaker transcription segmented by speaker turn.
- **Sentiment & Risk Telemetry**: Granular sentence-level emotion scoring and churn/escalation risk flagging.
- **Vector Semantic Search**: High-dimensional embeddings stored in **PostgreSQL + pgvector** using HNSW indexing for rapid semantic querying.
- **Dynamic Topic Clustering**: Automatic discovery of emerging customer complaints using UMAP dimensionality reduction and HDBSCAN clustering.
- **Responsive Analytics Dashboard**: Built with React 19, Tailwind CSS v4, Zustand, TanStack Query, and interactive Recharts data visualizations.

---

## 🏗️ System Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Client ["Client Layer (React 19 + TypeScript)"]
        UI["Modern SPA (Vite + Tailwind CSS v4)"]
        State["Zustand Store & TanStack Query"]
        Charts["Recharts Visualizations & Waveforms"]
    end

    subgraph API_Gateway ["Backend Application Layer (FastAPI)"]
        Auth["JWT Auth & Security"]
        Router["Async REST Controllers"]
        Pydantic["Pydantic v2 Data Validation"]
        ServiceLayer["Service & Business Logic"]
    end

    subgraph Task_Queue ["Distributed Processing Layer"]
        Redis["Redis 7 (Message Broker & Result Cache)"]
        Celery["Celery Task Workers (Async Audio Ingestion)"]
    end

    subgraph AI_Engine ["AI / ML Pipeline Microservices"]
        FFmpeg["Audio Normalization & Chunking"]
        ASR["faster-whisper (Speech-to-Text)"]
        Diar["pyannote.audio (Speaker Diarization)"]
        NLP["spaCy (NER) & Sentence-Transformers"]
        ML["XGBoost Risk Classifier & UMAP/HDBSCAN"]
    end

    subgraph Data_Layer ["Persistence & Storage Layer"]
        PG["PostgreSQL 16 (Relational DB)"]
        PGV["pgvector (HNSW Vector Indexing)"]
        Storage["Audio Artifacts Store (S3-Compatible)"]
    end

    UI <--> |HTTPS / REST API| Router
    Router --> ServiceLayer
    ServiceLayer --> |Enqueue Task| Redis
    Redis --> Celery
    Celery --> AI_Engine
    AI_Engine --> |Relational Metadata| PG
    AI_Engine --> |Dense Embeddings (768d)| PGV
    AI_Engine --> |Processed Audio| Storage
    ServiceLayer <--> |Async SQLAlchemy 2.0| PG
    ServiceLayer <--> |Vector Similarity Search| PGV
```

---

## 🚀 Key Engineering & Full-Stack Highlights

### 💻 Frontend Architecture
- **React 19 + TypeScript**: Statically typed component ecosystem with strict linting (`oxlint`) and zero runtime type regressions.
- **Tailwind CSS v4 & Glassmorphism Design System**: Tailored dark-mode UI with sleek glass surfaces, vibrant micro-interactions, and accessible typography.
- **TanStack Query v5**: Server-state synchronization, optimistic updates, intelligent caching, and network resilience.
- **Zustand State Management**: Lightweight, boilerplate-free client state for audio playback, active filter criteria, and active transcript markers.
- **Recharts Analytics**: Real-time rendering of call sentiment timelines, speaker talk-time ratios, customer intent distributions, and agent performance matrices.

### ⚙️ Backend & API Engineering
- **Asynchronous FastAPI Engine**: Non-blocking I/O with Python 3.11 `asyncio` and `uvicorn`, maximizing throughput for file uploads and analytical queries.
- **Clean Layered Architecture**: Strict separation of concerns across Routes (`api/`), Domain Services (`services/`), ORM Models (`models/`), and Schemas (`schemas/`).
- **SQLAlchemy 2.0 (Async) + Alembic**: Declarative async ORM mappings with full migration history and connection pooling via `asyncpg`.
- **Stateless Authentication**: High-security JWT (JSON Web Tokens) with Argon2/Bcrypt password hashing and role-based access control (RBAC).
- **Structured Logging**: Production JSON telemetry using `structlog` for correlation tracing across distributed worker tasks.

### 🧠 Distributed Systems & Vector Search
- **Decoupled Heavy Computation**: Audio transcription and ML inference are offloaded to **Celery** workers backed by **Redis**, ensuring API responsiveness under high ingest loads.
- **PostgreSQL 16 + pgvector**: Hybrid storage enabling relational joins between call metadata and 768-dimensional dense semantic vectors. Accelerated via HNSW (Hierarchical Navigable Small World) indices.
- **Dual Pipeline Execution**: Optimized for both batch historical ingestion and near-real-time streaming analytics.

---

## 🛠️ Technology Stack Breakdown

| Domain | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19, TypeScript, Vite | Core SPA foundation & build pipeline |
| **Styling & UI** | Tailwind CSS v4, Lucide React | Responsive UI, modern aesthetic tokens, iconography |
| **State & Cache** | TanStack Query v5, Zustand v5 | Server state caching & client UI state |
| **Visualization** | Recharts 3.x | Visual metrics (sentiment over time, talk ratios) |
| **Backend API** | FastAPI, Pydantic v2, Uvicorn | High-performance asynchronous REST API |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic | Relational data persistence & migrations |
| **Vector Engine** | pgvector extension (pg16) | High-dimensional embedding storage & HNSW similarity search |
| **Queue & Cache** | Redis 7, Celery 5.4 | Task queue for async background processing |
| **Audio Processing** | FFmpeg, librosa, soundfile | Audio format normalization, resampling (16kHz), VAD |
| **Speech & NLP AI** | faster-whisper, pyannote.audio, spaCy | Automatic Speech Recognition, Diarization, NER |
| **Machine Learning** | Sentence-Transformers, UMAP, HDBSCAN, XGBoost | Intent classification, clustering, escalation risk scoring |
| **DevOps & Infra** | Docker, Docker Compose, Multi-stage builds | Containerized local & production orchestration |

---

## 📂 Repository Directory Layout

```text
AI-Call-Analytics/
├── frontend/                     # Modern React 19 + TypeScript SPA
│   ├── src/
│   │   ├── charts/               # Recharts visualization modules
│   │   ├── components/           # Reusable UI components & design system
│   │   ├── hooks/                # Custom React hooks (useAudioPlayer, useAnalytics)
│   │   ├── layouts/              # Dashboard shell and responsive navigation
│   │   ├── pages/                # Page views (Dashboard, Calls, Details, Settings)
│   │   ├── services/             # Axios/Fetch API client functions
│   │   ├── store/                # Zustand client stores
│   │   ├── types/                # TypeScript interface contracts
│   │   └── utils/                # Formatting, calculations & helpers
│   ├── package.json              # Frontend manifest
│   └── vite.config.ts            # Vite bundler configuration
│
├── backend/                      # Scalable FastAPI Microservice
│   ├── app/
│   │   ├── api/                  # API endpoints & route versioning (/api/v1)
│   │   ├── core/                 # App configuration, security & structured logging
│   │   ├── database/             # Async session factory & base models
│   │   ├── models/               # SQLAlchemy 2.0 ORM entities
│   │   ├── schemas/              # Pydantic v2 input/output data schemas
│   │   ├── services/             # Business logic & domain services
│   │   ├── utils/                # Cryptography, token handling & helpers
│   │   └── workers/              # Celery task definitions
│   ├── tests/                    # Pytest backend test suite
│   └── requirements.txt          # Python backend dependencies
│
├── ai_service/                   # ML & Speech Intelligence Pipeline
│   ├── audio/                    # Audio normalization, silence trimming (FFmpeg)
│   ├── asr/                      # Speech-to-text inference (faster-whisper)
│   ├── diarization/              # Speaker diarization & turn-taking (pyannote.audio)
│   ├── sentiment/                # Turn-by-turn polarity & emotion scoring
│   ├── intent/                   # Customer intent classification
│   ├── ner/                      # PII redaction & named entity recognition
│   ├── embeddings/               # Semantic vector generation
│   ├── clustering/               # Unsupervised call clustering (UMAP + HDBSCAN)
│   ├── risk/                     # Churn & escalation risk model (XGBoost)
│   └── pipeline/                 # End-to-end composite pipeline orchestrator
│
├── docker/                       # Production & Dev Dockerfiles
│   ├── backend.Dockerfile        # Multi-stage Python FastAPI container
│   ├── frontend.Dockerfile       # Node build & static serve container
│   └── init-pgvector.sql         # DB bootstrap script with vector extension
│
├── data/                         # Local storage for audio tiers & datasets
├── docs/                         # Comprehensive engineering documentation
├── docker-compose.yml            # Complete multi-service orchestration
└── .env.example                  # Environment configuration template
```

---

## ⚡ Quick Start & Development Setup

### Prerequisites
- **Docker & Docker Compose** (Recommended for easiest setup)
- **Node.js 20+** & **Python 3.11+** (For native development)
- **FFmpeg** (For local audio processing)

---

### Option A: Complete Docker Compose Setup (Recommended)

Run the entire platform (Frontend, Backend, PostgreSQL with `pgvector`, and Redis) with a single command:

```bash
# 1. Clone repository
git clone https://github.com/vrajgoti07/AI-Call-Analytics.git
cd AI-Call-Analytics

# 2. Configure environment
cp .env.example .env

# 3. Spin up all containerized services
docker compose up --build -d
```

#### Access Points:
- 🌐 **Web Application Dashboard**: [http://localhost:5173](http://localhost:5173)
- 🔌 **FastAPI Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Backend Health Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option B: Local Native Development Setup

#### 1. Start Infrastructure (Postgres + Redis)
```bash
docker compose up -d postgres redis
```

Verify `pgvector` extension:
```bash
docker compose exec postgres psql -U postgres -d ai_call_analytics -c "\dx"
```

#### 2. Backend Service Setup
```bash
cd backend

# Setup virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server with hot-reload
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend Application Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

---

## 🧪 Testing & Code Quality

```bash
# Run backend test suite
cd backend
pytest -v

# Run frontend linting
cd frontend
npm run lint

# Build production bundle
npm run build
```

---

## 🗺️ Project Milestones & Roadmap

- [x] **Phase 0 — System Architecture & Foundations**
  - [x] Dockerized environment with PostgreSQL 16 + pgvector & Redis 7.
  - [x] Clean architecture skeleton for FastAPI backend and React 19 client.
  - [x] Strict typing setup with TypeScript 6 and Pydantic v2.
- [ ] **Phase 1 — Ingestion & Speech Intelligence**
  - [ ] Multi-format audio upload API with S3 artifact persistence.
  - [ ] Asynchronous Celery audio pipeline with `faster-whisper` and `pyannote.audio`.
  - [ ] Turn-level speaker transcription storage.
- [ ] **Phase 2 — NLP & Semantic Vector Search**
  - [ ] Sentiment trajectory analysis per call segment.
  - [ ] Dense embeddings via Sentence Transformers stored in `pgvector`.
  - [ ] Hybrid text & semantic search endpoint.
- [ ] **Phase 3 — Analytics & Executive Dashboards**
  - [ ] Interactive waveforms with synchronized transcript playback.
  - [ ] Escalation risk alerting and agent performance metrics.
  - [ ] Unsupervised trend & topic clustering with UMAP + HDBSCAN.

---

## 📄 License & Attribution

Developed as a Final-Year Engineering Project demonstrating modern **Full-Stack Software Engineering**, **Distributed Microservices**, and **Applied AI Systems**.

Distributed under the MIT License. See `LICENSE` for more information.
