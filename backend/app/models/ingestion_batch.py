"""
AI Call Analytics — IngestionBatch ORM Model.

Represents a logical batch/folder for each ZIP upload, ensuring every ZIP
remains an independent dataset scoped to a company workspace.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.call import Call
    from backend.app.models.company import Company


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class BatchStatus(str, enum.Enum):
    """Lifecycle states of an ingestion batch."""

    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class BatchUploadType(str, enum.Enum):
    """Type of ingestion upload."""

    ZIP = "ZIP"
    SINGLE_AUDIO = "SINGLE_AUDIO"


class IngestionBatch(Base):
    """
    Represents a single ZIP upload or bulk ingestion event.
    Every ZIP upload creates exactly ONE IngestionBatch.
    All calls extracted from that ZIP are linked via batch_id.
    """

    __tablename__ = "ingestion_batches"

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
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    upload_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=BatchUploadType.ZIP.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=BatchStatus.UPLOADING.value,
        index=True,
    )
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    archive_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    company: Mapped[Company] = relationship("Company")
    calls: Mapped[list[Call]] = relationship(
        "Call",
        back_populates="batch",
        order_by="desc(Call.created_at)",
    )

    __table_args__ = (
        Index("ix_ingestion_batches_company_created_at", "company_id", "created_at"),
        Index("ix_ingestion_batches_company_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<IngestionBatch(id={self.id}, filename='{self.original_filename}', status='{self.status}')>"
