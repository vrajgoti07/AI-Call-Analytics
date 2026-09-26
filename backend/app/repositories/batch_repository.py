"""
AI Call Analytics — Ingestion Batch Repository.

Handles CRUD operations and tenant-scoped retrieval for IngestionBatch entities.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.ingestion_batch import BatchStatus, IngestionBatch


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class BatchRepository:
    """Repository handling database access for IngestionBatch records."""

    @staticmethod
    def get_by_id(
        db: Session,
        batch_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
    ) -> IngestionBatch | None:
        """Fetch a batch by primary key, optionally verifying company ownership."""
        stmt = select(IngestionBatch).where(IngestionBatch.id == batch_id)
        if company_id is not None:
            stmt = stmt.where(IngestionBatch.company_id == company_id)
        return db.scalar(stmt)

    @staticmethod
    def create_batch(
        db: Session,
        company_id: uuid.UUID,
        original_filename: str,
        display_name: str,
        upload_type: str = "ZIP",
        archive_size: int | None = None,
        file_hash: str | None = None,
    ) -> IngestionBatch:
        """Create and persist a new IngestionBatch."""
        batch = IngestionBatch(
            company_id=company_id,
            original_filename=original_filename,
            display_name=display_name,
            upload_type=upload_type,
            status=BatchStatus.UPLOADING.value,
            archive_size=archive_size,
            file_hash=file_hash,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def update_status(
        db: Session,
        batch_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> IngestionBatch | None:
        """Update batch lifecycle status."""
        batch = db.scalar(select(IngestionBatch).where(IngestionBatch.id == batch_id))
        if not batch:
            return None
        batch.status = status
        if error_message is not None:
            batch.error_message = error_message
        if status in (BatchStatus.COMPLETED.value, BatchStatus.PARTIAL.value, BatchStatus.FAILED.value):
            batch.completed_at = utc_now()
        batch.updated_at = utc_now()
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def update_counters(
        db: Session,
        batch_id: uuid.UUID,
        total_files: int | None = None,
        processed_count: int | None = None,
        skipped_count: int | None = None,
        failed_count: int | None = None,
    ) -> IngestionBatch | None:
        """Update file processing counters for the batch."""
        batch = db.scalar(select(IngestionBatch).where(IngestionBatch.id == batch_id))
        if not batch:
            return None
        if total_files is not None:
            batch.total_files = total_files
        if processed_count is not None:
            batch.processed_count = processed_count
        if skipped_count is not None:
            batch.skipped_count = skipped_count
        if failed_count is not None:
            batch.failed_count = failed_count
        batch.updated_at = utc_now()
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def list_batches(
        db: Session,
        company_id: uuid.UUID,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[IngestionBatch], int, int]:
        """List batches scoped to a company workspace with pagination."""
        base_query = select(IngestionBatch).where(
            IngestionBatch.company_id == company_id
        )
        if status:
            base_query = base_query.where(IngestionBatch.status == status)
        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(
                or_(
                    IngestionBatch.original_filename.ilike(search_pattern),
                    IngestionBatch.display_name.ilike(search_pattern),
                )
            )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = db.scalar(count_stmt) or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(desc(IngestionBatch.created_at))
            .offset(offset)
            .limit(page_size)
        )
        batches = list(db.scalars(stmt))
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return batches, total, total_pages

    @staticmethod
    def delete_batch(db: Session, batch_id: uuid.UUID) -> bool:
        """Delete a batch and cascade to its related records."""
        batch = db.scalar(select(IngestionBatch).where(IngestionBatch.id == batch_id))
        if not batch:
            return False
        db.delete(batch)
        db.commit()
        return True
