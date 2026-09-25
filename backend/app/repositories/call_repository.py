"""
AI Call Analytics — Call Repository.

Handles relational database queries and transactions for Call and AudioFile entities.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models.call import AudioFile, Call, CallStatus


class CallRepository:
    """Repository handling CRUD operations for Call and AudioFile records."""

    @staticmethod
    def get_by_id(db: Session, call_id: uuid.UUID) -> Call | None:
        """Retrieve a Call by its primary key with audio_file and transcript loaded."""
        stmt = (
            select(Call)
            .options(joinedload(Call.audio_file), joinedload(Call.transcript))
            .where(Call.id == call_id)
        )
        return db.scalar(stmt)

    @staticmethod
    def list_calls(
        db: Session,
        status: str | None = None,
        language: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Call], int, int]:
        """
        List calls with optional filtering, bounded pagination, and total count.

        Returns:
            Tuple of (calls_list, total_count, total_pages)
        """
        base_query = select(Call).options(joinedload(Call.audio_file))

        if status:
            base_query = base_query.where(Call.status == status)
        if language:
            base_query = base_query.where(Call.language == language)
        if date_from:
            base_query = base_query.where(Call.created_at >= date_from)
        if date_to:
            base_query = base_query.where(Call.created_at <= date_to)

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = db.scalar(count_stmt) or 0

        # Pagination offset
        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(desc(Call.created_at))
            .offset(offset)
            .limit(page_size)
        )
        calls = list(db.scalars(stmt).unique())
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return calls, total, total_pages

    @staticmethod
    def create_call(
        db: Session,
        external_id: str | None = None,
        language: str | None = "en",
        status: str = CallStatus.UPLOADED.value,
    ) -> Call:
        """Create and persist a new Call record."""
        call = Call(
            external_id=external_id,
            language=language,
            status=status,
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call

    @staticmethod
    def update_status(
        db: Session,
        call_id: uuid.UUID,
        status: str,
        duration: float | None = None,
    ) -> Call | None:
        """Update lifecycle status and optional duration for a call."""
        call = CallRepository.get_by_id(db, call_id)
        if not call:
            return None
        call.status = status
        if duration is not None:
            call.duration = duration
        db.commit()
        db.refresh(call)
        return call

    @staticmethod
    def attach_audio_file(
        db: Session,
        call_id: uuid.UUID,
        filename: str,
        storage_key: str,
        mime_type: str,
        size: int,
        sample_rate: int = 16000,
        channels: int = 1,
        duration: float | None = None,
    ) -> AudioFile:
        """Attach or replace audio file metadata for a call."""
        call = CallRepository.get_by_id(db, call_id)
        if not call:
            raise ValueError(f"Call with id {call_id} does not exist.")

        if call.audio_file:
            audio = call.audio_file
            audio.filename = filename
            audio.storage_key = storage_key
            audio.mime_type = mime_type
            audio.size = size
            audio.sample_rate = sample_rate
            audio.channels = channels
            audio.duration = duration
        else:
            audio = AudioFile(
                call_id=call_id,
                filename=filename,
                storage_key=storage_key,
                mime_type=mime_type,
                size=size,
                sample_rate=sample_rate,
                channels=channels,
                duration=duration,
            )
            db.add(audio)

        db.commit()
        db.refresh(audio)
        return audio

    @staticmethod
    def delete_call(db: Session, call_id: uuid.UUID) -> bool:
        """Delete a call and cascade delete associated records."""
        call = CallRepository.get_by_id(db, call_id)
        if not call:
            return False
        db.delete(call)
        db.commit()
        return True
