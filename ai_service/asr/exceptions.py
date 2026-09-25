"""
AI Call Analytics — Automatic Speech Recognition (ASR) Exceptions.

Defines custom, descriptive exceptions for model loading, configuration,
input contract validation, transcription, and runtime errors.
"""

from __future__ import annotations


class ASRError(Exception):
    """Base exception for all ASR and speech-to-text operations."""


class AudioNotFoundError(ASRError, FileNotFoundError):
    """Raised when the specified audio file cannot be found."""


class InvalidPreprocessedAudioError(ASRError):
    """
    Raised when an audio file violates the Phase 2 standardization contract
    (e.g., not WAV, not 16 kHz, not mono, or corrupted PCM stream).
    """


class InvalidAudioStreamError(InvalidPreprocessedAudioError):
    """Raised when an audio file cannot be decoded as a valid audio stream."""


class InvalidDurationError(InvalidPreprocessedAudioError):
    """Raised when audio duration is zero, negative, or exceeds maximum limits."""


class ModelLoadError(ASRError):
    """Raised when loading or downloading the Whisper model fails."""


class ModelConfigurationError(ASRError):
    """Raised when model size, device, or compute type configuration is invalid."""


class TranscriptionError(ASRError):
    """Raised when speech-to-text inference fails during execution."""


class EmptyTranscriptionError(ASRError):
    """Raised when an audio file contains zero audible speech or fails to produce text."""


class UnsupportedRuntimeError(ASRError):
    """Raised when the requested compute device or runtime is unavailable on the host."""
