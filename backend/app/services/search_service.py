"""
AI Call Analytics — Semantic Search Application Service.

Bridges FastAPI endpoint with Phase 6 embedding search.
"""

from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.orm import Session

from backend.app.schemas.search import SearchResultItem, SemanticSearchResponse

logger = logging.getLogger("backend.app.services.search_service")


class SemanticSearchService:
    """Service handling semantic similarity search over call transcripts."""

    @staticmethod
    def search(
        db: Session,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        call_id: str | None = None,
    ) -> SemanticSearchResponse:
        """
        Execute semantic vector search.
        Uses Phase 6 SemanticSearchService with pgvector or in-memory fallback.
        """
        results: list[SearchResultItem] = []

        try:
            from ai_service.embeddings import SemanticSearchService as CoreSearchService

            core_search = CoreSearchService()
            filters = {}
            if call_id:
                filters["call_id"] = call_id

            search_results = core_search.search(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
                session=db,
            )

            for r in search_results:
                results.append(
                    SearchResultItem(
                        chunk_id=r.chunk_id,
                        call_id=r.call_id,
                        text=r.text,
                        similarity=round(r.similarity_score, 4),
                        start_time=r.start,
                        end_time=r.end,
                        speaker_ids=list(r.speaker_ids),
                    )
                )

        except Exception as e:
            logger.warning("Semantic search service error: %s", e)

        return SemanticSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
        )
