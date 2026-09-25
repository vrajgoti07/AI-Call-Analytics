"""
AI Call Analytics — Automatic Speech Recognition (ASR) Module.

Provides fast, robust speech-to-text inference powered by faster-whisper:
- Ingestion of Phase 2 standardized 16kHz mono PCM16 WAV audio
- Word and segment-level timestamps and alignments
- Dynamic language detection and confidence scoring
- Thread-safe model caching and reuse via WhisperModelManager
- Anomaly, hallucination loop, and timestamp monotonicity diagnostics
- Real-time factor (RTF) performance measurement
- Future-proof data contract ready for Phase 4 Speaker Diarization
"""

from ai_service.asr.config import WhisperConfig, DEFAULT_WHISPER_CONFIG
from ai_service.asr.exceptions import (
    ASRError,
    AudioNotFoundError,
    EmptyTranscriptionError,
    InvalidAudioStreamError,
    InvalidDurationError,
    InvalidPreprocessedAudioError,
    ModelConfigurationError,
    ModelLoadError,
    TranscriptionError,
    UnsupportedRuntimeError,
)
from ai_service.asr.model_manager import WhisperModelManager
from ai_service.asr.schema import (
    TranscriptSegment,
    TranscriptionMetadata,
    TranscriptionResult,
    WordTiming,
)
from ai_service.asr.transcriber import WhisperTranscriber
from ai_service.asr.validator import (
    detect_transcription_anomalies,
    validate_asr_input,
    validate_timestamps,
)

__all__ = [
    "WhisperConfig",
    "DEFAULT_WHISPER_CONFIG",
    "WhisperTranscriber",
    "WhisperModelManager",
    "TranscriptionResult",
    "TranscriptSegment",
    "WordTiming",
    "TranscriptionMetadata",
    "validate_asr_input",
    "validate_timestamps",
    "detect_transcription_anomalies",
    "ASRError",
    "AudioNotFoundError",
    "InvalidPreprocessedAudioError",
    "ModelLoadError",
    "ModelConfigurationError",
    "TranscriptionError",
    "EmptyTranscriptionError",
    "UnsupportedRuntimeError",
]
