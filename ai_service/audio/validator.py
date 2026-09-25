"""
AI Call Analytics — Audio Validation Layer.

Validates input audio files for existence, readability, supported containers,
duration limits, stream presence, and verifies standardized output specifications.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import soundfile as sf

from ai_service.audio.config import AudioConfig, DEFAULT_AUDIO_CONFIG
from ai_service.audio.exceptions import (
    AudioFileNotFoundError,
    InvalidAudioStreamError,
    InvalidDurationError,
    OutputValidationError,
    UnreadableAudioError,
    UnsupportedAudioFormatError,
)
from ai_service.audio.schema import AudioMetadata, AudioValidationResult

logger = logging.getLogger("ai_call_analytics.audio.validator")


def extract_audio_metadata(file_path: str | Path) -> AudioMetadata:
    """
    Extract technical stream metadata from an audio file.

    Args:
        file_path: Path to the audio file.

    Returns:
        AudioMetadata instance.

    Raises:
        AudioFileNotFoundError: If the file does not exist.
        UnreadableAudioError: If metadata cannot be read from the file.
    """
    path = Path(file_path).resolve()
    if not path.exists() or not path.is_file():
        raise AudioFileNotFoundError(f"Audio file not found: {path}")

    file_size = path.stat().st_size
    if file_size == 0:
        raise UnreadableAudioError(f"Audio file is empty (0 bytes): {path}")

    try:
        info = sf.info(str(path))
        return AudioMetadata(
            path=str(path),
            format=info.format or path.suffix.lstrip(".").upper(),
            sample_rate=info.samplerate,
            channels=info.channels,
            duration_seconds=round(info.duration, 4),
            file_size_bytes=file_size,
            subtype=info.subtype,
        )
    except Exception as err:
        logger.warning("soundfile failed to inspect '%s': %s", path.name, err)
        raise UnreadableAudioError(f"Cannot decode or inspect audio file '{path.name}': {err}") from err


def validate_audio_file(
    file_path: str | Path,
    config: AudioConfig | None = None,
) -> AudioValidationResult:
    """
    Perform pre-processing validation on an input audio file.

    Validates:
    - File exists and is a regular file.
    - File size is non-zero and within configured maximum limits.
    - File format/extension is supported.
    - Audio stream has valid duration, sample rate, and channels.
    - Duration complies with configured min/max limits.

    Args:
        file_path: Path to audio file.
        config: Optional AudioConfig instance.

    Returns:
        AudioValidationResult instance containing validation status, errors, warnings,
        and extracted metadata.
    """
    cfg = config or DEFAULT_AUDIO_CONFIG
    errors: list[str] = []
    warnings: list[str] = []

    path = Path(file_path)

    # 1. Existence check
    if not path.exists():
        errors.append(f"File not found: {path}")
        return AudioValidationResult(valid=False, errors=errors)

    if not path.is_file():
        errors.append(f"Path is not a regular file: {path}")
        return AudioValidationResult(valid=False, errors=errors)

    # 2. File size check
    file_size = path.stat().st_size
    if file_size == 0:
        errors.append(f"File is empty (0 bytes): {path}")
        return AudioValidationResult(valid=False, errors=errors, file_size_bytes=0)

    if file_size > cfg.max_file_size_bytes:
        errors.append(
            f"File size ({file_size / (1024 * 1024):.1f} MB) exceeds maximum allowed "
            f"({cfg.max_file_size_bytes / (1024 * 1024):.1f} MB)."
        )

    # 3. Format extension check
    suffix = path.suffix.lower()
    if suffix not in cfg.supported_formats:
        errors.append(
            f"Unsupported audio format '{suffix}'. Supported formats: {list(cfg.supported_formats)}"
        )

    # 4. Stream inspection
    meta: AudioMetadata | None = None
    try:
        meta = extract_audio_metadata(path)
    except Exception as err:
        errors.append(f"Unreadable audio stream: {err}")
        return AudioValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
            file_size_bytes=file_size,
        )

    # 5. Audio properties check
    if meta.duration_seconds <= 0:
        errors.append(f"Audio duration must be greater than 0s, got {meta.duration_seconds}s.")
    elif meta.duration_seconds < cfg.min_duration_seconds:
        errors.append(
            f"Audio duration ({meta.duration_seconds:.2f}s) is shorter than minimum allowed "
            f"({cfg.min_duration_seconds:.2f}s)."
        )
    elif meta.duration_seconds > cfg.max_duration_seconds:
        errors.append(
            f"Audio duration ({meta.duration_seconds:.1f}s) exceeds maximum allowed "
            f"({cfg.max_duration_seconds:.1f}s)."
        )

    if meta.sample_rate <= 0:
        errors.append(f"Invalid sample rate: {meta.sample_rate} Hz.")

    if meta.channels <= 0:
        errors.append(f"Invalid channel count: {meta.channels}.")

    is_valid = len(errors) == 0

    return AudioValidationResult(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        duration_seconds=meta.duration_seconds if meta else None,
        sample_rate=meta.sample_rate if meta else None,
        channels=meta.channels if meta else None,
        format=meta.format if meta else suffix.lstrip(".").upper(),
        file_size_bytes=file_size,
    )


def verify_standardized_audio(
    file_path: str | Path,
    config: AudioConfig | None = None,
) -> AudioMetadata:
    """
    Mandatory Output Verification (Step 18).

    Re-opens and verifies that the generated audio file strictly conforms
    to the target specification:
    - File exists and is readable.
    - Format == WAV
    - Subtype == PCM_16
    - Sample rate == 16000 Hz
    - Channels == 1 (Mono)
    - Duration > 0s

    Args:
        file_path: Path to the generated standardized audio file.
        config: Optional AudioConfig instance.

    Returns:
        Verified AudioMetadata instance.

    Raises:
        OutputValidationError: If any output property violates the specification.
    """
    cfg = config or DEFAULT_AUDIO_CONFIG
    path = Path(file_path).resolve()

    if not path.exists() or not path.is_file():
        raise OutputValidationError(f"Standardized output file does not exist: {path}")

    size = path.stat().st_size
    if size <= 44:  # 44 bytes is minimum standard WAV header size
        raise OutputValidationError(f"Standardized output file has invalid size ({size} bytes): {path}")

    try:
        info = sf.info(str(path))
    except Exception as err:
        raise OutputValidationError(f"Standardized output file is corrupted or unreadable: {err}") from err

    # Check WAV container
    if info.format != "WAV":
        raise OutputValidationError(
            f"Output validation failed: expected format 'WAV', got '{info.format}'."
        )

    # Check PCM_16 subtype
    if info.subtype != cfg.target_subtype:
        raise OutputValidationError(
            f"Output validation failed: expected subtype '{cfg.target_subtype}', got '{info.subtype}'."
        )

    # Check sample rate
    if info.samplerate != cfg.target_sample_rate:
        raise OutputValidationError(
            f"Output validation failed: expected sample rate {cfg.target_sample_rate} Hz, got {info.samplerate} Hz."
        )

    # Check channels (mono)
    if info.channels != cfg.target_channels:
        raise OutputValidationError(
            f"Output validation failed: expected {cfg.target_channels} channel(s), got {info.channels} channel(s)."
        )

    # Check duration
    if info.duration <= 0:
        raise OutputValidationError(
            f"Output validation failed: audio duration is {info.duration}s (must be > 0)."
        )

    return AudioMetadata(
        path=str(path),
        format=info.format,
        sample_rate=info.samplerate,
        channels=info.channels,
        duration_seconds=round(info.duration, 4),
        file_size_bytes=size,
        subtype=info.subtype,
    )
