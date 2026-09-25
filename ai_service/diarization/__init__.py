"""
AI Call Analytics — Speaker Diarization Module (Phase 4).

Provides acoustic speaker diarization powered by pyannote.audio and temporal
alignment with Phase 3 Whisper speech-to-text transcripts:
- Standardized 16kHz mono PCM16 WAV audio contract enforcement
- Thread-safe singleton model cache (DiarizationModelManager)
- Dynamic and bounded speaker identification (SPEAKER_00, SPEAKER_01, etc.)
- Multi-speaker overlapping speech detection and interruption measurement
- Conversational speaker statistics (speaking times, turn counts, share percentages)
- Temporal overlap alignment with cross-speaker splitting and dominant assignment
- Structured conversational output (SpeakerTurn and SpeakerAttributedTranscript)
"""

from ai_service.diarization.aligner import TranscriptAligner
from ai_service.diarization.config import (
    DEFAULT_DIARIZATION_CONFIG,
    DiarizationConfig,
)
from ai_service.diarization.engine import PyannoteDiarizer
from ai_service.diarization.exceptions import (
    AlignmentError,
    DiarizationConfigurationError,
    DiarizationError,
    DiarizationInferenceError,
    DiarizationModelLoadError,
    InvalidDiarizationOutputError,
    InvalidPreprocessedAudioError,
    NoSpeakersDetectedError,
)
from ai_service.diarization.model_manager import DiarizationModelManager
from ai_service.diarization.schema import (
    DiarizationMetadata,
    DiarizationResult,
    DiarizationSegment,
    SpeakerAttributedTranscript,
    SpeakerStats,
    SpeakerTurn,
)
from ai_service.diarization.validator import (
    calculate_speaker_stats,
    compute_overlap_duration,
    validate_diarization_audio,
    validate_diarization_segments,
)

__all__ = [
    # Engine & Alignment
    "PyannoteDiarizer",
    "TranscriptAligner",
    "DiarizationModelManager",
    # Configuration
    "DiarizationConfig",
    "DEFAULT_DIARIZATION_CONFIG",
    # Data Contracts & Schemas
    "DiarizationSegment",
    "SpeakerStats",
    "SpeakerTurn",
    "DiarizationMetadata",
    "DiarizationResult",
    "SpeakerAttributedTranscript",
    # Validation & Diagnostics
    "validate_diarization_audio",
    "validate_diarization_segments",
    "compute_overlap_duration",
    "calculate_speaker_stats",
    # Exceptions
    "DiarizationError",
    "DiarizationConfigurationError",
    "DiarizationModelLoadError",
    "DiarizationInferenceError",
    "InvalidDiarizationOutputError",
    "AlignmentError",
    "NoSpeakersDetectedError",
    "InvalidPreprocessedAudioError",
]
