"""
AI Call Analytics — Analysis API Router.

Endpoints for triggering pipeline execution, tracking stage progress, and retrieving
consolidated call analytics summaries, scoped strictly to the user's company workspace.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import AppException, CallNotFoundError
from backend.app.database.session import get_db
from backend.app.models.call import CallStatus
from backend.app.models.escalation import EscalationRisk
from backend.app.models.user import User
from backend.app.repositories.call_repository import CallRepository
from backend.app.repositories.job_repository import JobRepository
from backend.app.repositories.transcript_repository import TranscriptRepository
from backend.app.schemas.analysis import (
    AnalysisStatusResponse,
    AnalysisSummaryResponse,
    StartAnalysisRequest,
)
from backend.app.services.call_service import CallService

router = APIRouter(prefix="/calls", tags=["analysis"])


@router.post(
    "/{call_id}/analyze",
    response_model=AnalysisStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous AI analysis pipeline for a call",
)
def start_analysis(
    call_id: uuid.UUID,
    payload: StartAnalysisRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisStatusResponse:
    """
    Initiate background analysis pipeline across all AI components:
    Audio Preprocessing -> ASR -> Diarization -> NLP -> Embeddings -> Themes -> Risk.
    Returns HTTP 202 Accepted with the tracking Job ID.
    """
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    force_reprocess = payload.force_reprocess if payload else False
    job_id = CallService.start_call_analysis(
        db=db,
        call_id=call_id,
        force_reprocess=force_reprocess,
    )

    job = JobRepository.get_by_id(db, job_id)
    return AnalysisStatusResponse(
        call_id=call_id,
        status=job.status if job else CallStatus.QUEUED.value,
        progress=job.progress if job else 0,
        current_stage=job.current_stage if job else None,
        stages=job.stages if job else {},
        job_id=job_id,
    )


@router.get(
    "/{call_id}/analysis/status",
    response_model=AnalysisStatusResponse,
    summary="Track granular stage-level progress of call analysis",
)
def get_analysis_status(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisStatusResponse:
    """Check the real-time stage progress (0–100%) and error state of a call."""
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    job = JobRepository.get_latest_for_call(db, call_id)
    if not job:
        return AnalysisStatusResponse(
            call_id=call_id,
            status=call.status,
            progress=100 if call.status == CallStatus.COMPLETED.value else 0,
            stages={},
            job_id=None,
        )

    return AnalysisStatusResponse(
        call_id=call_id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        stages=job.stages,
        job_id=job.id,
        error_code=job.error_code,
        error_message=job.error_message,
    )


@router.get(
    "/{call_id}/analysis",
    response_model=AnalysisSummaryResponse,
    summary="Retrieve consolidated analytics summary for a call",
)
def get_analysis_summary(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisSummaryResponse:
    """Consolidated summary combining transcript, NLP metrics, themes, and risk."""
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    transcript = TranscriptRepository.get_by_call_id(db, call_id)

    # Speakers & NLP aggregations
    speakers: set[str] = set()
    sentiment_counts: dict[str, int] = {}
    intent_counts: dict[str, int] = {}

    if transcript and transcript.turns:
        for t in transcript.turns:
            speakers.add(t.speaker_id)
            if t.sentiment and isinstance(t.sentiment, dict):
                label = t.sentiment.get("label")
                if label:
                    sentiment_counts[label] = sentiment_counts.get(label, 0) + 1
            if t.intent and isinstance(t.intent, dict):
                intent = t.intent.get("intent")
                if intent:
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1

    dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else None
    primary_intent = max(intent_counts, key=intent_counts.get) if intent_counts else None

    # Fetch latest escalation risk
    risk_stmt = (
        select(EscalationRisk)
        .where(EscalationRisk.call_id == str(call_id))
        .order_by(EscalationRisk.created_at.desc())
        .limit(1)
    )
    risk_record = db.scalar(risk_stmt)

    return AnalysisSummaryResponse(
        call_id=call.id,
        status=call.status,
        duration=call.duration,
        transcript_summary=transcript.text[:200] + "..." if transcript and transcript.text and len(transcript.text) > 200 else (transcript.text if transcript else None),
        speaker_count=len(speakers),
        dominant_sentiment=dominant_sentiment,
        primary_intent=primary_intent,
        risk_level=risk_record.risk_level if risk_record else None,
        risk_score=risk_record.risk_score if risk_record else None,
        theme_count=0,
        themes=[],
        created_at=call.created_at,
    )
