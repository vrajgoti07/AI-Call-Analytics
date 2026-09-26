"""
AI Call Analytics — Semantic Search API Router.

Endpoints for vector similarity search across conversational transcript chunks,
scoped strictly to the user's company workspace.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SemanticSearchResponse:
    """
    Search conversational transcripts by semantic meaning using text embeddings and pgvector.
    Scoped strictly to the authenticated tenant's call transcripts.
    """
    return SemanticSearchService.search(
        db=db,
        query=payload.query,
        company_id=current_user.company_id,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
        call_id=payload.call_id,
    )
