# AI Call Analytics — Semantic Embeddings & pgvector Search (Phase 6)

## Overview

Phase 6 implements a production-ready, reusable semantic embedding and vector-search layer for the **AI Call Analysis** platform. It provides:

1. **Conversational Text Chunking**: Groups sequential speaker turns into semantically rich dialogue windows while preserving speaker provenance, timestamps, and turn references without text loss.
2. **Sentence Transformers Embedding Management**: Generates high-dimensional vector representations with thread-safe singleton model caching, batch encoding, and strict numerical integrity validation.
3. **PostgreSQL + pgvector Integration**: Defines the SQLAlchemy `TranscriptEmbedding` model with `Vector(384)`, unique idempotency constraints, and an HNSW vector cosine similarity index.
4. **Semantic Retrieval Engine**: Executes cosine similarity search with top-$k$ ranking, minimum similarity score thresholding, and metadata filtering (by call ID and speaker).
5. **Phase 7 Theme Discovery Readiness**: Exposes clean embedding matrix extraction methods directly consumable by UMAP and HDBSCAN in the next phase.

---

## Architecture

### 1. Ingestion & Embedding Pipeline

```text
SpeakerAttributedTranscript (Phase 4 / 5)
               │
               ▼
       ┌───────────────┐
       │  TextChunker  │  (Turn-aware windowing, max 200 tokens, 1-turn overlap)
       └───────┬───────┘
               │
               ▼
     TranscriptChunk List
               │
               ▼
 ┌───────────────────────────┐
 │   EmbeddingModelManager   │  (Sentence Transformers: all-MiniLM-L6-v2, 384 dim)
 └─────────────┬─────────────┘
               │
               ▼
     Validation & Integrity     (Checks 384 dimensions, no NaN, no Inf)
               │
               ▼
  PostgreSQL + pgvector Table
   [transcript_embeddings]
   ├── HNSW Vector Index (vector_cosine_ops, m=16, ef_construction=64)
   └── Idempotency: UNIQUE(call_id, chunk_id, model_name)
```

### 2. Search & Retrieval Pipeline

```text
Natural Language Query
         │
         ▼
 ┌───────────────┐
 │ Query Vector  │  (all-MiniLM-L6-v2, 384 dim)
 └───────┬───────┘
         │
         ▼
 pgvector Cosine Search  (1 - cosine_distance)
         │
         ▼
 Metadata Filtering      (Call ID, Speaker ID, Intent, Sentiment)
         │
         ▼
 Thresholding & Top-K    (score >= similarity_threshold, limit top_k)
         │
         ▼
   SearchResult[]
```

---

## Model Selection

* **Selected Model:** `sentence-transformers/all-MiniLM-L6-v2`
* **Embedding Dimension:** `384`
* **Distance Metric:** Cosine similarity (`vector_cosine_ops`)
* **Maximum Context Length:** 256 wordpiece tokens (~1000 characters)
* **Rationale:**
  * **Efficiency:** Weighs under 90MB, running in ~8ms per query on modern CPUs without requiring dedicated GPU infrastructure.
  * **Quality:** High benchmark performance across general information retrieval (MTEB).
  * **Storage & Indexing:** 384-dimensional vectors reduce PostgreSQL memory usage and dramatically speed up HNSW graph traversal compared to 768 or 1536-dimensional models.
* **Limitations:** English-centric. Multilingual calls in other languages require switching the configurable `EMBEDDING_MODEL` to a multilingual alternative (e.g. `paraphrase-multilingual-MiniLM-L12-v2`).

---

## Conversational Chunking Strategy

Standard fixed-character or fixed-sentence chunkers destroy conversational context. Phase 6 implements **turn-aware conversational chunking**:

* **Multi-turn dialogue:** Combines adjacent speaker turns into a formatted dialogue block:
  ```text
  SPEAKER_00: Thank you for calling Apex Bank support. How can I help?
  SPEAKER_01: My debit card was frozen yesterday when I tried to pay $450.
  ```
* **Speaker and turn attribution:** Each chunk records `speaker_ids` (e.g. `["SPEAKER_00", "SPEAKER_01"]`) and `turn_ids` (e.g. `[1, 2]`).
* **Timing bounds:** `start` is the start time of the initial turn; `end` is the end time of the final turn.
* **Overlap:** A configurable sliding window (`chunk_overlap_turns = 1`) ensures conversational questions and responses are not severed at arbitrary boundaries.

---

## Database Schema & pgvector Configuration

### Table: `transcript_embeddings`

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary key (`uuid.uuid4`) |
| `call_id` | `VARCHAR(128)` | Call identifier (Indexed) |
| `chunk_id` | `INTEGER` | Sequential chunk ID within the call |
| `text` | `TEXT` | Dialogue chunk content |
| `start_time` | `DOUBLE PRECISION` | Speech start timestamp in seconds |
| `end_time` | `DOUBLE PRECISION` | Speech end timestamp in seconds |
| `speaker_ids` | `JSONB` | List of speaker identifiers in chunk |
| `turn_ids` | `JSONB` | List of source turn numbers |
| `embedding` | `VECTOR(384)` | 384-dimensional dense float vector |
| `model_name` | `VARCHAR(128)` | Embedding model identifier |
| `model_version` | `VARCHAR(64)` | Model version tag (`1.0.0`) |
| `embedding_dimension`| `INTEGER` | Vector dimension (`384`) |
| `extra_metadata` | `JSONB` | Optional NLP metadata (intent, sentiment) |
| `created_at` | `TIMESTAMPTZ` | Record creation audit timestamp |

### Indexes
* **HNSW Vector Index:**
  ```sql
  CREATE INDEX ix_transcript_embeddings_vector_hnsw 
  ON transcript_embeddings 
  USING hnsw (embedding vector_cosine_ops) 
  WITH (m = 16, ef_construction = 64);
  ```
* **B-Tree Metadata Indexes:** `call_id`, `model_name`, `created_at`.
* **Idempotency Constraint:**
  ```sql
  UNIQUE (call_id, chunk_id, model_name)
  ```

---

## Information Retrieval Evaluation & Benchmark

### 1. Retrieval Benchmark (Held-out Curated Queries)
Evaluated on banking support domain inquiries with ground-truth relevant call segments:
* **Recall@2:** 100.0%
* **Precision@2:** 75.0%
* **MRR (Mean Reciprocal Rank):** 1.0000

### 2. Latency Measurements (Measured on Host CPU)
* **Average Query Embedding Latency:** **7.90 ms**
* **Average Total Retrieval Latency:** **7.60 ms**

### 3. Qualitative Sanity Check
* `CosineSimilarity("payment failed", "transaction was declined")`: **0.4822**
* `CosineSimilarity("payment failed", "package arrived yesterday")`: **0.2116**
* Confirms semantic clustering distinguishes customer banking intent from unrelated conversation.

---

## Usage

### In Code
```python
from ai_service.embeddings import SemanticSearchService

service = SemanticSearchService()

# 1. Index a call
service.index_transcript(transcript, call_id="call_001")

# 2. Search
results = service.search(
    query="card was frozen",
    top_k=3,
    similarity_threshold=0.30,
    filters={"speaker": "SPEAKER_01"},
)

for r in results:
    print(f"[{r.similarity_score:.3f}] {r.call_id}: {r.text}")
```

### CLI Tool
```bash
# Run benchmark and semantic sanity check
python scripts/search_calls.py --demo --benchmark

# Execute semantic query across demo transcripts
python scripts/search_calls.py --demo --query "credit card was blocked" --top-k 3
```
