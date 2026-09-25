"""
AI Call Analytics — Escalation Risk Schemas.

Defines strongly-typed dataclasses and enums representing engineered risk features,
individual risk factor contributions, temporal risk segments, and final prediction contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ai_service.risk.config import FEATURE_SCHEMA_VERSION, THRESHOLD_VERSION


class EscalationRiskLevel(str, Enum):
    """Categorical risk tiers for operational routing and reporting."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class EscalationFactor:
    """
    Individual evidence factor contributing to the overall escalation score.
    Used for interpretable, evidence-based explainability.
    """

    feature: str
    value: float
    contribution: float  # Normalized impact score in [0.0, 1.0]
    display_name: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize factor to dictionary."""
        return {
            "feature": self.feature,
            "value": round(self.value, 4),
            "contribution": round(self.contribution, 4),
            "display_name": self.display_name,
            "description": self.description,
        }


@dataclass(frozen=True)
class TemporalRiskPoint:
    """Risk telemetry across a specific conversational phase."""

    segment: str  # 'early', 'middle', 'late'
    turn_start: int
    turn_end: int
    sentiment_score: float  # Average signed polarity in [-1.0, 1.0]
    segment_risk_score: float  # Score in [0.0, 100.0]

    def to_dict(self) -> dict[str, Any]:
        """Serialize temporal risk point to dictionary."""
        return {
            "segment": self.segment,
            "turn_start": self.turn_start,
            "turn_end": self.turn_end,
            "sentiment_score": round(self.sentiment_score, 4),
            "segment_risk_score": round(self.segment_risk_score, 2),
        }


@dataclass
class EscalationFeatures:
    """
    Unified feature vector representation for a customer call.
    Aggregates signals from Phase 4 (Diarization), Phase 5 (Sentiment, Intent, NER),
    and Phase 7 (Theme Discovery).

    Guarantees strict schema versioning ('v1') for supervised models and heuristic scoring.
    """

    # 1. Acoustic & Diarization Features (Phase 4)
    call_duration: float = 0.0
    turn_count: int = 0
    speaker_count: int = 0
    speech_duration: float = 0.0
    overlap_duration: float = 0.0
    overlap_ratio: float = 0.0
    avg_turn_duration: float = 0.0
    max_turn_duration: float = 0.0
    speaker_switch_count: int = 0

    # 2. Sentiment Features (Phase 5)
    negative_sentiment_ratio: float = 0.0
    strong_negative_ratio: float = 0.0
    positive_sentiment_ratio: float = 0.0
    sentiment_volatility: float = 0.0
    min_sentiment_score: float = 0.0
    final_turn_sentiment: float = 0.0

    # 3. Sentiment Trajectory Features (Phase 5)
    early_sentiment_score: float = 0.0
    middle_sentiment_score: float = 0.0
    late_sentiment_score: float = 0.0
    sentiment_slope: float = 0.0

    # 4. Intent & Topic Features (Phase 5)
    is_problem_intent: int = 0  # 1 if friction/problem intent, 0 otherwise
    intent_confidence: float = 0.0
    predicted_intent: str = "unknown"

    # 5. Repetition & Escalation Keywords
    escalation_keyword_count: int = 0
    repetition_score: float = 0.0

    # 6. Theme Features (Phase 7)
    theme_count: int = 0
    has_problem_theme: int = 0

    # 7. Safe NER Counts (Phase 5 - PII-neutral)
    entity_count: int = 0
    account_number_count: int = 0
    money_entity_count: int = 0

    # Schema identifier
    schema_version: str = FEATURE_SCHEMA_VERSION

    @classmethod
    def feature_names(cls) -> list[str]:
        """Ordered list of numerical feature names for model input."""
        return [
            "call_duration",
            "turn_count",
            "speaker_count",
            "speech_duration",
            "overlap_duration",
            "overlap_ratio",
            "avg_turn_duration",
            "max_turn_duration",
            "speaker_switch_count",
            "negative_sentiment_ratio",
            "strong_negative_ratio",
            "positive_sentiment_ratio",
            "sentiment_volatility",
            "min_sentiment_score",
            "final_turn_sentiment",
            "early_sentiment_score",
            "middle_sentiment_score",
            "late_sentiment_score",
            "sentiment_slope",
            "is_problem_intent",
            "intent_confidence",
            "escalation_keyword_count",
            "repetition_score",
            "theme_count",
            "has_problem_theme",
            "entity_count",
            "account_number_count",
            "money_entity_count",
        ]

    def to_feature_vector(self) -> list[float]:
        """
        Export numerical features in the exact deterministic order required by ML models.
        Matches `feature_names()` index-for-index.
        """
        return [
            float(self.call_duration),
            float(self.turn_count),
            float(self.speaker_count),
            float(self.speech_duration),
            float(self.overlap_duration),
            float(self.overlap_ratio),
            float(self.avg_turn_duration),
            float(self.max_turn_duration),
            float(self.speaker_switch_count),
            float(self.negative_sentiment_ratio),
            float(self.strong_negative_ratio),
            float(self.positive_sentiment_ratio),
            float(self.sentiment_volatility),
            float(self.min_sentiment_score),
            float(self.final_turn_sentiment),
            float(self.early_sentiment_score),
            float(self.middle_sentiment_score),
            float(self.late_sentiment_score),
            float(self.sentiment_slope),
            float(self.is_problem_intent),
            float(self.intent_confidence),
            float(self.escalation_keyword_count),
            float(self.repetition_score),
            float(self.theme_count),
            float(self.has_problem_theme),
            float(self.entity_count),
            float(self.account_number_count),
            float(self.money_entity_count),
        ]

    def to_dict(self) -> dict[str, Any]:
        """
        Export a clean, PII-safe dictionary snapshot of all feature values.
        Suitable for audit trails and database persistence.
        """
        d = asdict(self)
        # Round floating point values for clean representation
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, 4)
        return d


@dataclass
class EscalationPrediction:
    """
    Standardized Output Contract for Escalation Risk Analysis.
    Delivers risk scoring, categorical tiering, explainability factors,
    and temporal trajectory telemetry.
    """

    call_id: str
    model_type: str  # 'heuristic' or 'supervised'
    model_name: str
    model_version: str
    feature_version: str
    risk_score: float  # Normalized scale: 0.0 (minimum) to 100.0 (maximum)
    risk_probability: float  # Probability scale: 0.0 to 1.0
    risk_level: EscalationRiskLevel
    threshold_version: str
    top_factors: list[EscalationFactor] = field(default_factory=list)
    explanation: str = ""
    feature_snapshot: dict[str, Any] = field(default_factory=dict)
    temporal_risk: list[TemporalRiskPoint] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete prediction to JSON-compatible dictionary."""
        return {
            "call_id": self.call_id,
            "model_type": self.model_type,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "risk_score": round(self.risk_score, 2),
            "risk_probability": round(self.risk_probability, 4),
            "risk_level": self.risk_level.value,
            "threshold_version": self.threshold_version,
            "top_factors": [f.to_dict() for f in self.top_factors],
            "explanation": self.explanation,
            "feature_snapshot": self.feature_snapshot,
            "temporal_risk": [t.to_dict() for t in self.temporal_risk],
            "processing_time_seconds": round(self.processing_time_seconds, 4),
            "metadata": self.metadata,
        }
