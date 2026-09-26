"""
AI Call Analytics — Reports API Router.

Endpoints for requesting report generation, tracking status, listing reports,
and securely downloading report artifacts (PDF, JSON, CSV), strictly scoped to
the authenticated user's active company workspace.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import AppException, ForbiddenError
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.repositories.report_repository import ReportRepository
from backend.app.schemas.common import PaginationMeta
from backend.app.schemas.report import (
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
)
from backend.app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


def _to_report_response(r) -> ReportResponse:
    """Helper to convert Report entity to ReportResponse with file existence flags."""
    return ReportResponse(
        id=r.id,
        company_id=r.company_id,
        call_id=r.call_id,
        title=r.title,
        report_type=r.report_type,
        status=r.status,
        date_from=r.date_from,
        date_to=r.date_to,
        has_pdf=bool(r.file_path_pdf and Path(r.file_path_pdf).exists()),
        has_json=bool(r.file_path_json and Path(r.file_path_json).exists()),
        has_csv=bool(r.file_path_csv and Path(r.file_path_csv).exists()),
        summary_data=r.summary_data,
        error_message=r.error_message,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.post(
    "/reports/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an intelligence report for a call or company workspace",
)
def generate_report(
    payload: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """
    Generate an individual call report or company-level executive summary report.
    Builds PDF, JSON, and CSV downloads, saving them into company-isolated storage.
    """
    report = ReportService.generate_report(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.id,
        req=payload,
    )
    return _to_report_response(report)


@router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    summary="Retrieve report metadata and generation status",
)
def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Retrieve details and status for a specific report in user's company."""
    report = ReportRepository.get_by_id(db, report_id, company_id=current_user.company_id)
    if not report:
        raise AppException(
            code="REPORT_NOT_FOUND",
            message=f"Report '{report_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _to_report_response(report)


@router.get(
    "/reports/{report_id}/download",
    summary="Securely download report artifact file (PDF, JSON, or CSV)",
)
def download_report(
    report_id: uuid.UUID,
    format: str = Query(default="pdf", description="Artifact format: 'pdf', 'json', or 'csv'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Secure download endpoint with strict multi-tenant boundary verification:
    1. Authenticates user token
    2. Validates company ownership (cross-company access strictly forbidden)
    3. Verifies file existence on disk
    4. Sets safe Content-Disposition and Content-Type headers
    """
    file_path, content_type, filename = ReportService.get_report_download_artifact(
        db=db,
        report_id=report_id,
        company_id=current_user.company_id,
        file_format=format,
    )

    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@router.get(
    "/reports",
    response_model=ReportListResponse,
    summary="List generated reports for active company workspace",
)
def list_reports(
    call_id: uuid.UUID | None = Query(default=None, description="Optional filter by Call ID"),
    report_type: str | None = Query(default=None, description="Filter by report type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """List reports strictly scoped to the active workspace."""
    reports, total, total_pages = ReportRepository.list_reports(
        db=db,
        company_id=current_user.company_id,
        call_id=call_id,
        report_type=report_type,
        page=page,
        page_size=page_size,
    )
    return ReportListResponse(
        items=[_to_report_response(r) for r in reports],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/companies/{company_id}/reports",
    response_model=ReportListResponse,
    summary="List reports for a specific company workspace",
)
def list_company_reports(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """
    List reports for a company. Non-admins can only access their own company.
    """
    if current_user.company_id != company_id and current_user.role != UserRole.ADMIN.value:
        raise ForbiddenError("You are not authorized to view reports for this company.")

    reports, total, total_pages = ReportRepository.list_reports(
        db=db,
        company_id=company_id,
        page=page,
        page_size=page_size,
    )
    return ReportListResponse(
        items=[_to_report_response(r) for r in reports],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/calls/{call_id}/report",
    response_model=ReportResponse,
    summary="Retrieve or get latest report for a specific call",
)
def get_call_report(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Get the latest completed report for a call in the user's workspace."""
    call = db.scalar(
        select(Call).where(Call.id == call_id, Call.company_id == current_user.company_id)
    )
    if not call:
        raise AppException(
            code="CALL_NOT_FOUND",
            message=f"Call '{call_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    report = ReportRepository.get_latest_for_call(
        db=db,
        call_id=call_id,
        company_id=current_user.company_id,
    )
    if not report:
        raise AppException(
            code="REPORT_NOT_FOUND",
            message=f"No report has been generated yet for call '{call_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return _to_report_response(report)
