"""
AI Call Analytics — Semantic Embedding & Vector Search Exceptions.

Defines a clean, domain-specific exception hierarchy for embedding generation,
model management, chunking, pgvector database integration, and similarity retrieval.
"""

from __future__ import annotations


class EmbeddingError(Exception):
    """Base exception for all semantic embedding and vector retrieval errors."""


class EmbeddingModelLoadError(EmbeddingError):
    """Raised when an embedding transformer model cannot be downloaded or initialized."""


class EmbeddingGenerationError(EmbeddingError):
    """Raised when encoding text into embedding vectors fails during inference."""


class InvalidEmbeddingDimension(EmbeddingError):
    """Raised when an embedding dimension does not match the configured/database dimension."""


class ChunkingError(EmbeddingError):
    """Raised when transcript chunking fails due to invalid turns or configuration."""


class VectorDatabaseError(EmbeddingError):
    """Raised when a database operation (insert, query, transaction) fails."""


class PgVectorUnavailable(VectorDatabaseError):
    """
    Raised when the pgvector extension is not installed or enabled in PostgreSQL.
    Signals that vector database capabilities are unavailable in the current environment.
    """


class SearchError(EmbeddingError):
    """Raised when semantic similarity search execution fails."""


class InvalidQuery(SearchError):
    """Raised when a search query is empty, whitespace-only, or invalid."""
