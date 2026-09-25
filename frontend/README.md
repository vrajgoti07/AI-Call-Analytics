# AI Call Analytics — Frontend Architecture & UI Foundation (Phase 11)

Production-oriented React 19 + TypeScript + Vite web application for the **AI Call Analysis** platform, built on real Phase 10 FastAPI backend contracts.

---

## 1. Architecture Overview

The frontend is architected around a scalable, feature-oriented structure with clear separation of concerns:

```text
frontend/src/
├── api/                  # Centralized HTTP client and Phase 10 API services
│   ├── client.ts         # Base fetch client with ApiError normalization & query builder
│   ├── types.ts          # TypeScript domain contracts mirroring FastAPI Pydantic schemas
│   ├── calls.ts          # Calls CRUD, audio upload, and streaming endpoints
│   ├── transcript.ts     # Transcript overview and turn retrieval
│   ├── analysis.ts       # Pipeline trigger (POST /analyze) and status polling
│   ├── risk.ts           # Multi-modal escalation risk retrieval
│   ├── search.ts         # Semantic vector search (POST /search/semantic)
│   ├── themes.ts         # Discovered theme clusters (GET /themes)
│   ├── jobs.ts           # Asynchronous Celery task status (GET /jobs)
│   ├── evaluation.ts     # Phase 9 AI benchmarks (GET /evaluation)
│   └── system.ts         # Health (/health) and readiness (/health/ready)
│
├── components/           # Reusable atomic and composite UI components
│   ├── layout/           # ApplicationShell, Sidebar, TopHeader, Breadcrumbs
│   ├── ui/               # Button, Input, Select, Badge, StatusBadge, SentimentBadge,
│   │                     # RiskBadge, MetricCard, Modal, Drawer, Tabs, EmptyState,
│   │                     # LoadingSkeleton, ErrorAlert
│   ├── audio/            # AudioPlayerDock (synchronized audio playback scrubber)
│   ├── transcript/       # TranscriptViewer (turns stream, seekable, masked NER tags)
│   └── risk/             # RiskScoreCard (explainable score meter & waterfall factors)
│
├── pages/                # Screen-level route views
│   ├── OverviewPage.tsx      # Operational KPI cards, status donut chart, recent queue
│   ├── CallsPage.tsx         # Filterable calls table, pagination, audio upload modal
│   ├── CallDetailPage.tsx    # Audio scrubber, turn-by-turn dialogue, risk explainability
│   ├── SearchPage.tsx        # Semantic vector search with threshold slider & deep links
│   ├── ThemesPage.tsx        # Topic clusters, c-TF-IDF keywords, noise & silhouette stats
│   ├── ThemeDetailPage.tsx   # Exemplar dialogue turns and cluster keywords
│   ├── RiskPage.tsx          # Escalation risk distribution and review queue
│   ├── EvaluationPage.tsx    # Stage-by-stage benchmarks (WER, DER, Intent F1, confusion)
│   ├── JobsPage.tsx          # Background Celery task tracker and stage progress bars
│   └── SettingsPage.tsx      # Infrastructure health and production model registry
│
├── hooks/                # TanStack Query server-state hooks
├── stores/               # Zustand client-only state stores (UI & Audio player sync)
├── lib/                  # Utilities, formatting helpers (duration, timestamp, %, bytes)
├── router/               # React Router route tree
└── styles/               # Tailwind CSS v4 styling & dark theme tokens
```

---

## 2. Technology Stack

- **Core**: React 19, TypeScript (target: `ES2023`), Vite 8
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`) with custom dark slate design tokens
- **Routing**: React Router DOM v7
- **Server State**: TanStack Query (React Query) v5
- **Client State**: Zustand v5
- **Icons**: Lucide React
- **Data Visualization**: Recharts v3
- **Testing**: Vitest v5, `@testing-library/react`, `@testing-library/jest-dom`
- **Linting**: Oxlint

---

## 3. Environment Variables

Create `.env` in the `frontend` root:

```env
# URL pointing to the FastAPI backend (defaults to http://localhost:8000)
VITE_API_BASE_URL=http://localhost:8000
```

> **Security Note**: Never place API keys, private passwords, or database credentials in `VITE_*` environment variables. Anything prefixed with `VITE_` is bundled into client-side assets.

---

## 4. Development & Build Commands

All standard scripts are managed via `package.json`:

```bash
# Start local development server (http://localhost:5173)
npm run dev

# Run TypeScript compilation check
npm run typecheck

# Run linter
npm run lint

# Run unit and component test suites
npm run test

# Run tests in interactive watch mode
npm run test:watch

# Build production bundle for deployment
npm run build

# Preview production build locally
npm run preview
```

---

## 5. State Management Architecture

- **Server State (TanStack Query)**:
  - Exclusively handles API queries, mutation lifecycle, and cache invalidation.
  - Queries: `useCalls`, `useCall`, `useTranscript`, `useTranscriptTurns`, `useAnalysisStatus`, `useRisk`, `useThemes`, `useJobs`, `useEvaluation`, `useSystemHealth`.
  - Configured with `staleTime`, background polling for active jobs (`refetchInterval`), and automatic invalidation on mutations.
- **Client State (Zustand)**:
  - `uiStore`: Controls desktop sidebar toggle, mobile navigation drawer, and global search modals.
  - `audioPlayerStore`: Synchronizes browser `<audio>` playback timestamp with the audio scrubber and highlighted transcript turn cards.
- **URL State**:
  - Filter and pagination params (`?status=COMPLETED&page=2`), deep-linking timestamps (`/calls/:id?t=42`), and search queries (`/search?q=card+declined`).

---

## 6. Accessibility & AI Transparency Rules

1. **Dual-Indicator Semantics**:
   - Status, sentiment, and escalation risk are never communicated by color alone. Every indicator is accompanied by explicit text and symbol (e.g. `HIGH RISK [▲]`, `COMPLETED [✓]`).
2. **Speaker Identification**:
   - Uses actual backend identifiers (`SPEAKER_00`, `SPEAKER_01`) from pyannote diarization without inferring unverified "Agent" or "Customer" roles.
3. **Privacy-Preserving NER**:
   - All extracted PII tokens (card numbers, dates, monetary amounts) are displayed in privacy-masked format (`•••• 4128`).
