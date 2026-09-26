"""
AI Call Analytics — Transcript API Router.

Endpoints for retrieving full call transcripts and paginated speaker turns,
scoped strictly to the user's company workspace.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import AppException, CallNotFoundError
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.repositories.call_repository import CallRepository
from backend.app.repositories.transcript_repository import TranscriptRepository
from backend.app.schemas.common import PaginationMeta
from backend.app.schemas.transcript import (
    TranscriptResponse,
    TranscriptTurnListResponse,
    TranscriptTurnResponse,
)

router = APIRouter(prefix="/calls", tags=["transcripts"])


@router.get(
    "/{call_id}/transcript",
    response_model=TranscriptResponse,
    summary="Retrieve call transcript overview",
)
def get_transcript(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TranscriptResponse:
    """Retrieve full transcript overview and model provenance for a call."""
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    transcript = TranscriptRepository.get_by_call_id(db, call_id)
    if not transcript:
        raise AppException(
            code="TRANSCRIPT_NOT_FOUND",
            message=f"No transcript found for call '{call_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return TranscriptResponse(
        id=transcript.id,
        call_id=transcript.call_id,
        language=transcript.language,
        text=transcript.text,
        duration=transcript.duration,
        model=transcript.model,
        model_version=transcript.model_version,
        created_at=transcript.created_at,
        turn_count=len(transcript.turns),
    )


@router.get(
    "/{call_id}/transcript/turns",
    response_model=TranscriptTurnListResponse,
    summary="Retrieve paginated speaker turns with NLP enrichments",
)
def get_transcript_turns(
    call_id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=50, ge=1, le=100, description="Turns per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TranscriptTurnListResponse:
    """Retrieve paginated speaker turns including sentiment, intent, and entities."""
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    transcript = TranscriptRepository.get_by_call_id(db, call_id)
    if not transcript:
        raise AppException(
            code="TRANSCRIPT_NOT_FOUND",
            message=f"No transcript found for call '{call_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    turns, total, total_pages = TranscriptRepository.list_turns(
        db=db,
        transcript_id=transcript.id,
        page=page,
        page_size=page_size,
    )

    return TranscriptTurnListResponse(
        call_id=call_id,
        transcript_id=transcript.id,
        items=[TranscriptTurnResponse.model_validate(t) for t in turns],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )
