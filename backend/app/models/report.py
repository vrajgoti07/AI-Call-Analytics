"""
AI Call Analytics — Report ORM Model for Multi-Tenant Reports.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.call import Call
    from backend.app.models.company import Company
    from backend.app.models.user import User


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class ReportType(str, enum.Enum):
    """Types of generated reports."""

    INDIVIDUAL_CALL = "INDIVIDUAL_CALL"
    COMPANY_ANALYTICS = "COMPANY_ANALYTICS"
    DATE_RANGE = "DATE_RANGE"


class ReportStatus(str, enum.Enum):
    """Lifecycle status of a generated report."""

    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Report(Base):
    """
    Report entity representing a compiled intelligence report (PDF, JSON, CSV).
    Belongs strictly to a company workspace for multi-tenant isolation.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=ReportType.COMPANY_ANALYTICS.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ReportStatus.PENDING.value,
        index=True,
    )
    date_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Generated file paths (safe server storage)
    file_path_pdf: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_path_json: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_path_csv: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Structured summary metrics
    summary_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    company: Mapped[Company] = relationship("Company")
    call: Mapped[Call | None] = relationship("Call")
    user: Mapped[User | None] = relationship("User")

    __table_args__ = (
        Index("ix_reports_company_created_at", "company_id", "created_at"),
        Index("ix_reports_company_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, title='{self.title}', status='{self.status}')>"
