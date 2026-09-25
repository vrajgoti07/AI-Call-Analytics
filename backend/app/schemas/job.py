"""
AI Call Analytics — Background Processing Job Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import PaginationMeta


class JobResponse(BaseModel):
    """Status details of an asynchronous processing job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: uuid.UUID
    task_id: str | None = None
    job_type: str
    status: str
    progress: int
    current_stage: str | None = None
    stages: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class JobListResponse(BaseModel):
    """Paginated list of processing jobs."""

    items: list[JobResponse]
    pagination: PaginationMeta
