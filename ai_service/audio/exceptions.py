"""
AI Call Analytics — Audio Processing Exceptions.

Defines custom, descriptive exceptions for the audio ingestion, validation,
conversion, and quality check stages.
"""

from __future__ import annotations


class AudioProcessingError(Exception):
    """Base exception for all audio processing errors in AI Call Analytics."""


class AudioFileNotFoundError(AudioProcessingError, FileNotFoundError):
    """Raised when an audio file cannot be found at the specified path."""


class UnsupportedAudioFormatError(AudioProcessingError):
    """Raised when an input audio format is not supported by the pipeline."""


class UnreadableAudioError(AudioProcessingError):
    """Raised when an audio file is corrupted, malformed, or unreadable."""


class FFmpegNotInstalledError(AudioProcessingError):
    """Raised when FFmpeg binary is required but not found on the system PATH."""


class FFmpegConversionError(AudioProcessingError):
    """Raised when FFmpeg subprocess exits with a non-zero return code or error."""


class InvalidAudioStreamError(AudioProcessingError):
    """Raised when an audio file contains no valid audio stream or has invalid channels."""


class InvalidDurationError(AudioProcessingError):
    """Raised when audio duration violates configured minimum or maximum limits."""


class OutputWriteError(AudioProcessingError):
    """Raised when writing the processed audio file fails."""


class OutputValidationError(AudioProcessingError):
    """Raised when the generated output file fails mandatory 16kHz mono WAV validation."""
