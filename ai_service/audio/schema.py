"""
AI Call Analytics — Audio Processing Schema & Contracts.

Defines strongly typed dataclasses representing the input audio metadata,
validation results, quality diagnostics telemetry, and final processing results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AudioMetadata:
    """Metadata extracted from an audio file."""

    path: str
    format: str
    sample_rate: int
    channels: int
    duration_seconds: float
    file_size_bytes: int
    subtype: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to dictionary."""
        return asdict(self)


@dataclass
class AudioValidationResult:
    """Structured report returned by the audio validation layer."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    format: str | None = None
    file_size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize validation result to dictionary."""
        return asdict(self)


@dataclass
class AudioQualityDiagnostics:
    """Telemetry report diagnosing audio amplitude, clipping, and silence."""

    is_silent: bool
    silence_percentage: float
    is_clipped: bool
    clipping_percentage: float
    peak_amplitude: float
    peak_dbfs: float
    rms_amplitude: float
    rms_dbfs: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize diagnostics to dictionary."""
        return asdict(self)


@dataclass
class AudioProcessingResult:
    """
    Standardized contract produced by the Audio Preprocessing Pipeline.
    Consumed directly by downstream ASR (Whisper) and Speaker Diarization stages.
    """

    output_path: str
    output_format: str
    sample_rate: int
    channels: int
    duration_seconds: float
    file_size_bytes: int
    status: str  # 'success', 'reused', 'failed'
    processing_time_ms: float
    original_metadata: AudioMetadata
    warnings: list[str] = field(default_factory=list)
    quality_diagnostics: AudioQualityDiagnostics | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize processing result to dictionary."""
        return {
            "output_path": self.output_path,
            "output_format": self.output_format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status,
            "processing_time_ms": self.processing_time_ms,
            "original_metadata": self.original_metadata.to_dict(),
            "warnings": list(self.warnings),
            "quality_diagnostics": self.quality_diagnostics.to_dict() if self.quality_diagnostics else None,
        }
