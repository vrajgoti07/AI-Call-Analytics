"""
AI Call Analytics — Speaker Diarization & Alignment Schemas.

Defines strongly typed dataclasses representing diarization segments,
speaker conversational statistics, speaker turns, and the combined
speaker-attributed transcript.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DiarizationSegment:
    """
    Individual raw acoustic speaker activity segment from pyannote.
    Represents contiguous speech by a single speaker.
    """

    speaker: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        """Segment duration in seconds."""
        return round(max(0.0, self.end - self.start), 4)

    def to_dict(self) -> dict[str, Any]:
        """Serialize segment to dictionary."""
        return {
            "speaker": self.speaker,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": self.duration,
        }


@dataclass(frozen=True)
class SpeakerStats:
    """Conversational activity metrics for an individual speaker."""

    speaker: str
    total_speaking_time: float
    segment_count: int
    speech_percentage: float  # Percentage of total call conversation speech time

    def to_dict(self) -> dict[str, Any]:
        """Serialize speaker statistics to dictionary."""
        return {
            "speaker": self.speaker,
            "total_speaking_time": round(self.total_speaking_time, 3),
            "segment_count": self.segment_count,
            "speech_percentage": round(self.speech_percentage, 2),
        }


@dataclass
class SpeakerTurn:
    """
    A continuous conversational turn attributed to a specific speaker.
    Formed by aligning Whisper ASR transcript segments with diarization boundaries
    and consolidating contiguous speech from the same speaker.
    """

    turn_id: int
    speaker: str
    start: float
    end: float
    text: str
    source_segment_ids: list[int] = field(default_factory=list)
    words: list[dict[str, Any]] = field(default_factory=list)
    overlap_score: float = 1.0  # Proportion of Whisper segment overlapping with speaker segment
    warning: str | None = None

    @property
    def duration(self) -> float:
        """Turn duration in seconds."""
        return round(max(0.0, self.end - self.start), 3)

    def to_dict(self) -> dict[str, Any]:
        """Serialize speaker turn to dictionary."""
        return {
            "turn_id": self.turn_id,
            "speaker": self.speaker,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": self.duration,
            "text": self.text,
            "source_segment_ids": list(self.source_segment_ids),
            "words": list(self.words),
            "overlap_score": round(self.overlap_score, 3),
            "warning": self.warning,
        }


@dataclass(frozen=True)
class DiarizationMetadata:
    """Technical metadata for the pyannote model execution."""

    model_name: str
    device: str
    min_speakers: int | None
    max_speakers: int | None
    audio_path: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to dictionary."""
        return asdict(self)


@dataclass
class DiarizationResult:
    """
    Complete output of the raw speaker diarization stage.
    Decoupled from raw pyannote library objects.
    """

    audio_path: str
    audio_duration: float
    speaker_segments: list[DiarizationSegment] = field(default_factory=list)
    speakers: list[str] = field(default_factory=list)
    speaker_stats: dict[str, SpeakerStats] = field(default_factory=dict)
    speech_duration: float = 0.0
    overlap_duration: float = 0.0
    overlap_detected: bool = False
    processing_time_seconds: float = 0.0
    real_time_factor: float = 0.0
    metadata: DiarizationMetadata | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize diarization result to dictionary."""
        return {
            "audio_path": self.audio_path,
            "audio_duration": round(self.audio_duration, 3),
            "speakers": list(self.speakers),
            "speaker_segments": [s.to_dict() for s in self.speaker_segments],
            "speaker_stats": {k: v.to_dict() for k, v in self.speaker_stats.items()},
            "speech_duration": round(self.speech_duration, 3),
            "overlap_duration": round(self.overlap_duration, 3),
            "overlap_detected": self.overlap_detected,
            "processing_time_seconds": round(self.processing_time_seconds, 3),
            "real_time_factor": round(self.real_time_factor, 3),
            "warnings": list(self.warnings),
            "metadata": self.metadata.to_dict() if self.metadata else None,
        }


@dataclass
class SpeakerAttributedTranscript:
    """
    Unified Phase 3 (Whisper ASR) + Phase 4 (Speaker Diarization) output contract.
    Serves as the structured conversational source of truth for downstream NLP,
    sentiment, intent, theme discovery, and escalation risk analysis.
    """

    full_text: str  # Formatted multi-line dialogue: 'SPEAKER_00: Hello...\nSPEAKER_01: ...'
    turns: list[SpeakerTurn] = field(default_factory=list)
    speakers: list[str] = field(default_factory=list)
    speaker_stats: dict[str, SpeakerStats] = field(default_factory=dict)
    total_turns: int = 0
    audio_duration: float = 0.0
    speech_duration: float = 0.0
    overlap_duration: float = 0.0
    overlap_detected: bool = False
    alignment_time_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    transcription_metadata: dict[str, Any] = field(default_factory=dict)
    diarization_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete speaker-attributed transcript to dictionary."""
        return {
            "full_text": self.full_text,
            "turns": [t.to_dict() for t in self.turns],
            "speakers": list(self.speakers),
            "speaker_stats": {k: v.to_dict() for k, v in self.speaker_stats.items()},
            "total_turns": self.total_turns,
            "audio_duration": round(self.audio_duration, 3),
            "speech_duration": round(self.speech_duration, 3),
            "overlap_duration": round(self.overlap_duration, 3),
            "overlap_detected": self.overlap_detected,
            "alignment_time_seconds": round(self.alignment_time_seconds, 3),
            "warnings": list(self.warnings),
            "transcription_metadata": self.transcription_metadata,
            "diarization_metadata": self.diarization_metadata,
        }
