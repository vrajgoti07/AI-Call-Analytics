"""
AI Call Analytics — Semantic Embedding & Search Schemas.

Defines strongly typed dataclasses representing conversational transcript chunks,
computed vector embeddings, search queries, and structured retrieval results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TranscriptChunk:
    """
    Searchable conversational text chunk derived from grouped speaker turns (Step 8, 10).
    Preserves speaker attribution, chronological timestamps, and source turn IDs.
    """

    chunk_id: int
    call_id: str
    speaker_ids: list[str]
    turn_ids: list[int]
    start: float
    end: float
    text: str
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Chunk duration in seconds."""
        return round(max(0.0, self.end - self.start), 3)

    def to_dict(self) -> dict[str, Any]:
        """Serialize chunk to JSON-compatible dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "call_id": self.call_id,
            "speaker_ids": list(self.speaker_ids),
            "turn_ids": list(self.turn_ids),
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": self.duration,
            "text": self.text,
            "token_count": self.token_count,
            "metadata": dict(self.metadata),
        }


@dataclass
class EmbeddingItem:
    """A computed high-dimensional vector paired with its source transcript chunk."""

    chunk: TranscriptChunk
    embedding: list[float]
    model_name: str
    dimension: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize embedding item to dictionary (omitting large vector unless explicit)."""
        return {
            "chunk": self.chunk.to_dict(),
            "model_name": self.model_name,
            "dimension": self.dimension,
            "vector_sample": [round(v, 4) for v in self.embedding[:5]],
        }


@dataclass(frozen=True)
class SearchResult:
    """
    Structured Semantic Retrieval Result (Step 22).
    Represents a relevant call segment matching an embedding similarity query.
    """

    chunk_id: int
    call_id: str
    text: str
    speaker_ids: list[str]
    turn_ids: list[int]
    start: float
    end: float
    similarity_score: float  # Cosine similarity in [0.0, 1.0]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize search result to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "call_id": self.call_id,
            "text": self.text,
            "speaker_ids": list(self.speaker_ids),
            "turn_ids": list(self.turn_ids),
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "similarity_score": round(self.similarity_score, 4),
            "metadata": dict(self.metadata),
        }


@dataclass
class SearchQuery:
    """Input parameters for semantic similarity search with optional filtering."""

    query: str
    top_k: int = 5
    similarity_threshold: float | None = None
    filters: dict[str, Any] = field(default_factory=dict)
