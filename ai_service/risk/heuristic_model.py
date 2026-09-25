"""
AI Call Analytics — Heuristic Escalation Model.

Implements the transparent, configurable, multi-factor rule-based scoring engine
specified in Phase 8 (Section 30, 31, 56) for zero-label environments.
"""

from __future__ import annotations

import logging
from typing import Any

from ai_service.risk.config import EscalationConfig
from ai_service.risk.schema import (
    EscalationFactor,
    EscalationFeatures,
    EscalationPrediction,
    EscalationRiskLevel,
    TemporalRiskPoint,
)

logger = logging.getLogger(__name__)


class HeuristicEscalationModel:
    """
    Transparent weighted risk scoring model combining sentiment, trajectory,
    explicit escalation keywords, friction intents, acoustic overlap, and repetition.
    """

    def __init__(self, config: EscalationConfig | None = None) -> None:
        self.config = config or EscalationConfig()

    def predict(
        self,
        call_id: str,
        features: EscalationFeatures,
        temporal_risk: list[TemporalRiskPoint] | None = None,
    ) -> EscalationPrediction:
        """
        Compute escalation risk score, risk tier, and factor contributions.

        Args:
            call_id: Identifier of the call being analyzed.
            features: Engineered feature snapshot for the call.
            temporal_risk: Optional temporal progression points.

        Returns:
            Standardized `EscalationPrediction` result.
        """
        # 1. Negative Sentiment Sub-score (0.0 to 1.0)
        s_neg = min(
            1.0,
            0.6 * features.negative_sentiment_ratio
            + 0.4 * features.strong_negative_ratio,
        )

        # 2. Sentiment Trajectory Sub-score (0.0 to 1.0)
        # Negative slope = deteriorating sentiment; positive slope = resolution
        slope_penalty = max(0.0, -features.sentiment_slope)
        late_penalty = max(0.0, -features.late_sentiment_score)
        s_traj = min(1.0, 0.6 * slope_penalty + 0.4 * late_penalty)

        # 3. Escalation Keyword / Trigger Phrase Sub-score (0.0 to 1.0)
        # 1 keyword = 0.50, 2+ keywords = 1.0
        s_kw = min(1.0, features.escalation_keyword_count / 2.0)

        # 4. Problem Intent Sub-score (0.0 to 1.0)
        if features.is_problem_intent:
            s_intent = min(1.0, max(0.6, features.intent_confidence))
        else:
            s_intent = 0.0

        # 5. Acoustic / Conversational Friction Sub-score (0.0 to 1.0)
        overlap_term = min(1.0, features.overlap_ratio / 0.15) if features.overlap_ratio > 0 else 0.0
        turn_len_term = min(1.0, features.max_turn_duration / 60.0) if features.max_turn_duration > 0 else 0.0
        s_acoustic = 0.6 * overlap_term + 0.4 * turn_len_term

        # 6. Repetition Sub-score (0.0 to 1.0)
        s_rep = min(1.0, features.repetition_score / 0.35)

        # Compute weighted risk probability
        risk_prob = (
            self.config.weight_negative_sentiment * s_neg
            + self.config.weight_sentiment_trajectory * s_traj
            + self.config.weight_escalation_keywords * s_kw
            + self.config.weight_problem_intent * s_intent
            + self.config.weight_acoustic_friction * s_acoustic
            + self.config.weight_repetition * s_rep
        )

        # Clamp between 0.0 and 1.0
        risk_prob = max(0.0, min(1.0, risk_prob))
        risk_score = round(risk_prob * 100.0, 2)

        # Determine Risk Level Tier
        if risk_score >= self.config.high_threshold:
            risk_level = EscalationRiskLevel.HIGH
        elif risk_score >= self.config.low_threshold:
            risk_level = EscalationRiskLevel.MEDIUM
        else:
            risk_level = EscalationRiskLevel.LOW

        # Generate Factor Contributions for Explainability
        factors = self._build_factors(
            features=features,
            s_neg=s_neg,
            s_traj=s_traj,
            s_kw=s_kw,
            s_intent=s_intent,
            s_acoustic=s_acoustic,
            s_rep=s_rep,
        )

        return EscalationPrediction(
            call_id=call_id,
            model_type="heuristic",
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            feature_version=self.config.feature_schema_version,
            risk_score=risk_score,
            risk_probability=round(risk_prob, 4),
            risk_level=risk_level,
            threshold_version=self.config.threshold_version,
            top_factors=factors,
            explanation="",  # Will be populated by EscalationExplainer
            feature_snapshot=features.to_dict(),
            temporal_risk=temporal_risk or [],
            metadata={
                "sub_scores": {
                    "negative_sentiment": round(s_neg, 4),
                    "sentiment_trajectory": round(s_traj, 4),
                    "escalation_keywords": round(s_kw, 4),
                    "problem_intent": round(s_intent, 4),
                    "acoustic_friction": round(s_acoustic, 4),
                    "repetition": round(s_rep, 4),
                },
                "weights": {
                    "negative_sentiment": self.config.weight_negative_sentiment,
                    "sentiment_trajectory": self.config.weight_sentiment_trajectory,
                    "escalation_keywords": self.config.weight_escalation_keywords,
                    "problem_intent": self.config.weight_problem_intent,
                    "acoustic_friction": self.config.weight_acoustic_friction,
                    "repetition": self.config.weight_repetition,
                },
                "thresholds": {
                    "low": self.config.low_threshold,
                    "high": self.config.high_threshold,
                },
            },
        )

    def _build_factors(
        self,
        features: EscalationFeatures,
        s_neg: float,
        s_traj: float,
        s_kw: float,
        s_intent: float,
        s_acoustic: float,
        s_rep: float,
    ) -> list[EscalationFactor]:
        """Construct ranked list of explainable evidence factors."""
        raw_factors = [
            EscalationFactor(
                feature="escalation_keywords",
                value=float(features.escalation_keyword_count),
                contribution=round(self.config.weight_escalation_keywords * s_kw, 4),
                display_name="Explicit Escalation Keywords",
                description=f"Detected {features.escalation_keyword_count} escalation phrases (e.g., manager, supervisor, dispute)",
            ),
            EscalationFactor(
                feature="sentiment_trajectory",
                value=float(features.sentiment_slope),
                contribution=round(self.config.weight_sentiment_trajectory * s_traj, 4),
                display_name="Deteriorating Sentiment Trajectory",
                description=f"Sentiment slope of {features.sentiment_slope:+.2f} indicates worsening customer tone across conversational phases",
            ),
            EscalationFactor(
                feature="negative_sentiment",
                value=float(features.negative_sentiment_ratio),
                contribution=round(self.config.weight_negative_sentiment * s_neg, 4),
                display_name="Negative Sentiment Volume",
                description=f"{features.negative_sentiment_ratio * 100:.1f}% of turns were negative ({features.strong_negative_ratio * 100:.1f}% strongly negative)",
            ),
            EscalationFactor(
                feature="problem_intent",
                value=float(features.is_problem_intent),
                contribution=round(self.config.weight_problem_intent * s_intent, 4),
                display_name="Friction Banking Intent",
                description=f"Primary intent '{features.predicted_intent}' indicates account friction or system error",
            ),
            EscalationFactor(
                feature="acoustic_friction",
                value=float(features.overlap_ratio),
                contribution=round(self.config.weight_acoustic_friction * s_acoustic, 4),
                display_name="Conversational Overlap & Turn Monologues",
                description=f"Speech overlap ratio of {features.overlap_ratio * 100:.1f}% with max turn duration of {features.max_turn_duration:.1f}s",
            ),
            EscalationFactor(
                feature="repetition_score",
                value=float(features.repetition_score),
                contribution=round(self.config.weight_repetition * s_rep, 4),
                display_name="Conversational Repetition",
                description=f"Turn lexical overlap score of {features.repetition_score:.2f} suggests unresolved recurring requests",
            ),
        ]

        # Sort descending by contribution
        raw_factors.sort(key=lambda f: f.contribution, reverse=True)
        return raw_factors
