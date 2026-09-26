"""
AI Call Analytics — Semantic Search Application Service.

Bridges FastAPI endpoint with Phase 6 embedding search, with strict company tenant isolation.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.call import Call
from backend.app.schemas.search import SearchResultItem, SemanticSearchResponse

logger = logging.getLogger("backend.app.services.search_service")


class SemanticSearchService:
    """Service handling semantic similarity search over call transcripts with tenant boundary."""

    @staticmethod
    def search(
        db: Session,
        query: str,
        company_id: uuid.UUID | None = None,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        call_id: str | None = None,
    ) -> SemanticSearchResponse:
        """
        Execute semantic vector search.
        Restricted to calls belonging to the specified company_id.
        """
        results: list[SearchResultItem] = []

        # Find allowed call IDs for this tenant
        allowed_call_ids: set[str] | None = None
        if company_id is not None:
            stmt = select(Call.id).where(Call.company_id == company_id)
            if call_id:
                stmt = stmt.where(Call.id == uuid.UUID(call_id))
            ids = db.scalars(stmt).all()
            allowed_call_ids = {str(cid) for cid in ids}
            if not allowed_call_ids:
                return SemanticSearchResponse(
                    query=query,
                    total_results=0,
                    results=[],
                )

        try:
            from ai_service.embeddings import SemanticSearchService as CoreSearchService

            core_search = CoreSearchService()
            filters = {}
            if call_id:
                filters["call_id"] = call_id

            search_results = core_search.search(
                query=query,
                top_k=top_k * 2 if allowed_call_ids else top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
                session=db,
            )

            for r in search_results:
                r_call_id_str = str(r.call_id)
                if allowed_call_ids is not None and r_call_id_str not in allowed_call_ids:
                    continue

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
                if len(results) >= top_k:
                    break

        except Exception as e:
            logger.warning("Semantic search service error: %s", e)

        return SemanticSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
        )
