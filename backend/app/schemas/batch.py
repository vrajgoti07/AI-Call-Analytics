"""
AI Call Analytics — Ingestion Batch Pydantic Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import PaginationMeta


class BatchResponse(BaseModel):
    """Public representation of an IngestionBatch entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    original_filename: str
    display_name: str
    upload_type: str
    status: str
    total_files: int = 0
    processed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    archive_size: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    # Computed fields populated from service layer
    call_count: int | None = None
    report_id: uuid.UUID | None = None
    report_status: str | None = None


class BatchDetailResponse(BatchResponse):
    """Detailed batch representation with call summary statistics."""

    total_duration: float | None = None
    average_duration: float | None = None


class BatchListResponse(BaseModel):
    """Paginated list of IngestionBatch entities."""

    items: list[BatchResponse]
    pagination: PaginationMeta


class BatchListParams(BaseModel):
    """Query parameters for listing batches."""

    status: str | None = None
    page: int = 1
    page_size: int = 20
