"""
AI Call Analytics — Batches API Router (v1).

Enforces company multi-tenant isolation on all ingestion batch operations.
Enables ZIP-wise batch management, filtering, re-analysis, and batch reporting.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import AppException
from backend.app.database.session import get_db
from backend.app.models.call import CallStatus
from backend.app.models.report import ReportType
from backend.app.models.user import User
from backend.app.repositories.batch_repository import BatchRepository
from backend.app.repositories.call_repository import CallRepository
from backend.app.repositories.report_repository import ReportRepository
from backend.app.schemas.batch import BatchDetailResponse, BatchListResponse, BatchResponse
from backend.app.schemas.call import CallListResponse, CallResponse
from backend.app.schemas.common import PaginationMeta
from backend.app.schemas.report import ReportGenerateRequest, ReportListResponse, ReportResponse
from backend.app.services.call_service import CallService
from backend.app.services.report_service import ReportService

logger = logging.getLogger("backend.app.api.v1.batches")

router = APIRouter(prefix="/batches", tags=["Ingestion Batches"])


@router.get(
    "",
    response_model=BatchListResponse,
    summary="List all ZIP ingestion batches for current workspace",
)
def list_batches(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (e.g. PROCESSING, COMPLETED)"),
    search: str | None = Query(default=None, description="Search by filename or display name"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchListResponse:
    """List all ingestion batches scoped strictly to the authenticated user's workspace."""
    batches, total, total_pages = BatchRepository.list_batches(
        db=db,
        company_id=current_user.company_id,
        status=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )
    return BatchListResponse(
        items=[BatchResponse.model_validate(b) for b in batches],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/{batch_id}",
    response_model=BatchDetailResponse,
    summary="Retrieve batch details by ID",
)
def get_batch(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchDetailResponse:
    """Get single batch metadata and processing progress."""
    batch = BatchRepository.get_by_id(db, batch_id, company_id=current_user.company_id)
    if not batch:
        raise AppException("BATCH_NOT_FOUND", f"Batch {batch_id} not found.", 404)

    # Compute additional stats
    calls, total_calls, _ = CallRepository.list_calls(
        db=db,
        company_id=current_user.company_id,
        batch_id=batch_id,
        page=1,
        page_size=1000,
    )
    durations = [c.duration for c in calls if c.duration]
    avg_dur = sum(durations) / len(durations) if durations else 0.0

    resp = BatchDetailResponse.model_validate(batch)
    resp.average_duration = round(avg_dur, 1)
    return resp


@router.get(
    "/{batch_id}/calls",
    response_model=CallListResponse,
    summary="List all calls belonging to a specific batch",
)
def list_batch_calls(
    batch_id: uuid.UUID,
    status_filter: str | None = Query(default=None, alias="status", description="Filter by call status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CallListResponse:
    """Retrieve calls extracted from this specific batch archive."""
    batch = BatchRepository.get_by_id(db, batch_id, company_id=current_user.company_id)
    if not batch:
        raise AppException("BATCH_NOT_FOUND", f"Batch {batch_id} not found.", 404)

    calls, total, total_pages = CallRepository.list_calls(
        db=db,
        company_id=current_user.company_id,
        batch_id=batch_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return CallListResponse(
        items=[CallResponse.model_validate(c) for c in calls],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.post(
    "/{batch_id}/analyze",
    summary="Trigger analysis for unanalyzed calls in this batch",
)
def analyze_batch(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Queue AI pipeline tasks for all unanalyzed or failed calls in this batch."""
    batch = BatchRepository.get_by_id(db, batch_id, company_id=current_user.company_id)
    if not batch:
        raise AppException("BATCH_NOT_FOUND", f"Batch {batch_id} not found.", 404)

    calls, _, _ = CallRepository.list_calls(
        db=db,
        company_id=current_user.company_id,
        batch_id=batch_id,
        page=1,
        page_size=1000,
    )

    queued_count = 0
    for call in calls:
        if call.status in (CallStatus.UPLOADED.value, CallStatus.FAILED.value):
            try:
                CallService.start_call_analysis(db=db, call_id=call.id)
                queued_count += 1
            except Exception as exc:
                logger.warning("Failed to start analysis for call %s: %s", call.id, exc)

    db.commit()
    return {
        "batch_id": str(batch.id),
        "total_calls": len(calls),
        "queued_calls": queued_count,
        "message": f"Successfully queued {queued_count} calls for processing.",
    }


@router.post(
    "/{batch_id}/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate analytics report for this batch",
)
def generate_batch_report(
    batch_id: uuid.UUID,
    req: ReportGenerateRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Generate a batch-scoped PDF/JSON/CSV report."""
    batch = BatchRepository.get_by_id(db, batch_id, company_id=current_user.company_id)
    if not batch:
        raise AppException("BATCH_NOT_FOUND", f"Batch {batch_id} not found.", 404)

    if req is None:
        req = ReportGenerateRequest(
            report_type=ReportType.BATCH_ANALYTICS.value,
            batch_id=batch_id,
            title=f"Batch Report — {batch.display_name}",
        )
    else:
        req.report_type = ReportType.BATCH_ANALYTICS.value
        req.batch_id = batch_id
        if not req.title:
            req.title = f"Batch Report — {batch.display_name}"

    report = ReportService.generate_report(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.id,
        req=req,
    )
    return ReportResponse.model_validate(report)


@router.get(
    "/{batch_id}/reports",
    response_model=ReportListResponse,
    summary="List generated reports for this batch",
)
def list_batch_reports(
    batch_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """List reports specifically generated for this batch."""
    batch = BatchRepository.get_by_id(db, batch_id, company_id=current_user.company_id)
    if not batch:
        raise AppException("BATCH_NOT_FOUND", f"Batch {batch_id} not found.", 404)

    reports, total, total_pages = ReportRepository.list_reports(
        db=db,
        company_id=current_user.company_id,
        batch_id=batch_id,
        page=page,
        page_size=page_size,
    )
    return ReportListResponse(
        items=[ReportResponse.model_validate(r) for r in reports],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )
