"""
AI Call Analytics — Speaker Diarization Exceptions.

Defines custom, descriptive exceptions for diarization model loading,
Hugging Face authentication, pipeline execution, segment validation,
and ASR-diarization temporal alignment.
"""

from __future__ import annotations


class DiarizationError(Exception):
    """Base exception for all speaker diarization operations."""


class DiarizationConfigurationError(DiarizationError):
    """Raised when diarization configuration or speaker constraints are invalid."""


class DiarizationModelLoadError(DiarizationError):
    """
    Raised when loading or downloading the pyannote pipeline fails.
    Common causes: missing HF_TOKEN, gated repository terms not accepted,
    or network/CUDA errors.
    """


class DiarizationInferenceError(DiarizationError):
    """Raised when pyannote pipeline inference fails during audio processing."""


class InvalidDiarizationOutputError(DiarizationError):
    """Raised when diarization segments violate temporal validity or monotonicity."""


class AlignmentError(DiarizationError):
    """Raised when aligning Whisper transcription segments to diarization fails."""


class NoSpeakersDetectedError(DiarizationError):
    """Raised when an audio recording produces zero detected speaker tracks."""


class InvalidPreprocessedAudioError(DiarizationError):
    """Raised when audio fails the Phase 2 contract (16kHz mono PCM16 WAV)."""
