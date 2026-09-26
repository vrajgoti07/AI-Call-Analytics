"""
AI Call Analytics — Report Pydantic Schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import PaginationMeta


class ReportGenerateRequest(BaseModel):
    """Payload to request asynchronous report generation."""

    report_type: str = Field(
        default="COMPANY_ANALYTICS",
        description="Type of report: 'COMPANY_ANALYTICS', 'INDIVIDUAL_CALL', or 'DATE_RANGE'",
    )
    call_id: uuid.UUID | None = Field(
        default=None,
        description="Specific Call UUID when generating an INDIVIDUAL_CALL report",
    )
    date_from: datetime | None = Field(
        default=None,
        description="Optional start date for date-range analytics",
    )
    date_to: datetime | None = Field(
        default=None,
        description="Optional end date for date-range analytics",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Optional custom title for the generated report",
    )


class ReportResponse(BaseModel):
    """Public representation of a generated report."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    call_id: uuid.UUID | None = None
    title: str
    report_type: str
    status: str
    date_from: datetime | None = None
    date_to: datetime | None = None
    has_pdf: bool = False
    has_json: bool = False
    has_csv: bool = False
    summary_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportListResponse(BaseModel):
    """Paginated list of Report entities."""

    items: list[ReportResponse]
    pagination: PaginationMeta
