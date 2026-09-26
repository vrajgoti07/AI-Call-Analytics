"""
AI Call Analytics — Call & AudioFile Pydantic Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import PaginationMeta


class AudioFileResponse(BaseModel):
    """Metadata response for an uploaded audio recording."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: uuid.UUID
    filename: str
    size: int
    duration: float | None = None
    sample_rate: int
    channels: int
    mime_type: str
    created_at: datetime


class CallCreate(BaseModel):
    """Payload to create a new call record before/during upload."""

    external_id: str | None = Field(default=None, max_length=128, description="External reference ID (CRM/telephony)")
    language: str | None = Field(default="en", max_length=16, description="Spoken language code (e.g. en, es)")


class CallResponse(BaseModel):
    """Public representation of a Call entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None = None
    external_id: str | None = None
    status: str
    duration: float | None = None
    language: str | None = "en"
    created_at: datetime
    updated_at: datetime
    audio_file: AudioFileResponse | None = None


class CallDetailResponse(CallResponse):
    """Detailed call representation with summary flags and latest job ID."""

    has_transcript: bool = False
    has_risk_analysis: bool = False
    latest_job_id: uuid.UUID | None = None


class CallListResponse(BaseModel):
    """Paginated list of Call entities."""

    items: list[CallResponse]
    pagination: PaginationMeta


class SkippedFileInfo(BaseModel):
    """Information regarding a file within a ZIP archive that was not processed."""

    filename: str
    reason: str


class BulkIngestResponse(BaseModel):
    """Result summary of a bulk ZIP or multi-file call upload."""

    total_files: int
    processed_count: int
    skipped_count: int = 0
    created_calls: list[CallResponse]
    skipped_files: list[SkippedFileInfo]
