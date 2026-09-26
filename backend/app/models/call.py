"""
AI Call Analytics — Core Call, AudioFile, and ProcessingJob ORM Models.

Provides aggregate root entity Call, associated AudioFile metadata, and
asynchronous ProcessingJob state tracking.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.company import Company
    from backend.app.models.ingestion_batch import IngestionBatch
    from backend.app.models.transcript import Transcript


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class CallStatus(str, enum.Enum):
    """Lifecycle states of a call record."""

    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class JobStatus(str, enum.Enum):
    """Lifecycle states of an asynchronous processing job."""

    PENDING = "PENDING"
    STARTED = "STARTED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"


class JobType(str, enum.Enum):
    """Types of asynchronous analysis jobs."""

    FULL_CALL_ANALYSIS = "FULL_CALL_ANALYSIS"
    PREPROCESS_AUDIO = "PREPROCESS_AUDIO"
    TRANSCRIBE = "TRANSCRIBE"
    DIARIZE = "DIARIZE"
    ANALYZE_NLP = "ANALYZE_NLP"
    GENERATE_EMBEDDINGS = "GENERATE_EMBEDDINGS"
    DISCOVER_THEMES = "DISCOVER_THEMES"
    CALCULATE_RISK = "CALCULATE_RISK"


class Call(Base):
    """
    Central aggregate root entity representing a customer support call recording.
    """

    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CallStatus.UPLOADED.value,
        index=True,
    )
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True, default="en")

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
    company: Mapped[Company | None] = relationship("Company", back_populates="calls")
    batch: Mapped[IngestionBatch | None] = relationship("IngestionBatch", back_populates="calls")
    audio_file: Mapped[AudioFile | None] = relationship(
        "AudioFile",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan",
    )
    transcript: Mapped[Transcript | None] = relationship(
        "Transcript",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan",
    )
    jobs: Mapped[list[ProcessingJob]] = relationship(
        "ProcessingJob",
        back_populates="call",
        cascade="all, delete-orphan",
        order_by="desc(ProcessingJob.created_at)",
    )

    __table_args__ = (
        Index("ix_calls_status_created_at", "status", "created_at"),
        Index("ix_calls_company_created_at", "company_id", "created_at"),
        Index("ix_calls_company_status", "company_id", "status"),
        Index("ix_calls_company_batch", "company_id", "batch_id"),
    )

    @property
    def batch_name(self) -> str | None:
        """Display name of the parent ingestion batch."""
        return self.batch.display_name if self.batch else None

    @property
    def batch_filename(self) -> str | None:
        """Original filename of the parent ingestion batch."""
        return self.batch.original_filename if self.batch else None

    def __repr__(self) -> str:
        return f"<Call(id={self.id}, status='{self.status}', duration={self.duration})>"


class AudioFile(Base):
    """
    Audio file metadata entity referencing local or object storage locations.
    """

    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="audio/wav")
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=16000)
    channels: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    audio_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    call: Mapped[Call] = relationship("Call", back_populates="audio_file")

    def __repr__(self) -> str:
        return f"<AudioFile(id={self.id}, filename='{self.filename}', size={self.size})>"


class ProcessingJob(Base):
    """
    State tracking for asynchronous processing pipeline jobs.
    """

    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=JobType.FULL_CALL_ANALYSIS.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStatus.PENDING.value,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stages: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    call: Mapped[Call] = relationship("Call", back_populates="jobs")

    __table_args__ = (
        Index("ix_processing_jobs_call_status", "call_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, call_id={self.call_id}, status='{self.status}', progress={self.progress})>"
