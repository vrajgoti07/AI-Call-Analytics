"""
AI Call Analytics — Processing Job Repository.

Tracks and updates asynchronous task execution states, pipeline stages, and progress.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.models.call import JobStatus, JobType, ProcessingJob


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class JobRepository:
    """Repository handling ProcessingJob tracking and stage progress updates."""

    @staticmethod
    def get_by_id(db: Session, job_id: uuid.UUID) -> ProcessingJob | None:
        """Fetch job by primary key."""
        stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
        return db.scalar(stmt)

    @staticmethod
    def get_latest_for_call(db: Session, call_id: uuid.UUID) -> ProcessingJob | None:
        """Fetch the most recent processing job for a call."""
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.call_id == call_id)
            .order_by(desc(ProcessingJob.created_at))
            .limit(1)
        )
        return db.scalar(stmt)

    @staticmethod
    def create_job(
        db: Session,
        call_id: uuid.UUID,
        task_id: str | None = None,
        job_type: str = JobType.FULL_CALL_ANALYSIS.value,
        initial_stages: dict[str, str] | None = None,
    ) -> ProcessingJob:
        """Create and persist a new ProcessingJob in PENDING state."""
        default_stages = {
            "preprocessing": "PENDING",
            "transcription": "PENDING",
            "diarization": "PENDING",
            "nlp": "PENDING",
            "embeddings": "PENDING",
            "themes": "PENDING",
            "risk": "PENDING",
        }
        if initial_stages:
            default_stages.update(initial_stages)

        job = ProcessingJob(
            call_id=call_id,
            task_id=task_id,
            job_type=job_type,
            status=JobStatus.PENDING.value,
            progress=0,
            current_stage=None,
            stages=default_stages,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def update_stage(
        db: Session,
        job_id: uuid.UUID,
        stage: str,
        stage_status: str,
        progress: int,
    ) -> ProcessingJob | None:
        """Update current stage, overall progress, and stage dictionary."""
        job = JobRepository.get_by_id(db, job_id)
        if not job:
            return None

        if job.status == JobStatus.PENDING.value:
            job.status = JobStatus.PROCESSING.value
            job.started_at = utc_now()

        job.current_stage = stage
        job.progress = min(100, max(0, progress))
        stages = dict(job.stages)
        stages[stage] = stage_status
        job.stages = stages
        job.updated_at = utc_now()

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def mark_completed(db: Session, job_id: uuid.UUID) -> ProcessingJob | None:
        """Mark job as successfully completed with 100% progress."""
        job = JobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.status = JobStatus.SUCCESS.value
        job.progress = 100
        job.completed_at = utc_now()
        job.updated_at = utc_now()

        # Ensure all stages are marked completed
        stages = dict(job.stages)
        for k in stages:
            if stages[k] != "FAILED":
                stages[k] = "COMPLETED"
        job.stages = stages

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def mark_failed(
        db: Session,
        job_id: uuid.UUID,
        error_code: str,
        error_message: str,
    ) -> ProcessingJob | None:
        """Mark job as failed with error code and description."""
        job = JobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.status = JobStatus.FAILURE.value
        job.error_code = error_code
        job.error_message = error_message
        job.completed_at = utc_now()
        job.updated_at = utc_now()

        if job.current_stage:
            stages = dict(job.stages)
            stages[job.current_stage] = "FAILED"
            job.stages = stages

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def list_jobs(
        db: Session,
        call_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProcessingJob], int, int]:
        """List jobs with pagination."""
        base_query = select(ProcessingJob)
        if call_id:
            base_query = base_query.where(ProcessingJob.call_id == call_id)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = db.scalar(count_stmt) or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(desc(ProcessingJob.created_at))
            .offset(offset)
            .limit(page_size)
        )
        jobs = list(db.scalars(stmt))
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return jobs, total, total_pages
