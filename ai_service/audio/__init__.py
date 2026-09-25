"""
AI Call Analytics — Audio Preprocessing Pipeline.

Provides production-grade audio standardization for call analytics:
- Ingestion & format validation (.wav, .mp3, .flac, .ogg, .m4a)
- Conversion to 16 kHz sampling rate
- Stereo-to-mono downmixing
- Linear peak amplitude normalization (-1.0 dBFS)
- Audio quality diagnostics (clipping, silence, amplitude telemetry)
- Idempotent storage and temporary file safety
- Strict output verification
"""

from ai_service.audio.config import AudioConfig, DEFAULT_AUDIO_CONFIG
from ai_service.audio.diagnostics import analyze_audio_quality
from ai_service.audio.engine import (
    is_ffmpeg_available,
    normalize_audio,
    process_audio_file,
    resample_audio,
    to_mono,
)
from ai_service.audio.exceptions import (
    AudioFileNotFoundError,
    AudioProcessingError,
    FFmpegConversionError,
    FFmpegNotInstalledError,
    InvalidAudioStreamError,
    InvalidDurationError,
    OutputValidationError,
    OutputWriteError,
    UnreadableAudioError,
    UnsupportedAudioFormatError,
)
from ai_service.audio.preprocessor import AudioPreprocessor
from ai_service.audio.schema import (
    AudioMetadata,
    AudioProcessingResult,
    AudioQualityDiagnostics,
    AudioValidationResult,
)
from ai_service.audio.validator import (
    extract_audio_metadata,
    validate_audio_file,
    verify_standardized_audio,
)

__all__ = [
    "AudioConfig",
    "DEFAULT_AUDIO_CONFIG",
    "AudioPreprocessor",
    "AudioMetadata",
    "AudioValidationResult",
    "AudioQualityDiagnostics",
    "AudioProcessingResult",
    "AudioProcessingError",
    "AudioFileNotFoundError",
    "UnsupportedAudioFormatError",
    "UnreadableAudioError",
    "FFmpegNotInstalledError",
    "FFmpegConversionError",
    "InvalidAudioStreamError",
    "InvalidDurationError",
    "OutputWriteError",
    "OutputValidationError",
    "validate_audio_file",
    "verify_standardized_audio",
    "extract_audio_metadata",
    "analyze_audio_quality",
    "resample_audio",
    "to_mono",
    "normalize_audio",
    "is_ffmpeg_available",
    "process_audio_file",
]
