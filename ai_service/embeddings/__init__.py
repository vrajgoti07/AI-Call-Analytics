"""AI Call Analytics — Semantic Embedding & Vector Search Layer."""

from ai_service.embeddings.chunker import TextChunker
from ai_service.embeddings.config import EmbeddingConfig
from ai_service.embeddings.exceptions import (
    ChunkingError,
    EmbeddingError,
    EmbeddingGenerationError,
    EmbeddingModelLoadError,
    InvalidEmbeddingDimension,
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
from ai_service.embeddings.search import SemanticSearchService

__all__ = [
    "EmbeddingConfig",
    "EmbeddingError",
    "EmbeddingModelLoadError",
    "EmbeddingGenerationError",
    "InvalidEmbeddingDimension",
    "ChunkingError",
    "VectorDatabaseError",
    "PgVectorUnavailable",
    "SearchError",
    "InvalidQuery",
    "TextChunker",
    "TranscriptChunk",
    "EmbeddingItem",
    "SearchResult",
    "SearchQuery",
    "EmbeddingModelManager",
    "SemanticSearchService",
]
