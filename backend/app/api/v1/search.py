"""
AI Call Analytics — Semantic Search API Router.

Endpoints for vector similarity search across conversational transcript chunks.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from backend.app.services.search_service import SemanticSearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    summary="Semantic vector search across call transcript chunks",
)
def semantic_search(
    payload: SemanticSearchRequest,
    db: Session = Depends(get_db),
) -> SemanticSearchResponse:
    """
    Search conversational transcripts by semantic meaning using text embeddings and pgvector.
    Supports top-k ranking, cosine thresholding, and optional call_id filtering.
    """
    return SemanticSearchService.search(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
        call_id=payload.call_id,
    )
