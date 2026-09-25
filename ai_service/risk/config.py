"""
AI Call Analytics — Escalation Risk Configuration.

Defines hyperparameters, feature schema versioning, threshold policies,
and weight vectors for heuristic and supervised escalation risk detection.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

FEATURE_SCHEMA_VERSION: str = "v1"
THRESHOLD_VERSION: str = "v1.0"

# Explicit escalation trigger phrases (lowered for matching)
DEFAULT_ESCALATION_TRIGGER_PHRASES: list[str] = [
    "speak to a manager",
    "speak with a manager",
    "speak to your manager",
    "talk to a manager",
    "supervisor",
    "speak to a supervisor",
    "talk to a supervisor",
    "transfer me",
    "transfer to",
    "cancel my account",
    "close my account",
    "file a complaint",
    "make a complaint",
    "official complaint",
    "unacceptable",
    "ridiculous",
    "lawyer",
    "attorney",
    "legal action",
    "sue you",
    "fraud",
    "fraudulent",
    "waste of time",
    "terrible service",
    "horrible service",
    "escalate this",
    "escalation",
    "dispute this charge",
    "dispute the fee",
]

# Friction-inducing MInDS-14 banking intents
DEFAULT_PROBLEM_INTENTS: list[str] = [
    "freeze",
    "card_issues",
    "app_error",
    "direct_debit",
]


@dataclass
class EscalationConfig:
    """
    Configuration parameters for the Phase 8 Escalation Risk Detection pipeline.
    Supports environment variable overrides and reproducible execution.
    """

    model_type: str = field(
        default_factory=lambda: os.getenv("ESCALATION_MODEL_TYPE", "heuristic")
    )
    model_name: str = field(
        default_factory=lambda: os.getenv("ESCALATION_MODEL_NAME", "composite_weighted_heuristic_v1")
    )
    model_version: str = "1.0.0"
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    threshold_version: str = THRESHOLD_VERSION

    # Risk level decision thresholds (on 0.0 - 100.0 score scale)
    low_threshold: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_LOW_THRESHOLD", "35.0"))
    )
    high_threshold: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_HIGH_THRESHOLD", "65.0"))
    )

    # Heuristic component weights (sum to 1.0)
    weight_negative_sentiment: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_WEIGHT_NEGATIVE_SENTIMENT", "0.20"))
    )
    weight_sentiment_trajectory: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_WEIGHT_SENTIMENT_TRAJECTORY", "0.20"))
    )
    weight_escalation_keywords: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_WEIGHT_KEYWORDS", "0.25"))
    )
    weight_problem_intent: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_WEIGHT_PROBLEM_INTENT", "0.15"))
    )
    weight_acoustic_friction: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_WEIGHT_ACOUSTIC_FRICTION", "0.10"))
    )
    weight_repetition: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_WEIGHT_REPETITION", "0.10"))
    )

    # Thresholds for feature extraction
    strong_negative_sentiment_threshold: float = 0.75
    min_turns_for_trajectory: int = 3
    repetition_similarity_threshold: float = 0.75
    max_turn_duration_friction_seconds: float = 45.0
    speech_overlap_ratio_friction: float = 0.10

    # Trigger phrase dictionary
    trigger_phrases: list[str] = field(default_factory=lambda: list(DEFAULT_ESCALATION_TRIGGER_PHRASES))
    problem_intents: list[str] = field(default_factory=lambda: list(DEFAULT_PROBLEM_INTENTS))

    def __post_init__(self) -> None:
        """Validate weight normalization and threshold ordering."""
        total_weight = (
            self.weight_negative_sentiment
            + self.weight_sentiment_trajectory
            + self.weight_escalation_keywords
            + self.weight_problem_intent
            + self.weight_acoustic_friction
            + self.weight_repetition
        )
        if total_weight <= 0.0:
            raise ValueError(f"Total heuristic weight must be positive, got {total_weight}")

        # Normalize weights if they deviate slightly from 1.0
        if abs(total_weight - 1.0) > 1e-4:
            self.weight_negative_sentiment /= total_weight
            self.weight_sentiment_trajectory /= total_weight
            self.weight_escalation_keywords /= total_weight
            self.weight_problem_intent /= total_weight
            self.weight_acoustic_friction /= total_weight
            self.weight_repetition /= total_weight

        if self.low_threshold >= self.high_threshold:
            raise ValueError(
                f"low_threshold ({self.low_threshold}) must be strictly less than high_threshold ({self.high_threshold})"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration parameters."""
        return {
            "model_type": self.model_type,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "feature_schema_version": self.feature_schema_version,
            "threshold_version": self.threshold_version,
            "low_threshold": self.low_threshold,
            "high_threshold": self.high_threshold,
            "weights": {
                "negative_sentiment": round(self.weight_negative_sentiment, 4),
                "sentiment_trajectory": round(self.weight_sentiment_trajectory, 4),
                "escalation_keywords": round(self.weight_escalation_keywords, 4),
                "problem_intent": round(self.weight_problem_intent, 4),
                "acoustic_friction": round(self.weight_acoustic_friction, 4),
                "repetition": round(self.weight_repetition, 4),
            },
            "problem_intents": list(self.problem_intents),
        }
