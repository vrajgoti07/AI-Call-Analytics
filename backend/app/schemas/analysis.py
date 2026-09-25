"""
AI Call Analytics — Analysis Status and Summary Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class StartAnalysisRequest(BaseModel):
    """Request payload to initiate asynchronous call analysis."""

    pipeline_stages: list[str] | None = Field(
        default=None,
        description="Optional subset of stages to execute (default: all pipeline stages)",
    )
    force_reprocess: bool = Field(
        default=False,
        description="Whether to overwrite existing transcript, embeddings, and risk results",
    )


class AnalysisStatusResponse(BaseModel):
    """Granular stage-level execution status of call analysis."""

    call_id: uuid.UUID
    status: str
    progress: int = Field(..., ge=0, le=100, description="Overall completion percentage")
    current_stage: str | None = None
    stages: dict[str, str] = Field(
        default_factory=dict,
        description="Status per pipeline stage (e.g. preprocessing, transcription, diarization, nlp, embeddings, themes, risk)",
    )
    job_id: uuid.UUID | None = None
    error_code: str | None = None
    error_message: str | None = None


class AnalysisSummaryResponse(BaseModel):
    """Consolidated overview of all analytics for a given call."""

    call_id: uuid.UUID
    status: str
    duration: float | None = None
    transcript_summary: str | None = None
    speaker_count: int = 0
    dominant_sentiment: str | None = None
    primary_intent: str | None = None
    risk_level: str | None = None
    risk_score: float | None = None
    theme_count: int = 0
    themes: list[str] = Field(default_factory=list)
    created_at: datetime
