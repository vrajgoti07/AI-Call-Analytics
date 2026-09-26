"""
AI Call Analytics — Report Repository.

Handles CRUD operations and tenant-scoped retrieval for Report entities.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.models.report import Report, ReportStatus, ReportType


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class ReportRepository:
    """Repository handling database access for generated reports."""

    @staticmethod
    def get_by_id(
        db: Session,
        report_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
    ) -> Report | None:
        """
        Fetch a report by primary key, strictly verifying company ownership if company_id is provided.
        """
        stmt = select(Report).where(Report.id == report_id)
        if company_id is not None:
            stmt = stmt.where(Report.company_id == company_id)
        return db.scalar(stmt)

    @staticmethod
    def create_report(
        db: Session,
        company_id: uuid.UUID,
        title: str,
        report_type: str = ReportType.COMPANY_ANALYTICS.value,
        call_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str = ReportStatus.PENDING.value,
    ) -> Report:
        """Create and persist a new Report entity."""
        report = Report(
            company_id=company_id,
            call_id=call_id,
            user_id=user_id,
            title=title,
            report_type=report_type,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def update_report_completed(
        db: Session,
        report_id: uuid.UUID,
        file_path_pdf: str | None = None,
        file_path_json: str | None = None,
        file_path_csv: str | None = None,
        summary_data: dict[str, Any] | None = None,
    ) -> Report | None:
        """Mark report as completed with paths to generated files."""
        report = db.scalar(select(Report).where(Report.id == report_id))
        if not report:
            return None

        report.status = ReportStatus.COMPLETED.value
        report.file_path_pdf = file_path_pdf
        report.file_path_json = file_path_json
        report.file_path_csv = file_path_csv
        report.summary_data = summary_data
        report.updated_at = utc_now()
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def update_report_failed(
        db: Session,
        report_id: uuid.UUID,
        error_message: str,
    ) -> Report | None:
        """Mark report generation as failed."""
        report = db.scalar(select(Report).where(Report.id == report_id))
        if not report:
            return None

        report.status = ReportStatus.FAILED.value
        report.error_message = error_message
        report.updated_at = utc_now()
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def list_reports(
        db: Session,
        company_id: uuid.UUID,
        call_id: uuid.UUID | None = None,
        report_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Report], int, int]:
        """
        List reports scoped strictly to a company workspace with pagination.
        """
        base_query = select(Report).where(Report.company_id == company_id)

        if call_id is not None:
            base_query = base_query.where(Report.call_id == call_id)
        if report_type:
            base_query = base_query.where(Report.report_type == report_type)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = db.scalar(count_stmt) or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(desc(Report.created_at))
            .offset(offset)
            .limit(page_size)
        )
        reports = list(db.scalars(stmt))
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return reports, total, total_pages

    @staticmethod
    def get_latest_for_call(
        db: Session,
        call_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
    ) -> Report | None:
        """Get latest completed report for a call."""
        stmt = (
            select(Report)
            .where(Report.call_id == call_id)
            .order_by(desc(Report.created_at))
            .limit(1)
        )
        if company_id is not None:
            stmt = stmt.where(Report.company_id == company_id)
        return db.scalar(stmt)
