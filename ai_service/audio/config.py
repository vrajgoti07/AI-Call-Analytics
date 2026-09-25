"""
AI Call Analytics — Audio Pipeline Configuration.

Provides centralized, configurable parameters for audio resampling,
channel conversion, amplitude normalization, quality thresholds, and paths.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AudioConfig:
    """Configuration settings for the Audio Preprocessing Pipeline."""

    # Target specification for downstream Whisper & Diarization
    target_sample_rate: int = 16000
    target_channels: int = 1
    target_format: str = "wav"
    target_subtype: str = "PCM_16"

    # Normalization parameters (Speech-Oriented Peak Normalization)
    # Headroom of -1.0 dBFS ensures speech peaks reach optimal level without clipping
    normalization_enabled: bool = True
    target_peak_dbfs: float = -1.0
    min_norm_peak_threshold: float = 1e-4  # Skip normalizing near-silent audio to avoid amplifying noise

    # Silence handling (Preserved by default for conversational call analysis)
    trim_silence: bool = False
    silence_threshold_db: float = -40.0
    silence_warning_ratio: float = 0.90  # Warn if > 90% is silence

    # Clipping detection
    clipping_threshold: float = 0.999
    clipping_warning_ratio: float = 0.001  # Warn if > 0.1% samples clipped

    # Duration limits (in seconds)
    min_duration_seconds: float = 0.5     # Minimum 500ms
    max_duration_seconds: float = 7200.0   # Maximum 2 hours per call recording
    max_file_size_bytes: int = 500 * 1024 * 1024  # 500 MB max input file size

    # Supported input formats
    supported_formats: tuple[str, ...] = (
        ".wav",
        ".mp3",
        ".flac",
        ".ogg",
        ".m4a",
        ".aac",
        ".wma",
    )

    # Output storage and directory policy
    output_dir: str = "data/processed"
    overwrite_policy: str = "reuse_existing"  # 'reuse_existing', 'overwrite', or 'error'

    # Backend preference
    prefer_ffmpeg: bool = True

    @classmethod
    def from_env(cls) -> AudioConfig:
        """Create AudioConfig instance with environment variable overrides."""
        target_sr = int(os.environ.get("AUDIO_SAMPLE_RATE", "16000"))
        target_ch = int(os.environ.get("AUDIO_CHANNELS", "1"))
        norm_enabled = os.environ.get("NORMALIZATION_ENABLED", "true").lower() in ("true", "1", "yes")
        output_dir = os.environ.get("AUDIO_OUTPUT_DIR", "data/processed")
        min_dur = float(os.environ.get("MIN_AUDIO_DURATION", "0.5"))
        max_dur = float(os.environ.get("MAX_AUDIO_DURATION", "7200.0"))
        overwrite_policy = os.environ.get("AUDIO_OVERWRITE_POLICY", "reuse_existing")

        return cls(
            target_sample_rate=target_sr,
            target_channels=target_ch,
            normalization_enabled=norm_enabled,
            output_dir=output_dir,
            min_duration_seconds=min_dur,
            max_duration_seconds=max_dur,
            overwrite_policy=overwrite_policy,
        )


# Global default configuration instance
DEFAULT_AUDIO_CONFIG = AudioConfig()
