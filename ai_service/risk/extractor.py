"""
AI Call Analytics — Escalation Feature Extractor.

Extracts multi-modal conversational signals across Phase 4 (Diarization),
Phase 5 (Sentiment, Intent, NER), and Phase 7 (Themes) into a strongly-typed
feature snapshot for escalation risk modeling.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

import numpy as np

from ai_service.diarization.schema import SpeakerAttributedTranscript, SpeakerTurn
from ai_service.intent.schema import IntentPrediction
from ai_service.ner.schema import NERResult
from ai_service.risk.config import EscalationConfig
from ai_service.risk.exceptions import FeatureExtractionError
from ai_service.risk.schema import EscalationFeatures, TemporalRiskPoint

logger = logging.getLogger(__name__)


class EscalationFeatureExtractor:
    """
    Extracts acoustic, sentiment, trajectory, intent, repetition, and theme signals
    from upstream pipeline outputs into an `EscalationFeatures` dataclass.
    """

    def __init__(self, config: EscalationConfig | None = None) -> None:
        self.config = config or EscalationConfig()

    def extract(
        self,
        call_id: str,
        transcript: SpeakerAttributedTranscript | None = None,
        sentiment: Any | None = None,
        intent: IntentPrediction | None = None,
        entities: NERResult | None = None,
        themes: list[dict[str, Any]] | None = None,
    ) -> tuple[EscalationFeatures, list[TemporalRiskPoint]]:
        """
        Extract complete feature snapshot and temporal progression telemetry.

        Args:
            call_id: Unique call identifier.
            transcript: Speaker-attributed transcript from Phase 4.
            sentiment: CallSentiment object or dictionary from Phase 5.
            intent: IntentPrediction from Phase 5.
            entities: NERResult from Phase 5.
            themes: List of theme records or dictionaries from Phase 7.

        Returns:
            Tuple of (EscalationFeatures, list[TemporalRiskPoint]).
        """
        try:
            features = EscalationFeatures()

            # 1. Acoustic & Diarization Features
            turns = self._extract_acoustic_features(transcript, features)

            # 2. Sentiment & Trajectory Features
            temporal_points = self._extract_sentiment_features(sentiment, turns, features)

            # 3. Intent & Topic Features
            self._extract_intent_features(intent, features)

            # 4. Escalation Trigger Phrases & Repetition
            self._extract_repetition_and_keywords(turns, features)

            # 5. Theme Features (Phase 7)
            self._extract_theme_features(themes, features)

            # 6. Safe NER Features (Phase 5 - PII safe)
            self._extract_ner_features(entities, features)

            logger.debug(
                "Extracted escalation features for call %s: duration=%.1fs, turns=%d, neg_ratio=%.2f, slope=%.2f, kw_count=%d",
                call_id,
                features.call_duration,
                features.turn_count,
                features.negative_sentiment_ratio,
                features.sentiment_slope,
                features.escalation_keyword_count,
            )

            return features, temporal_points

        except Exception as exc:
            logger.error("Failed to extract escalation features for call %s: %s", call_id, exc)
            raise FeatureExtractionError(
                f"Escalation feature extraction failed for call '{call_id}': {exc}",
                details={"call_id": call_id},
            ) from exc

    def _extract_acoustic_features(
        self,
        transcript: SpeakerAttributedTranscript | None,
        features: EscalationFeatures,
    ) -> list[SpeakerTurn]:
        """Extract conversational structure and acoustic timing features."""
        if transcript is None:
            return []

        turns = getattr(transcript, "turns", []) or []
        features.call_duration = float(getattr(transcript, "audio_duration", 0.0) or 0.0)
        features.turn_count = len(turns)
        features.speaker_count = len(getattr(transcript, "speakers", []) or [])
        features.speech_duration = float(getattr(transcript, "speech_duration", 0.0) or 0.0)
        features.overlap_duration = float(getattr(transcript, "overlap_duration", 0.0) or 0.0)

        if features.speech_duration > 0.0:
            features.overlap_ratio = round(features.overlap_duration / features.speech_duration, 4)

        if turns:
            durations = [t.duration for t in turns if hasattr(t, "duration")]
            if durations:
                features.avg_turn_duration = round(float(np.mean(durations)), 3)
                features.max_turn_duration = round(float(np.max(durations)), 3)

            # Count speaker transitions between consecutive turns
            switches = 0
            for i in range(1, len(turns)):
                if getattr(turns[i], "speaker", None) != getattr(turns[i - 1], "speaker", None):
                    switches += 1
            features.speaker_switch_count = switches

        return turns

    def _extract_sentiment_features(
        self,
        sentiment: Any | None,
        turns: list[SpeakerTurn],
        features: EscalationFeatures,
    ) -> list[TemporalRiskPoint]:
        """Extract static sentiment ratios, volatility, and trajectory metrics."""
        temporal_points: list[TemporalRiskPoint] = []
        if sentiment is None:
            return temporal_points

        # Ratios from CallSentiment
        features.negative_sentiment_ratio = float(getattr(sentiment, "negative_ratio", 0.0) or 0.0)
        features.positive_sentiment_ratio = float(getattr(sentiment, "positive_ratio", 0.0) or 0.0)

        # Extract turn-level polarities
        sentiment_turns = getattr(sentiment, "turns", []) or []
        polarities: list[float] = []
        strong_neg_count = 0

        for t in sentiment_turns:
            label = getattr(t, "label", "NEUTRAL")
            score = float(getattr(t, "score", 0.5) or 0.5)

            if label == "POSITIVE":
                polarity = score
            elif label == "NEGATIVE":
                polarity = -score
                if score >= self.config.strong_negative_sentiment_threshold:
                    strong_neg_count += 1
            else:
                polarity = 0.0
            polarities.append(polarity)

        if sentiment_turns:
            features.strong_negative_ratio = round(strong_neg_count / len(sentiment_turns), 4)

        if polarities:
            features.sentiment_volatility = round(float(np.std(polarities)), 4)
            features.min_sentiment_score = round(float(np.min(polarities)), 4)
            features.final_turn_sentiment = round(float(polarities[-1]), 4)

            # Segment into early (0-33%), middle (33-66%), late (66-100%)
            n = len(polarities)
            idx_early_end = max(1, n // 3)
            idx_mid_end = max(idx_early_end + 1, (2 * n) // 3)

            early_vals = polarities[:idx_early_end]
            mid_vals = polarities[idx_early_end:idx_mid_end]
            late_vals = polarities[idx_mid_end:] if idx_mid_end < n else [polarities[-1]]

            features.early_sentiment_score = round(float(np.mean(early_vals)), 4)
            features.middle_sentiment_score = round(float(np.mean(mid_vals)) if mid_vals else 0.0, 4)
            features.late_sentiment_score = round(float(np.mean(late_vals)), 4)

            # Trajectory slope: negative slope indicates deteriorating sentiment
            if n >= self.config.min_turns_for_trajectory:
                # Linear slope across turns: normalized from -1.0 to 1.0
                x = np.arange(n)
                slope, _ = np.polyfit(x, polarities, 1)
                features.sentiment_slope = round(float(slope) * n, 4)  # Net change over call
            else:
                features.sentiment_slope = round(
                    features.late_sentiment_score - features.early_sentiment_score, 4
                )

            # Build temporal risk points
            segments = [
                ("early", 0, idx_early_end, features.early_sentiment_score),
                ("middle", idx_early_end, idx_mid_end, features.middle_sentiment_score),
                ("late", idx_mid_end, n, features.late_sentiment_score),
            ]
            for seg_name, start_idx, end_idx, pol_val in segments:
                # Polarity in [-1.0, 1.0] -> risk in [0, 100]
                # Negative polarity maps to high risk
                seg_risk = max(0.0, min(100.0, 50.0 - (pol_val * 40.0)))
                temporal_points.append(
                    TemporalRiskPoint(
                        segment=seg_name,
                        turn_start=start_idx,
                        turn_end=end_idx,
                        sentiment_score=pol_val,
                        segment_risk_score=seg_risk,
                    )
                )

        return temporal_points

    def _extract_intent_features(
        self,
        intent: IntentPrediction | None,
        features: EscalationFeatures,
    ) -> None:
        """Extract intent category and friction status."""
        if intent is None:
            return

        pred = getattr(intent, "predicted_intent", None) or "unknown"
        conf = float(getattr(intent, "confidence", 0.0) or 0.0)

        features.predicted_intent = str(pred).lower()
        features.intent_confidence = round(conf, 4)

        if features.predicted_intent in self.config.problem_intents:
            features.is_problem_intent = 1
        else:
            features.is_problem_intent = 0

    def _extract_repetition_and_keywords(
        self,
        turns: list[SpeakerTurn],
        features: EscalationFeatures,
    ) -> None:
        """Extract explicit escalation trigger phrases and semantic/lexical repetition."""
        if not turns:
            return

        trigger_count = 0
        texts: list[str] = []

        for turn in turns:
            text = getattr(turn, "text", "") or ""
            lowered = text.lower()
            texts.append(lowered)

            # Scan for trigger phrases
            for phrase in self.config.trigger_phrases:
                if phrase in lowered:
                    trigger_count += 1

        features.escalation_keyword_count = trigger_count

        # Estimate repetition between consecutive customer/speaker turns
        repetition_scores: list[float] = []
        for i in range(1, len(texts)):
            # Word token Jaccard similarity between adjacent turns
            tokens1 = set(re.findall(r"\b[a-z]{3,}\b", texts[i - 1]))
            tokens2 = set(re.findall(r"\b[a-z]{3,}\b", texts[i]))
            if tokens1 and tokens2:
                intersection = len(tokens1 & tokens2)
                union = len(tokens1 | tokens2)
                repetition_scores.append(intersection / union)

        if repetition_scores:
            features.repetition_score = round(float(np.mean(repetition_scores)), 4)

    def _extract_theme_features(
        self,
        themes: list[dict[str, Any]] | None,
        features: EscalationFeatures,
    ) -> None:
        """Extract theme diversity and problem theme indicators from Phase 7."""
        if not themes:
            return

        features.theme_count = len(themes)
        problem_keywords = {"freeze", "declined", "error", "failed", "unblock", "dispute", "complaint", "fee"}

        has_problem = 0
        for th in themes:
            keywords = th.get("keywords", []) or []
            label = str(th.get("label", "")).lower()
            if any(k.lower() in problem_keywords for k in keywords) or any(
                w in label for w in problem_keywords
            ):
                has_problem = 1
                break

        features.has_problem_theme = has_problem

    def _extract_ner_features(
        self,
        entities: NERResult | None,
        features: EscalationFeatures,
    ) -> None:
        """Extract entity category counts safely without exposing PII values."""
        if entities is None:
            return

        counts = getattr(entities, "entity_counts", {}) or {}
        items = getattr(entities, "entities", []) or []

        features.entity_count = len(items) if items else sum(counts.values())
        features.account_number_count = counts.get("ACCOUNT_NUMBER", 0)
        features.money_entity_count = counts.get("MONEY", 0)
