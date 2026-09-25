"""
AI Call Analytics — ASR Schema & Contracts.

Defines strongly typed dataclasses representing speech-to-text outputs:
word-level timings, segment-level transcripts, language detection telemetry,
processing performance metrics, and the full transcription contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class WordTiming:
    """Word-level alignment timestamp and acoustic probability."""

    word: str
    start: float
    end: float
    probability: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize word timing to dictionary."""
        return asdict(self)


@dataclass
class TranscriptSegment:
    """
    Individual conversational speech segment with timestamps and confidence telemetry.

    Future Diarization Contract (Step 30):
    Includes optional 'speaker' attribute so Phase 4 (Speaker Diarization)
    can annotate speaker turns without breaking the data schema.
    """

    id: int
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None
    words: list[WordTiming] = field(default_factory=list)
    speaker: str | None = None  # Populated in Phase 4 Diarization

    def __init__(
        self,
        id: int | None = None,
        start: float = 0.0,
        end: float = 0.0,
        text: str = "",
        avg_logprob: float | None = None,
        no_speech_prob: float | None = None,
        compression_ratio: float | None = None,
        words: list[WordTiming] | None = None,
        speaker: str | None = None,
        segment_id: int | None = None,
    ) -> None:
        self.id = segment_id if segment_id is not None else (id if id is not None else 0)
        self.start = start
        self.end = end
        self.text = text
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob
        self.compression_ratio = compression_ratio
        self.words = words if words is not None else []
        self.speaker = speaker

    @property
    def segment_id(self) -> int:
        """Alias for id conforming to segment_id naming."""
        return self.id

    @property
    def duration(self) -> float:
        """Segment duration in seconds."""
        return round(self.end - self.start, 4)

    def to_dict(self) -> dict[str, Any]:
        """Serialize segment to dictionary."""
        return {
            "id": self.id,
            "segment_id": self.id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": self.duration,
            "text": self.text,
            "avg_logprob": round(self.avg_logprob, 4) if self.avg_logprob is not None else None,
            "no_speech_prob": round(self.no_speech_prob, 4) if self.no_speech_prob is not None else None,
            "compression_ratio": round(self.compression_ratio, 3) if self.compression_ratio is not None else None,
            "speaker": self.speaker,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass(frozen=True)
class TranscriptionMetadata:
    """Technical metadata regarding the model, compute runtime, and parameters."""

    model_name: str
    device: str
    compute_type: str
    beam_size: int
    vad_filter: bool
    audio_path: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to dictionary."""
        return asdict(self)


@dataclass
class TranscriptionResult:
    """
    Standardized ASR Output Contract.
    Consumed by downstream NLP, Diarization, Sentiment, and Analytics modules.
    """

    text: str
    language: str
    language_probability: float
    duration_seconds: float
    processing_time_seconds: float
    real_time_factor: float
    segments: list[TranscriptSegment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: TranscriptionMetadata | None = None

    @property
    def audio_duration(self) -> float:
        """Alias for duration_seconds matching call analytics telemetry."""
        return self.duration_seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete transcription result to dictionary."""
        return {
            "text": self.text,
            "language": self.language,
            "language_probability": round(self.language_probability, 4),
            "duration_seconds": round(self.duration_seconds, 3),
            "audio_duration": round(self.duration_seconds, 3),
            "processing_time_seconds": round(self.processing_time_seconds, 3),
            "real_time_factor": round(self.real_time_factor, 3),
            "segments": [s.to_dict() for s in self.segments],
            "warnings": list(self.warnings),
            "metadata": self.metadata.to_dict() if self.metadata else None,
        }
