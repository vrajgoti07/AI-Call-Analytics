"""
AI Call Analytics — Transcript & TranscriptTurn ORM Models.

Persists full transcripts and speaker-attributed turns with start/end boundaries,
sentiment labels, intent predictions, and privacy-masked entity annotations.
"""

from __future__ import annotations

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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.call import Call


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Transcript(Base):
    """
    Call-level transcript metadata and full text.
    """

    __tablename__ = "transcripts"

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
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="whisper")
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="base")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    # Relationships
    call: Mapped[Call] = relationship("Call", back_populates="transcript")
    turns: Mapped[list[TranscriptTurn]] = relationship(
        "TranscriptTurn",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptTurn.sequence_number",
    )

    def __repr__(self) -> str:
        return f"<Transcript(id={self.id}, call_id={self.call_id}, model='{self.model}:{self.model_version}')>"


class TranscriptTurn(Base):
    """
    Speaker-attributed turn with temporal boundaries, sentiment, intent, and NER.
    """

    __tablename__ = "transcript_turns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker_id: Mapped[str] = mapped_column(String(64), nullable=False, default="SPEAKER_00", index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # NLP Enrichments (JSON payloads)
    sentiment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    intent: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    entities: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    alignment_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    transcript: Mapped[Transcript] = relationship("Transcript", back_populates="turns")

    __table_args__ = (
        Index("ix_transcript_turns_transcript_seq", "transcript_id", "sequence_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptTurn(id={self.id}, speaker='{self.speaker_id}', "
            f"start={self.start_time:.1f}, end={self.end_time:.1f})>"
        )
