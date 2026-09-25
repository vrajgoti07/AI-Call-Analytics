"""
AI Call Analytics — Sentiment Analysis Schemas.

Defines dataclasses for turn-level sentiment, per-speaker aggregated sentiment,
temporal timeline tracking, and call-level summary sentiment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TurnSentiment:
    """Sentiment classification for an individual conversational turn."""

    turn_id: int
    speaker: str
    start: float
    end: float
    text: str
    label: str  # 'POSITIVE', 'NEUTRAL', 'NEGATIVE'
    score: float  # Confidence probability in [0.0, 1.0]

    def to_dict(self) -> dict[str, Any]:
        """Serialize turn sentiment to dictionary."""
        return {
            "turn_id": self.turn_id,
            "speaker": self.speaker,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "label": self.label,
            "score": round(self.score, 4),
        }


@dataclass(frozen=True)
class SpeakerSentiment:
    """Aggregated sentiment telemetry for a distinct conversational participant."""

    speaker: str
    positive_count: int
    neutral_count: int
    negative_count: int
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    average_score: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize speaker sentiment summary to dictionary."""
        return {
            "speaker": self.speaker,
            "positive_count": self.positive_count,
            "neutral_count": self.neutral_count,
            "negative_count": self.negative_count,
            "positive_ratio": round(self.positive_ratio, 3),
            "neutral_ratio": round(self.neutral_ratio, 3),
            "negative_ratio": round(self.negative_ratio, 3),
            "average_score": round(self.average_score, 4),
        }


@dataclass(frozen=True)
class SentimentTimelinePoint:
    """Chronological point for sentiment trajectory visualization."""

    timestamp: float
    turn_id: int
    speaker: str
    label: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize timeline point to dictionary."""
        return {
            "timestamp": round(self.timestamp, 3),
            "turn_id": self.turn_id,
            "speaker": self.speaker,
            "label": self.label,
            "score": round(self.score, 4),
        }


@dataclass
class CallSentiment:
    """Complete call-level sentiment evaluation with supporting metrics and timeline."""

    label: str  # 'POSITIVE', 'NEUTRAL', 'NEGATIVE'
    score: float  # Confidence probability in [0.0, 1.0]
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    turns: list[TurnSentiment] = field(default_factory=list)
    speaker_sentiments: dict[str, SpeakerSentiment] = field(default_factory=dict)
    timeline: list[SentimentTimelinePoint] = field(default_factory=list)
    aggregation_method: str = "duration_and_polarity_weighted"

    def to_dict(self) -> dict[str, Any]:
        """Serialize call sentiment to dictionary."""
        return {
            "label": self.label,
            "score": round(self.score, 4),
            "positive_ratio": round(self.positive_ratio, 3),
            "neutral_ratio": round(self.neutral_ratio, 3),
            "negative_ratio": round(self.negative_ratio, 3),
            "turns": [t.to_dict() for t in self.turns],
            "speaker_sentiments": {k: v.to_dict() for k, v in self.speaker_sentiments.items()},
            "timeline": [p.to_dict() for p in self.timeline],
            "aggregation_method": self.aggregation_method,
        }
