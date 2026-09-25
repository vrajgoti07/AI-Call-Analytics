"""
AI Call Analytics — Transcript Pydantic Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import PaginationMeta


class TranscriptTurnResponse(BaseModel):
    """A single speaker-attributed dialogue turn."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    speaker_id: str
    start_time: float
    end_time: float
    text: str
    sequence_number: int
    sentiment: dict[str, Any] | None = None
    intent: dict[str, Any] | None = None
    entities: list[dict[str, Any]] | None = None


class TranscriptResponse(BaseModel):
    """Full transcript overview for a call."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: uuid.UUID
    language: str
    text: str
    duration: float | None = None
    model: str
    model_version: str
    created_at: datetime
    turn_count: int = 0


class TranscriptTurnListResponse(BaseModel):
    """Paginated list of speaker turns for a call transcript."""

    call_id: uuid.UUID
    transcript_id: uuid.UUID
    items: list[TranscriptTurnResponse]
    pagination: PaginationMeta
