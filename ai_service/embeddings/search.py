"""
AI Call Analytics — Semantic Vector Search & Database Integration Service.

Coordinates:
1. Turn-aware transcript chunking
2. High-dimensional vector embedding generation
3. PostgreSQL + pgvector storage with idempotency and transaction safety
4. Cosine similarity semantic search with top-k ranking and metadata filtering
5. Matrix extraction for downstream Phase 7 theme discovery
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ai_service.diarization.schema import SpeakerAttributedTranscript
from ai_service.embeddings.chunker import TextChunker
from ai_service.embeddings.config import EmbeddingConfig
from ai_service.embeddings.exceptions import (
    InvalidQuery,
    PgVectorUnavailable,
    SearchError,
    VectorDatabaseError,
)
from ai_service.embeddings.manager import EmbeddingModelManager
from ai_service.embeddings.schema import (
    EmbeddingItem,
    SearchQuery,
    SearchResult,
    TranscriptChunk,
)
from backend.app.database.pgvector_checker import check_pgvector_availability
from backend.app.database.session import sync_engine
from backend.app.models.transcript_embedding import TranscriptEmbedding

logger = logging.getLogger("ai_call_analytics.embeddings.search")


def _numpy_cosine_similarity(vec_a: list[float] | np.ndarray, vec_b: list[float] | np.ndarray) -> float:
    """Compute cosine similarity between two numeric vectors in [0.0, 1.0]."""
    a = np.asarray(vec_a, dtype=np.float32)
    b = np.asarray(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    sim = float(np.dot(a, b) / (norm_a * norm_b))
    return max(0.0, min(1.0, sim))


class SemanticSearchService:
    """
    Unified Semantic Search & Vector Storage Service (Phase 6).
    """

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        model_manager: EmbeddingModelManager | None = None,
        chunker: TextChunker | None = None,
    ) -> None:
        """
        Initialize the semantic search service.

        Args:
            config: Optional EmbeddingConfig.
            model_manager: Optional pre-configured EmbeddingModelManager.
            chunker: Optional pre-configured TextChunker.
        """
        self.config = config or EmbeddingConfig.from_env()
        self.model_manager = model_manager or EmbeddingModelManager(config=self.config)
        self.chunker = chunker or TextChunker(
            max_chunk_tokens=self.config.max_chunk_tokens,
            chunk_overlap_turns=self.config.chunk_overlap_turns,
        )

        # In-memory vector cache for local/test execution or when pgvector is unavailable
        self._in_memory_records: list[dict[str, Any]] = []

    def index_transcript(
        self,
        transcript: SpeakerAttributedTranscript,
        call_id: str,
        metadata: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> list[TranscriptChunk]:
        """
        Chunk, embed, and store a speaker-attributed transcript (Step 18, 19).

        Args:
            transcript: Speaker-attributed transcript from Phase 4 alignment.
            call_id: Unique call identifier.
            metadata: Optional metadata (e.g. sentiment, intent).
            session: Optional active SQLAlchemy session.

        Returns:
            List of indexed TranscriptChunk instances.
        """
        chunks = self.chunker.chunk_transcript(
            transcript=transcript,
            call_id=call_id,
            base_metadata=metadata,
        )
        if not chunks:
            logger.warning("No chunks generated for call '%s'", call_id)
            return []

        self.index_chunks(chunks, session=session)
        return chunks

    def index_chunks(
        self,
        chunks: list[TranscriptChunk],
        session: Session | None = None,
    ) -> list[EmbeddingItem]:
        """
        Embed a list of text chunks and persist them to PostgreSQL + pgvector (Step 11, 18, 19).
        Enforces idempotency and transaction safety.
        """
        if not chunks:
            return []

        # 1. Generate embeddings in batch
        texts = [c.text for c in chunks]
        vectors = self.model_manager.embed_batch(texts)

        embedding_items: list[EmbeddingItem] = [
            EmbeddingItem(
                chunk=chunk,
                embedding=vec,
                model_name=self.config.model_name,
                dimension=self.config.dimension,
            )
            for chunk, vec in zip(chunks, vectors)
        ]

        # 2. Check if pgvector is available in the database (only when a database session is provided)
        has_pgvector = False
        if session is not None:
            try:
                has_pgvector = check_pgvector_availability(sync_engine)
            except Exception as e:
                logger.debug("Database check encountered error: %s", e)

        # 3. Store in PostgreSQL if pgvector is available and session provided
        if has_pgvector and session is not None:
            try:
                for item in embedding_items:
                    c = item.chunk
                    # Upsert check for idempotency (Step 19)
                    existing = session.execute(
                        select(TranscriptEmbedding).where(
                            TranscriptEmbedding.call_id == c.call_id,
                            TranscriptEmbedding.chunk_id == c.chunk_id,
                            TranscriptEmbedding.model_name == self.config.model_name,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        existing.text = c.text
                        existing.start_time = c.start
                        existing.end_time = c.end
                        existing.speaker_ids = c.speaker_ids
                        existing.turn_ids = c.turn_ids
                        existing.embedding = item.embedding
                        existing.extra_metadata = c.metadata
                    else:
                        record = TranscriptEmbedding(
                            call_id=c.call_id,
                            chunk_id=c.chunk_id,
                            text=c.text,
                            start_time=c.start,
                            end_time=c.end,
                            speaker_ids=c.speaker_ids,
                            turn_ids=c.turn_ids,
                            embedding=item.embedding,
                            model_name=self.config.model_name,
                            model_version="1.0.0",
                            embedding_dimension=self.config.dimension,
                            extra_metadata=c.metadata,
                        )
                        session.add(record)

                session.commit()
                logger.info("Persisted %d chunks for call to PostgreSQL", len(chunks))
            except Exception as err:
                session.rollback()
                logger.error("Failed to persist vector embeddings to database: %s", err)
                raise VectorDatabaseError(f"Database insertion failed: {err}") from err

        # 4. Always maintain in-memory store for fast retrieval and fallback
        for item in embedding_items:
            c = item.chunk
            # Replace if already in in-memory list (idempotency)
            self._in_memory_records = [
                r for r in self._in_memory_records
                if not (r["call_id"] == c.call_id and r["chunk_id"] == c.chunk_id and r["model_name"] == self.config.model_name)
            ]
            self._in_memory_records.append({
                "chunk_id": c.chunk_id,
                "call_id": c.call_id,
                "text": c.text,
                "speaker_ids": c.speaker_ids,
                "turn_ids": c.turn_ids,
                "start": c.start,
                "end": c.end,
                "embedding": item.embedding,
                "model_name": self.config.model_name,
                "metadata": c.metadata,
            })

        return embedding_items

    def search(
        self,
        query: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> list[SearchResult]:
        """
        Execute semantic similarity search for a query string (Step 21, 23, 24, 25, 27).

        Args:
            query: Natural language search query.
            top_k: Number of highest-similarity chunks to return (capped at max_top_k).
            similarity_threshold: Minimum cosine similarity score threshold.
            filters: Optional metadata filters (e.g. {'call_id': '...', 'speaker': '...'})
            session: Optional active SQLAlchemy session.

        Returns:
            List of SearchResult objects sorted by descending similarity score.
        """
        clean_query = query.strip()
        if not clean_query:
            raise InvalidQuery("Search query cannot be empty or whitespace-only.")

        effective_top_k = min(top_k or self.config.top_k, self.config.max_top_k)
        effective_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else self.config.similarity_threshold
        )
        active_filters = dict(filters or {})

        start_time = time.perf_counter()

        # Step 27: Query MUST be embedded using the SAME model
        query_vector = self.model_manager.embed(clean_query)
        embed_time = time.perf_counter() - start_time

        has_pgvector = False
        if session is not None:
            try:
                has_pgvector = check_pgvector_availability(sync_engine)
            except Exception:
                has_pgvector = False

        db_start = time.perf_counter()
        results: list[SearchResult] = []

        # 1. Search via pgvector in PostgreSQL if available
        if has_pgvector and session is not None:
            try:
                # Cosine distance operator '<=>' in pgvector
                cosine_dist = TranscriptEmbedding.embedding.cosine_distance(query_vector)
                similarity_expr = 1.0 - cosine_dist

                stmt = select(
                    TranscriptEmbedding,
                    similarity_expr.label("similarity"),
                ).where(
                    TranscriptEmbedding.model_name == self.config.model_name
                )

                # Metadata filtering (Step 25)
                if "call_id" in active_filters:
                    stmt = stmt.where(TranscriptEmbedding.call_id == str(active_filters["call_id"]))

                stmt = stmt.order_by(cosine_dist.asc()).limit(effective_top_k * 2)
                db_rows = session.execute(stmt).all()

                for row, sim in db_rows:
                    score = float(sim)
                    # Filter by speaker if requested
                    if "speaker" in active_filters and active_filters["speaker"] not in row.speaker_ids:
                        continue
                    if effective_threshold is not None and score < effective_threshold:
                        continue

                    results.append(
                        SearchResult(
                            chunk_id=row.chunk_id,
                            call_id=row.call_id,
                            text=row.text,
                            speaker_ids=list(row.speaker_ids),
                            turn_ids=list(row.turn_ids),
                            start=row.start_time,
                            end=row.end_time,
                            similarity_score=score,
                            metadata=dict(row.extra_metadata),
                        )
                    )
                    if len(results) >= effective_top_k:
                        break

            except Exception as err:
                logger.error("pgvector database search failed: %s", err)
                raise SearchError(f"Database vector similarity search failed: {err}") from err

        # 2. Fallback to in-memory search
        else:
            candidates: list[tuple[float, dict[str, Any]]] = []
            for record in self._in_memory_records:
                if record["model_name"] != self.config.model_name:
                    continue
                # Filter by call_id
                if "call_id" in active_filters and record["call_id"] != str(active_filters["call_id"]):
                    continue
                # Filter by speaker
                if "speaker" in active_filters and active_filters["speaker"] not in record["speaker_ids"]:
                    continue

                sim = _numpy_cosine_similarity(query_vector, record["embedding"])
                if effective_threshold is not None and sim < effective_threshold:
                    continue

                candidates.append((sim, record))

            # Sort descending by similarity
            candidates.sort(key=lambda x: x[0], reverse=True)

            for sim, record in candidates[:effective_top_k]:
                results.append(
                    SearchResult(
                        chunk_id=record["chunk_id"],
                        call_id=record["call_id"],
                        text=record["text"],
                        speaker_ids=list(record["speaker_ids"]),
                        turn_ids=list(record["turn_ids"]),
                        start=record["start"],
                        end=record["end"],
                        similarity_score=sim,
                        metadata=dict(record["metadata"]),
                    )
                )

        total_time = time.perf_counter() - start_time
        logger.info(
            "Semantic search completed in %.4fs (embed=%.4fs, returned=%d)",
            total_time,
            embed_time,
            len(results),
        )
        return results

    def get_embedding_matrix(
        self,
        call_ids: list[str] | None = None,
        session: Session | None = None,
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """
        Extract complete embedding matrix for Phase 7 theme discovery (UMAP + HDBSCAN) (Step 42).

        Args:
            call_ids: Optional list of call IDs to restrict extraction to.
            session: Optional active SQLAlchemy session.

        Returns:
            Tuple of (numpy ndarray of shape (N, dimension), list of metadata dicts).
        """
        has_pgvector = False
        if session is not None:
            try:
                has_pgvector = check_pgvector_availability(sync_engine)
            except Exception:
                has_pgvector = False

        if has_pgvector and session is not None:
            stmt = select(TranscriptEmbedding).where(
                TranscriptEmbedding.model_name == self.config.model_name
            )
            if call_ids:
                stmt = stmt.where(TranscriptEmbedding.call_id.in_(call_ids))

            rows = session.execute(stmt).scalars().all()
            if not rows:
                return np.empty((0, self.config.dimension), dtype=np.float32), []

            matrix = np.array([r.embedding for r in rows], dtype=np.float32)
            meta = [r.to_dict() for r in rows]
            return matrix, meta

        # Fallback to in-memory records
        records = [
            r for r in self._in_memory_records
            if r["model_name"] == self.config.model_name
            and (not call_ids or r["call_id"] in call_ids)
        ]
        if not records:
            return np.empty((0, self.config.dimension), dtype=np.float32), []

        matrix = np.array([r["embedding"] for r in records], dtype=np.float32)
        meta = [
            {
                "call_id": r["call_id"],
                "chunk_id": r["chunk_id"],
                "text": r["text"],
                "speaker_ids": r["speaker_ids"],
                "turn_ids": r["turn_ids"],
                "start": r["start"],
                "end": r["end"],
                "metadata": r["metadata"],
            }
            for r in records
        ]
        return matrix, meta
