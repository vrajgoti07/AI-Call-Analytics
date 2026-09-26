"""
AI Call Analytics — Secure Bulk & ZIP Call Ingestion Service.

Implements safe, multi-tenant ZIP extraction, security guards:
1. ZIP Bomb protection (ratio & uncompressed size limits)
2. Directory Traversal prevention
3. Supported audio format validation
4. SHA-256 duplicate detection per company workspace
5. Automated background pipeline dispatching
6. IngestionBatch creation for ZIP-wise call management
7. Real audio duration extraction
"""

from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
import os
import re
import struct
import uuid
import wave
import zipfile
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.exceptions import AppException
from backend.app.models.call import AudioFile, Call, CallStatus
from backend.app.models.ingestion_batch import BatchStatus, BatchUploadType, IngestionBatch
from backend.app.repositories.batch_repository import BatchRepository
from backend.app.repositories.call_repository import CallRepository
from backend.app.schemas.call import BulkIngestResponse, CallResponse, SkippedFileInfo
from backend.app.services.call_service import CallService

logger = logging.getLogger("backend.app.services.bulk_upload_service")

# Security limits for ZIP uploads
MAX_UNCOMPRESSED_ZIP_SIZE = 250 * 1024 * 1024  # 250 MB
MAX_FILES_PER_ZIP = 100
MAX_COMPRESSION_RATIO = 100.0


def _safe_stem(filename: str) -> str:
    """Generate safe, clean alphanumeric external_id stem from filename."""
    stem = Path(filename).stem
    cleaned = re.sub(r"[^\w\s-]", "", stem).strip()
    cleaned = re.sub(r"[\s_-]+", "-", cleaned)
    return cleaned[:100] or f"call-{uuid.uuid4().hex[:8]}"


def _extract_audio_duration(content: bytes, filename: str) -> float | None:
    """
    Extract real audio duration from audio file bytes.
    Supports WAV (via wave module) and estimates for other formats via file size.
    Returns duration in seconds, or None if extraction fails.
    """
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".wav":
            buf = io.BytesIO(content)
            with wave.open(buf, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return round(frames / rate, 3)
        # Try mutagen for MP3/FLAC/OGG/M4A if available
        try:
            import mutagen
            buf = io.BytesIO(content)
            audio_meta = mutagen.File(buf, filename=filename)
            if audio_meta is not None and audio_meta.info and hasattr(audio_meta.info, "length"):
                return round(audio_meta.info.length, 3)
        except ImportError:
            pass
        except Exception:
            pass
    except Exception as e:
        logger.warning("Failed to extract audio duration from %s: %s", filename, e)
    return None


class BulkUploadService:
    """Service orchestrating secure ZIP call ingestion and duplicate detection."""

    @classmethod
    def process_zip_upload(
        cls,
        db: Session,
        company_id: uuid.UUID,
        zip_file: UploadFile,
        auto_analyze: bool = True,
    ) -> BulkIngestResponse:
        """
        Validate, extract, deduplicate, and ingest audio files from a ZIP archive
        scoped strictly to the specified company workspace.
        Creates an IngestionBatch to group all calls from this ZIP.
        """
        filename = zip_file.filename or "calls.zip"
        if not filename.lower().endswith(".zip"):
            raise AppException(
                code="INVALID_ARCHIVE_FORMAT",
                message="Uploaded file must be a .zip archive.",
                status_code=400,
            )

        # Read zip file bytes with upload size checking
        zip_bytes = io.BytesIO()
        total_zip_size = 0
        while chunk := zip_file.file.read(1024 * 1024):
            total_zip_size += len(chunk)
            if total_zip_size > settings.max_upload_size:
                raise AppException(
                    code="ZIP_TOO_LARGE",
                    message=f"ZIP archive size ({total_zip_size} bytes) exceeds maximum limit ({settings.max_upload_size} bytes).",
                    status_code=413,
                )
            zip_bytes.write(chunk)

        zip_bytes.seek(0)

        # Validate ZIP archive structure
        if not zipfile.is_zipfile(zip_bytes):
            raise AppException(
                code="CORRUPT_ZIP_ARCHIVE",
                message="The uploaded file is not a valid or readable ZIP archive.",
                status_code=400,
            )

        try:
            zf = zipfile.ZipFile(zip_bytes, "r")
        except Exception as e:
            raise AppException(
                code="ZIP_READ_ERROR",
                message=f"Unable to read ZIP archive: {e}",
                status_code=400,
            )

        infolist = zf.infolist()
        if len(infolist) > MAX_FILES_PER_ZIP:
            raise AppException(
                code="ZIP_TOO_MANY_FILES",
                message=f"ZIP contains {len(infolist)} files, exceeding maximum of {MAX_FILES_PER_ZIP}.",
                status_code=400,
            )

        # Security check: ZIP Bomb prevention
        total_uncompressed = sum(info.file_size for info in infolist)
        if total_uncompressed > MAX_UNCOMPRESSED_ZIP_SIZE:
            raise AppException(
                code="ZIP_BOMB_DETECTED",
                message=f"Uncompressed size ({total_uncompressed} bytes) exceeds maximum allowed ({MAX_UNCOMPRESSED_ZIP_SIZE} bytes).",
                status_code=400,
            )

        if total_zip_size > 0:
            compression_ratio = total_uncompressed / total_zip_size
            if compression_ratio > MAX_COMPRESSION_RATIO:
                raise AppException(
                    code="ZIP_BOMB_DETECTED",
                    message="Abnormally high compression ratio detected (potential zip bomb).",
                    status_code=400,
                )

        # Create IngestionBatch BEFORE processing any files
        zip_display_name = Path(filename).stem
        batch = BatchRepository.create_batch(
            db=db,
            company_id=company_id,
            original_filename=filename,
            display_name=zip_display_name,
            upload_type=BatchUploadType.ZIP.value,
            archive_size=total_zip_size,
        )
        logger.info("Created IngestionBatch %s for ZIP '%s' (company %s)", batch.id, filename, company_id)

        # Update batch status to PROCESSING
        BatchRepository.update_status(db, batch.id, BatchStatus.PROCESSING.value)

        # Destination directory for this company's calls
        company_upload_dir = Path(settings.storage_local_dir) / f"company_{company_id}"
        company_upload_dir.mkdir(parents=True, exist_ok=True)

        created_calls: list[Call] = []
        skipped_files: list[SkippedFileInfo] = []
        total_valid_entries = 0

        # Query existing file hashes for this company to prevent duplicates
        existing_hashes_stmt = (
            select(AudioFile.file_hash)
            .join(Call, AudioFile.call_id == Call.id)
            .where(Call.company_id == company_id, AudioFile.file_hash.isnot(None))
        )
        existing_hashes: set[str] = set(db.scalars(existing_hashes_stmt).all())

        for member in infolist:
            # Skip directories
            if member.is_dir():
                continue

            raw_name = member.filename
            base_name = Path(raw_name).name

            # Skip OS junk & hidden files (__MACOSX, .DS_Store, dotfiles)
            if (
                base_name.startswith(".")
                or "__MACOSX" in raw_name
                or base_name.startswith("._")
                or base_name.lower() == "thumbs.db"
            ):
                continue

            # Path traversal guard: ensure name doesn't contain '..' or absolute paths
            if ".." in raw_name or raw_name.startswith(("/", "\\")) or ":" in raw_name:
                skipped_files.append(
                    SkippedFileInfo(filename=base_name, reason="Malicious or invalid relative path detected in archive.")
                )
                continue

            total_valid_entries += 1
            ext = Path(base_name).suffix.lower()

            # Check supported audio format
            if ext not in settings.allowed_audio_extensions:
                skipped_files.append(
                    SkippedFileInfo(
                        filename=base_name,
                        reason=f"Unsupported audio format '{ext}'. Allowed: {', '.join(settings.allowed_audio_extensions)}",
                    )
                )
                continue

            # Read file content safely
            try:
                content = zf.read(member)
            except Exception as e:
                skipped_files.append(
                    SkippedFileInfo(filename=base_name, reason=f"Failed to read file from archive: {e}")
                )
                continue

            if len(content) == 0:
                skipped_files.append(
                    SkippedFileInfo(filename=base_name, reason="File is empty (0 bytes).")
                )
                continue

            # Compute SHA-256 hash for deduplication
            file_hash = hashlib.sha256(content).hexdigest()

            # Check duplicate against this company's calls
            if file_hash in existing_hashes:
                skipped_files.append(
                    SkippedFileInfo(
                        filename=base_name,
                        reason="Duplicate audio recording already exists in this workspace.",
                    )
                )
                continue

            # Generate new Call entity
            call_id = uuid.uuid4()
            safe_filename = f"{call_id}{ext}"
            destination = company_upload_dir / safe_filename

            try:
                with open(destination, "wb") as f_out:
                    f_out.write(content)
            except Exception as e:
                logger.error("Failed to write extracted audio file %s: %s", destination, e)
                skipped_files.append(
                    SkippedFileInfo(filename=base_name, reason=f"Server storage error: {e}")
                )
                continue

            # Extract real audio duration
            audio_duration = _extract_audio_duration(content, base_name)
            if audio_duration is not None:
                logger.info("Extracted real duration for %s: %.3f seconds", base_name, audio_duration)
            else:
                logger.warning("AUDIO_DURATION_UNAVAILABLE: Could not extract duration from %s", base_name)

            # Guess mime-type
            mime_type, _ = mimetypes.guess_type(base_name)
            mime_type = mime_type or "audio/wav"

            # Persist Call with batch_id
            external_id = _safe_stem(base_name)
            call = Call(
                id=call_id,
                company_id=company_id,
                batch_id=batch.id,
                external_id=external_id,
                status=CallStatus.UPLOADED.value,
                duration=audio_duration,
                language="en",
            )
            db.add(call)
            db.flush()

            # Persist AudioFile with real duration
            audio_record = AudioFile(
                id=uuid.uuid4(),
                call_id=call_id,
                filename=base_name,
                storage_key=str(destination),
                mime_type=mime_type,
                size=len(content),
                duration=audio_duration,
                file_hash=file_hash,
                audio_data=content,
                sample_rate=settings.audio_sample_rate,
                channels=settings.audio_channels,
            )
            db.add(audio_record)
            db.commit()
            db.refresh(call)

            existing_hashes.add(file_hash)
            created_calls.append(call)

            # Trigger automated background analysis if requested
            if auto_analyze:
                try:
                    CallService.start_call_analysis(db=db, call_id=call_id)
                except Exception as e:
                    logger.warning("Auto analysis trigger note for call %s: %s", call_id, e)

        db.commit()

        # Update batch counters and determine final status
        failed_count = total_valid_entries - len(created_calls) - len(skipped_files)
        if failed_count < 0:
            failed_count = 0

        BatchRepository.update_counters(
            db=db,
            batch_id=batch.id,
            total_files=total_valid_entries,
            processed_count=len(created_calls),
            skipped_count=len(skipped_files),
            failed_count=failed_count,
        )

        # Determine batch status based on results
        if len(created_calls) == 0:
            if total_valid_entries == 0:
                batch_status = BatchStatus.COMPLETED.value  # No audio files in ZIP
            else:
                batch_status = BatchStatus.FAILED.value
        elif len(skipped_files) > 0 or failed_count > 0:
            # Some calls were created, some skipped - mark as PROCESSING (analysis still running)
            batch_status = BatchStatus.PROCESSING.value
        else:
            batch_status = BatchStatus.PROCESSING.value  # All calls created, analysis running

        BatchRepository.update_status(db, batch.id, batch_status)

        return BulkIngestResponse(
            batch_id=batch.id,
            batch_name=batch.display_name,
            total_files=total_valid_entries,
            processed_count=len(created_calls),
            skipped_count=len(skipped_files),
            created_calls=[CallResponse.model_validate(c) for c in created_calls],
            skipped_files=skipped_files,
        )
