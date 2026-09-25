"""
AI Call Analytics — Processing Jobs API Router.

Endpoints for checking background task execution states and histories.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.exceptions import JobNotFoundError
from backend.app.database.session import get_db
from backend.app.repositories.job_repository import JobRepository
from backend.app.schemas.common import PaginationMeta
from backend.app.schemas.job import JobListResponse, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Retrieve processing job status and progress",
)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Retrieve execution state, current stage, and progress percentage for a background job."""
    job = JobRepository.get_by_id(db, job_id)
    if not job:
        raise JobNotFoundError(job_id)
    return JobResponse.model_validate(job)


@router.get(
    "",
    response_model=JobListResponse,
    summary="List background processing jobs with pagination",
)
def list_jobs(
    call_id: uuid.UUID | None = Query(default=None, description="Filter jobs by call ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """List historical and active processing jobs."""
    jobs, total, total_pages = JobRepository.list_jobs(
        db=db,
        call_id=call_id,
        page=page,
        page_size=page_size,
    )
    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )
