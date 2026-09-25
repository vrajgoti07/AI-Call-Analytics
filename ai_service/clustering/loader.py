"""
AI Call Analytics — Embedding Loader & Validation Service.

Loads stored high-dimensional embeddings from PostgreSQL/pgvector or in-memory fixtures (Step 6),
validates dimensions, filters NaNs/Infs, enforces minimum dataset requirements (Step 8),
and deduplicates clustering input (Step 9) without modifying database records.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_service.clustering.config import ThemeDiscoveryConfig
from ai_service.clustering.exceptions import (
    InsufficientEmbeddingsError,
    InvalidEmbeddingDataError,
)
from backend.app.models.transcript_embedding import TranscriptEmbedding

logger = logging.getLogger("ai_call_analytics.clustering.loader")


class EmbeddingLoader:
    """
    Loads, validates, and filters embeddings for theme discovery.
    """

    def __init__(self, config: ThemeDiscoveryConfig | None = None) -> None:
        """Initialize the embedding loader."""
        self.config = config or ThemeDiscoveryConfig.from_env()

    def load_from_db(
        self,
        session: Session,
        call_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """
        Load embeddings directly from PostgreSQL/pgvector table 'transcript_embeddings' (Step 6).
        """
        stmt = select(TranscriptEmbedding).where(
            TranscriptEmbedding.model_name == self.config.expected_model_name
        )
        if call_ids:
            stmt = stmt.where(TranscriptEmbedding.call_id.in_(call_ids))
        if limit:
            stmt = stmt.limit(limit)

        rows = session.execute(stmt).scalars().all()
        if not rows:
            raise InsufficientEmbeddingsError(
                f"No embeddings found in database matching model '{self.config.expected_model_name}'"
            )

        raw_vectors = [r.embedding for r in rows]
        metadata = [r.to_dict() for r in rows]

        return self.validate_and_prepare(raw_vectors, metadata)

    def validate_and_prepare(
        self,
        vectors: list[list[float]] | np.ndarray,
        metadata: list[dict[str, Any]],
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """
        Validate vector dimensionality, numerical integrity, minimum count, and deduplicate (Steps 7, 8, 9).

        Returns:
            Tuple of (clean float32 numpy array of shape (N, dimension), aligned metadata list).
        """
        if len(vectors) != len(metadata):
            raise InvalidEmbeddingDataError(
                f"Vector count ({len(vectors)}) does not match metadata count ({len(metadata)})"
            )

        n_initial = len(vectors)
        if n_initial < self.config.min_embeddings:
            raise InsufficientEmbeddingsError(
                f"Theme discovery requires at least {self.config.min_embeddings} embeddings, "
                f"but only {n_initial} were provided."
            )

        arr = np.asarray(vectors, dtype=np.float32)

        # 1. Dimension validation (Step 7)
        if arr.ndim != 2 or arr.shape[1] != self.config.expected_dimension:
            raise InvalidEmbeddingDataError(
                f"Embedding dimension mismatch: expected ({self.config.expected_dimension}), "
                f"got shape {arr.shape}"
            )

        # 2. NaN / Inf validation (Step 7)
        invalid_mask = np.isnan(arr).any(axis=1) | np.isinf(arr).any(axis=1)
        n_invalid = int(np.sum(invalid_mask))
        if n_invalid > 0:
            logger.warning("Filtered out %d embeddings containing NaN or Infinite values", n_invalid)
            valid_indices = np.where(~invalid_mask)[0]
            arr = arr[valid_indices]
            metadata = [metadata[i] for i in valid_indices]

        # 3. Deduplication for clustering dataset (Step 9)
        # Identify duplicates by (call_id, chunk_id)
        seen_keys: set[tuple[str, int]] = set()
        unique_indices: list[int] = []

        for idx, meta in enumerate(metadata):
            call_id = str(meta.get("call_id", ""))
            chunk_id = int(meta.get("chunk_id", idx))
            key = (call_id, chunk_id)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_indices.append(idx)

        n_duplicates = len(metadata) - len(unique_indices)
        if n_duplicates > 0:
            logger.info("Deduplicated %d duplicate chunks from clustering dataset", n_duplicates)
            arr = arr[unique_indices]
            metadata = [metadata[i] for i in unique_indices]

        # Re-check minimum threshold after cleaning
        if len(arr) < self.config.min_embeddings:
            raise InsufficientEmbeddingsError(
                f"After validation and deduplication, only {len(arr)} valid embeddings remain, "
                f"which is below the minimum threshold ({self.config.min_embeddings})."
            )

        logger.info(
            "Embedding validation complete: %d valid embeddings ready (dim=%d)",
            len(arr),
            arr.shape[1],
        )
        return arr, metadata
