"""
AI Call Analytics — Semantic Embedding Configuration.

Defines centralized, validated configuration for model management, chunking parameters,
and pgvector retrieval settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmbeddingConfig:
    """Configuration settings for semantic text embeddings and vector retrieval."""

    # Model settings
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    device: str = "cpu"
    batch_size: int = 32
    normalize_embeddings: bool = True

    # Vector search & pgvector settings
    distance_metric: str = "cosine"  # 'cosine', 'l2', 'inner_product'
    top_k: int = 5
    max_top_k: int = 50
    similarity_threshold: float | None = 0.30

    # Chunking strategy parameters
    max_chunk_tokens: int = 200  # Target maximum tokens per chunk (~800 characters)
    chunk_overlap_turns: int = 1  # Number of overlapping turns between consecutive chunks

    @classmethod
    def from_env(cls) -> EmbeddingConfig:
        """Construct EmbeddingConfig loaded from environment variables with defaults."""
        raw_dim = os.getenv("EMBEDDING_DIMENSION", "384")
        raw_batch = os.getenv("EMBEDDING_BATCH_SIZE", "32")
        raw_top_k = os.getenv("VECTOR_TOP_K", "5")
        raw_thresh = os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.30")

        return cls(
            model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip(),
            dimension=int(raw_dim) if raw_dim.isdigit() else 384,
            device=os.getenv("EMBEDDING_DEVICE", os.getenv("DEVICE", "cpu")).strip().lower(),
            batch_size=int(raw_batch) if raw_batch.isdigit() else 32,
            distance_metric=os.getenv("VECTOR_DISTANCE_METRIC", "cosine").strip().lower(),
            top_k=int(raw_top_k) if raw_top_k.isdigit() else 5,
            similarity_threshold=float(raw_thresh) if raw_thresh and raw_thresh.lower() != "none" else None,
        )
