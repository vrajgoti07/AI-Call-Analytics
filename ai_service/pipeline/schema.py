"""
AI Call Analytics — NLP Pipeline Unified Schemas.

Defines the unified output contracts, status enums, speaker analytics summaries,
and metadata tracking for the Phase 5 conversational NLP layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ai_service.intent.schema import IntentPrediction
from ai_service.ner.schema import NERResult
from ai_service.sentiment.schema import CallSentiment, SpeakerSentiment


class ComponentStatus(str, Enum):
    """Execution status for individual NLP pipeline components."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    SKIPPED = "SKIPPED"


class AnalysisStatus(str, Enum):
    """Aggregate lifecycle execution status for the entire NLP analysis."""

    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class ComponentMetadata:
    """Telemetry and execution trace for an individual NLP component."""

    status: str
    model_name: str | None = None
    processing_time_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize component metadata to dictionary."""
        return {
            "status": self.status,
            "model_name": self.model_name,
            "processing_time_seconds": round(self.processing_time_seconds, 4),
            "error": self.error,
        }


@dataclass
class SpeakerAnalysisSummary:
    """
    Combined conversational, sentiment, and entity telemetry for an individual speaker.
    Links Phase 4 acoustic stats with Phase 5 NLP attributes.
    """

    speaker: str
    speaking_time: float
    speech_percentage: float
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    positive_turns: int = 0
    neutral_turns: int = 0
    negative_turns: int = 0
    negative_turn_ratio: float = 0.0
    entity_count: int = 0
    entities_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize speaker analysis summary to dictionary."""
        return {
            "speaker": self.speaker,
            "speaking_time": round(self.speaking_time, 3),
            "speech_percentage": round(self.speech_percentage, 2),
            "sentiment_label": self.sentiment_label,
            "sentiment_score": round(self.sentiment_score, 4) if self.sentiment_score is not None else None,
            "positive_turns": self.positive_turns,
            "neutral_turns": self.neutral_turns,
            "negative_turns": self.negative_turns,
            "negative_turn_ratio": round(self.negative_turn_ratio, 3),
            "entity_count": self.entity_count,
            "entities_by_type": dict(self.entities_by_type),
        }


@dataclass
class NLPAnalysisMetadata:
    """Comprehensive technical execution and audit metadata for Phase 5."""

    language: str
    is_language_supported: bool
    status: str
    processing_time_seconds: float
    component_statuses: dict[str, ComponentMetadata] = field(default_factory=dict)
    audio_duration: float = 0.0
    total_turns: int = 0
    total_speakers: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to dictionary."""
        return {
            "language": self.language,
            "is_language_supported": self.is_language_supported,
            "status": self.status,
            "processing_time_seconds": round(self.processing_time_seconds, 4),
            "component_statuses": {k: v.to_dict() for k, v in self.component_statuses.items()},
            "audio_duration": round(self.audio_duration, 3),
            "total_turns": self.total_turns,
            "total_speakers": self.total_speakers,
            "warnings": list(self.warnings),
        }


@dataclass
class CallNLPAnalysis:
    """
    Standardized Phase 5 NLP Output Contract (Step 3).

    Consolidates sentiment analysis, intent classification, named entity recognition,
    and cross-speaker metrics into a unified result consumable by later phases
    (Theme Discovery, Embeddings, Escalation Risk).
    """

    sentiment: CallSentiment | None = None
    intent: IntentPrediction | None = None
    entities: NERResult | None = None
    speaker_analysis: dict[str, SpeakerAnalysisSummary] = field(default_factory=dict)
    metadata: NLPAnalysisMetadata | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete CallNLPAnalysis object into a JSON-compatible dictionary."""
        return {
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
            "intent": self.intent.to_dict() if self.intent else None,
            "entities": self.entities.to_dict() if self.entities else None,
            "speaker_analysis": {k: v.to_dict() for k, v in self.speaker_analysis.items()},
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "warnings": list(self.warnings),
        }
