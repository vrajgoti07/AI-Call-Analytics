"""
AI Call Analytics — Semantic Search Pydantic Schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    """Semantic vector search query payload."""

    query: str = Field(..., min_length=2, max_length=500, description="Natural language search query")
    top_k: int = Field(default=10, ge=1, le=50, description="Maximum number of relevant chunks to return")
    similarity_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity cutoff (0.0 to 1.0)",
    )
    call_id: str | None = Field(default=None, description="Optional filter to search within a specific call")


class SearchResultItem(BaseModel):
    """A single matched transcript chunk result."""

    chunk_id: int
    call_id: str
    text: str
    similarity: float
    start_time: float
    end_time: float
    speaker_ids: list[str]


class SemanticSearchResponse(BaseModel):
    """Semantic search response containing matching chunks and score ranking."""

    query: str
    total_results: int
    results: list[SearchResultItem]
