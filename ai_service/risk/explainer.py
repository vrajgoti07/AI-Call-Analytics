"""
AI Call Analytics — Escalation Explainer.

Generates interpretable, evidence-based human-readable explanations and
factor contribution rankings for escalation predictions. Strictly avoids
subjective psychological claims, adhering to concrete observational metrics.
"""

from __future__ import annotations

import logging

from ai_service.risk.schema import EscalationPrediction, EscalationRiskLevel

logger = logging.getLogger(__name__)


class EscalationExplainer:
    """
    Synthesizes clear, auditable explanations from feature snapshots and factor rankings.
    """

    @classmethod
    def explain(cls, prediction: EscalationPrediction) -> str:
        """
        Generate a human-readable evidence summary for an escalation prediction.

        Args:
            prediction: Complete EscalationPrediction object.

        Returns:
            Structured multi-line narrative explanation.
        """
        level = prediction.risk_level
        score = prediction.risk_score
        factors = prediction.top_factors
        snapshot = prediction.feature_snapshot

        if level == EscalationRiskLevel.HIGH:
            intro = f"Escalation risk is HIGH (score {score:.1f}/100). Concrete friction signals were observed:"
        elif level == EscalationRiskLevel.MEDIUM:
            intro = f"Escalation risk is MODERATE (score {score:.1f}/100). The call contains emerging concern signals:"
        else:
            intro = f"Escalation risk is LOW (score {score:.1f}/100). Interaction exhibited stable conversational dynamics:"

        bullet_points: list[str] = []

        # 1. Escalation Keywords
        kw_count = snapshot.get("escalation_keyword_count", 0)
        if kw_count > 0:
            bullet_points.append(
                f"- Detected {kw_count} explicit escalation phrase(s) (e.g., manager, supervisor, dispute)."
            )

        # 2. Sentiment Trajectory & Negative Proportion
        neg_ratio = snapshot.get("negative_sentiment_ratio", 0.0)
        slope = snapshot.get("sentiment_slope", 0.0)
        strong_neg = snapshot.get("strong_negative_ratio", 0.0)

        if neg_ratio >= 0.40:
            desc = f"- High negative sentiment volume: {neg_ratio * 100:.1f}% of turns were negative"
            if strong_neg > 0:
                desc += f" ({strong_neg * 100:.1f}% strongly negative)."
            else:
                desc += "."
            bullet_points.append(desc)
        elif neg_ratio < 0.20 and level == EscalationRiskLevel.LOW:
            bullet_points.append(f"- Low negative sentiment: only {neg_ratio * 100:.1f}% of turns were classified negative.")

        if slope <= -0.20:
            bullet_points.append(
                f"- Worsening conversational trajectory: sentiment slope of {slope:+.2f} indicates deteriorating customer tone across turns."
            )
        elif slope >= 0.20 and level != EscalationRiskLevel.HIGH:
            bullet_points.append(
                f"- Resolving trajectory: positive sentiment slope ({slope:+.2f}) indicates constructive tone recovery."
            )

        # 3. Intent Friction
        is_problem = snapshot.get("is_problem_intent", 0)
        intent_name = snapshot.get("predicted_intent", "unknown")
        if is_problem:
            bullet_points.append(
                f"- Problem-related banking topic: inquiry classified as '{intent_name}' (associated with account friction or transaction blocks)."
            )

        # 4. Conversational Dynamics (overlap & repetition)
        overlap = snapshot.get("overlap_ratio", 0.0)
        max_turn = snapshot.get("max_turn_duration", 0.0)
        if overlap >= 0.10:
            bullet_points.append(
                f"- Elevated speech overlap: {overlap * 100:.1f}% of speech duration involved simultaneous speaking/interruption."
            )
        if max_turn >= 45.0:
            bullet_points.append(
                f"- Extended monologue: longest continuous speaker turn lasted {max_turn:.1f}s."
            )

        rep_score = snapshot.get("repetition_score", 0.0)
        if rep_score >= 0.35:
            bullet_points.append(
                f"- High conversational repetition: {rep_score * 100:.1f}% turn-to-turn lexical recurrence suggests recurring unaddressed questions."
            )

        # If no specific bullets triggered, summarize from top factors
        if not bullet_points and factors:
            for f in factors[:3]:
                if f.contribution > 0.05:
                    bullet_points.append(f"- {f.display_name}: {f.description}")

        if not bullet_points:
            bullet_points.append("- No acute friction or escalation triggers detected during this interaction.")

        explanation = intro + "\n" + "\n".join(bullet_points)
        return explanation
