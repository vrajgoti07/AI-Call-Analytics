"""
AI Call Analytics — Call Application Service.

Coordinates call creation, secure audio upload handling, and background task dispatch.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    AudioTooLargeError,
    AudioUploadError,
    CallNotFoundError,
    UnsupportedAudioError,
)
from backend.app.models.call import Call, CallStatus, JobStatus, JobType
from backend.app.repositories.call_repository import CallRepository
from backend.app.repositories.job_repository import JobRepository
from backend.app.workers.pipeline_tasks import analyze_call_task

logger = logging.getLogger("backend.app.services.call_service")


class CallService:
    """Service orchestrating call lifecycle, uploads, and pipeline jobs."""

    @staticmethod
    def create_call(
        db: Session,
        external_id: str | None = None,
        language: str | None = "en",
    ) -> Call:
        """Create a new Call entity in UPLOADED state."""
        return CallRepository.create_call(
            db=db,
            external_id=external_id,
            language=language,
            status=CallStatus.UPLOADED.value,
        )

    @staticmethod
    def upload_audio_for_call(
        db: Session,
        call_id: uuid.UUID,
        file: UploadFile,
    ) -> Call:
        """
        Validate and save uploaded audio file with security constraints:
        - Extension whitelist
        - MIME type check
        - Size limit check
        - Safe file naming to prevent directory traversal
        """
        call = CallRepository.get_by_id(db, call_id)
        if not call:
            raise CallNotFoundError(call_id)

        # 1. Validate filename and extension
        filename = file.filename or "audio.wav"
        ext = Path(filename).suffix.lower()
        if ext not in settings.allowed_audio_extensions:
            raise UnsupportedAudioError(ext)

        # 2. Check MIME type if provided
        if file.content_type and file.content_type not in settings.allowed_mime_types:
            logger.warning("Uncommon MIME type '%s' for '%s'", file.content_type, filename)

        # 3. Create destination directory
        upload_dir = Path(settings.storage_local_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{call_id}{ext}"
        destination = upload_dir / safe_filename

        # 4. Stream write with size limit checking
        total_size = 0
        try:
            with open(destination, "wb") as buffer:
                while chunk := file.file.read(1024 * 1024):  # 1MB chunks
                    total_size += len(chunk)
                    if total_size > settings.max_upload_size:
                        raise AudioTooLargeError(total_size, settings.max_upload_size)
                    buffer.write(chunk)
        except Exception:
            if destination.exists():
                destination.unlink()
            raise

        # 5. Attach metadata to Call
        CallRepository.attach_audio_file(
            db=db,
            call_id=call_id,
            filename=filename,
            storage_key=str(destination),
            mime_type=file.content_type or "audio/wav",
            size=total_size,
            sample_rate=settings.audio_sample_rate,
            channels=settings.audio_channels,
        )

        return call

    @staticmethod
    def start_call_analysis(
        db: Session,
        call_id: uuid.UUID,
        force_reprocess: bool = False,
    ) -> uuid.UUID:
        """
        Create a ProcessingJob and enqueue Celery analysis task.

        Returns:
            Job ID of the created background job.
        """
        call = CallRepository.get_by_id(db, call_id)
        if not call:
            raise CallNotFoundError(call_id)

        # Create Job in DB
        job = JobRepository.create_job(
            db=db,
            call_id=call_id,
            job_type=JobType.FULL_CALL_ANALYSIS.value,
        )

        # Dispatch Celery task
        try:
            async_result = analyze_call_task.delay(
                str(call_id),
                str(job.id),
                force_reprocess,
            )
            job.task_id = async_result.id
            db.commit()
            logger.info("Enqueued Celery task %s for call %s (job %s)", async_result.id, call_id, job.id)
        except Exception as e:
            logger.warning(
                "Celery broker dispatch unavailable (%s). Running synchronously/fallback.",
                e,
            )
            # If Redis/Celery worker isn't running in local testing, execute synchronously
            try:
                analyze_call_task(
                    call_id_str=str(call_id),
                    job_id_str=str(job.id),
                    force_reprocess=force_reprocess,
                )
            except Exception as sync_err:
                logger.error("Synchronous fallback task failed: %s", sync_err)

        # Update Call status to QUEUED
        CallRepository.update_status(db, call_id, CallStatus.QUEUED.value)
        return job.id
