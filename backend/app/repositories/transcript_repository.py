"""
AI Call Analytics — Transcript Repository.

Handles relational database queries and transactions for Transcripts and TranscriptTurns.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models.transcript import Transcript, TranscriptTurn


class TranscriptRepository:
    """Repository handling CRUD operations for transcripts and speaker turns."""

    @staticmethod
    def get_by_call_id(db: Session, call_id: uuid.UUID) -> Transcript | None:
        """Fetch transcript associated with a call ID."""
        stmt = (
            select(Transcript)
            .options(joinedload(Transcript.turns))
            .where(Transcript.call_id == call_id)
        )
        return db.scalar(stmt)

    @staticmethod
    def get_by_id(db: Session, transcript_id: uuid.UUID) -> Transcript | None:
        """Fetch transcript by primary key."""
        stmt = select(Transcript).where(Transcript.id == transcript_id)
        return db.scalar(stmt)

    @staticmethod
    def list_turns(
        db: Session,
        transcript_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[TranscriptTurn], int, int]:
        """
        List turns for a transcript with pagination.

        Returns:
            Tuple of (turns_list, total_count, total_pages)
        """
        count_stmt = (
            select(func.count())
            .select_from(TranscriptTurn)
            .where(TranscriptTurn.transcript_id == transcript_id)
        )
        total = db.scalar(count_stmt) or 0

        offset = (page - 1) * page_size
        stmt = (
            select(TranscriptTurn)
            .where(TranscriptTurn.transcript_id == transcript_id)
            .order_by(TranscriptTurn.sequence_number.asc())
            .offset(offset)
            .limit(page_size)
        )
        turns = list(db.scalars(stmt))
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return turns, total, total_pages

    @staticmethod
    def save_transcript_and_turns(
        db: Session,
        call_id: uuid.UUID,
        text: str,
        language: str = "en",
        duration: float | None = None,
        model: str = "whisper",
        model_version: str = "base",
        turns_data: list[dict[str, Any]] | None = None,
    ) -> Transcript:
        """
        Idempotently save or update transcript and replace turns.
        """
        transcript = TranscriptRepository.get_by_call_id(db, call_id)

        if transcript:
            transcript.text = text
            transcript.language = language
            transcript.duration = duration
            transcript.model = model
            transcript.model_version = model_version
            # Clear existing turns to ensure idempotency
            transcript.turns.clear()
            db.flush()
        else:
            transcript = Transcript(
                call_id=call_id,
                text=text,
                language=language,
                duration=duration,
                model=model,
                model_version=model_version,
            )
            db.add(transcript)
            db.flush()

        if turns_data:
            for idx, turn in enumerate(turns_data):
                turn_obj = TranscriptTurn(
                    transcript_id=transcript.id,
                    speaker_id=turn.get("speaker_id", "SPEAKER_00"),
                    start_time=float(turn.get("start_time", 0.0)),
                    end_time=float(turn.get("end_time", 0.0)),
                    text=turn.get("text", ""),
                    sequence_number=turn.get("sequence_number", idx + 1),
                    sentiment=turn.get("sentiment"),
                    intent=turn.get("intent"),
                    entities=turn.get("entities"),
                    alignment_metadata=turn.get("alignment_metadata"),
                )
                db.add(turn_obj)

        db.commit()
        db.refresh(transcript)
        return transcript
