"""
AI Call Analytics — Calls API Router.

Endpoints for call creation, audio file uploads, retrieval, listing, and deletion,
scoped strictly to the authenticated user's company workspace.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.exceptions import AppException, CallNotFoundError
from backend.app.database.session import get_db
from backend.app.models.call import CallStatus
from backend.app.models.user import User
from backend.app.repositories.call_repository import CallRepository
from backend.app.repositories.job_repository import JobRepository
from backend.app.schemas.call import (
    BulkIngestResponse,
    CallCreate,
    CallDetailResponse,
    CallListResponse,
    CallResponse,
)
from backend.app.schemas.common import PaginationMeta
from backend.app.services.bulk_upload_service import BulkUploadService
from backend.app.services.call_service import CallService

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post(
    "",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new call record",
)
def create_call(
    payload: CallCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CallResponse:
    """Create a new Call entity before uploading audio, associated with current user's company."""
    call = CallService.create_call(
        db=db,
        company_id=current_user.company_id,
        external_id=payload.external_id,
        language=payload.language,
    )
    return CallResponse.model_validate(call)


@router.post(
    "/{call_id}/upload",
    response_model=CallResponse,
    summary="Upload audio recording for a call",
)
def upload_audio(
    call_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CallResponse:
    """
    Upload an audio file (.wav, .mp3, .flac) for an existing Call entity.
    Enforces company workspace ownership.
    """
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    updated_call = CallService.upload_audio_for_call(db=db, call_id=call_id, file=file)
    return CallResponse.model_validate(updated_call)


@router.post(
    "/upload-zip",
    response_model=BulkIngestResponse,
    summary="Upload and ingest multiple calls from a ZIP archive",
)
def upload_zip(
    file: UploadFile = File(...),
    auto_analyze: bool = Query(default=True, description="Automatically queue AI analysis pipeline for ingested calls"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkIngestResponse:
    """
    Ingest call recordings from a ZIP archive scoped strictly to current user's workspace.
    Validates ZIP, detects duplicates via SHA-256, protects against path traversal and zip bombs.
    """
    return BulkUploadService.process_zip_upload(
        db=db,
        company_id=current_user.company_id,
        zip_file=file,
        auto_analyze=auto_analyze,
    )


@router.get(
    "",
    response_model=CallListResponse,
    summary="List calls with filtering and pagination",
)
def list_calls(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (e.g. UPLOADED, COMPLETED)"),
    language: str | None = Query(default=None, description="Filter by language code"),
    date_from: datetime | None = Query(default=None, description="Created on or after"),
    date_to: datetime | None = Query(default=None, description="Created on or before"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CallListResponse:
    """List calls scoped strictly to the authenticated user's workspace."""
    calls, total, total_pages = CallRepository.list_calls(
        db=db,
        company_id=current_user.company_id,
        status=status_filter,
        language=language,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return CallListResponse(
        items=[CallResponse.model_validate(c) for c in calls],
        pagination=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/{call_id}",
    response_model=CallDetailResponse,
    summary="Retrieve call detail by ID",
)
def get_call(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CallDetailResponse:
    """Retrieve detailed metadata for a specific call belonging to the user's workspace."""
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    latest_job = JobRepository.get_latest_for_call(db, call_id)

    return CallDetailResponse(
        id=call.id,
        external_id=call.external_id,
        status=call.status,
        duration=call.duration,
        language=call.language,
        created_at=call.created_at,
        updated_at=call.updated_at,
        audio_file=call.audio_file,
        has_transcript=call.transcript is not None,
        has_risk_analysis=len(getattr(call, "escalation_risks", [])) > 0 or call.status == CallStatus.COMPLETED.value,
        latest_job_id=latest_job.id if latest_job else None,
    )


@router.get(
    "/{call_id}/audio",
    summary="Stream raw audio recording for a call",
)
def get_call_audio(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream stored audio file for browser playback, enforcing tenant boundary."""
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)
    if not call.audio_file or not call.audio_file.storage_key:
        raise AppException(
            code="AUDIO_NOT_FOUND",
            message=f"No audio file associated with call '{call_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    audio_path = Path(call.audio_file.storage_key)
    if not audio_path.exists():
        raise AppException(
            code="AUDIO_FILE_MISSING",
            message=f"Audio file '{call.audio_file.filename}' is not found on disk.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return FileResponse(
        path=str(audio_path),
        media_type=call.audio_file.mime_type or "audio/wav",
        filename=call.audio_file.filename,
    )


@router.delete(
    "/{call_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a call and its associated records",
)
def delete_call(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete a call from the user's workspace."""
    call = CallRepository.get_by_id(db, call_id, company_id=current_user.company_id)
    if not call:
        raise CallNotFoundError(call_id)

    deleted = CallRepository.delete_call(db, call_id)
    if not deleted:
        raise CallNotFoundError(call_id)
