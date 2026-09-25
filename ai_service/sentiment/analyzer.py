"""
AI Call Analytics — Sentiment Analysis Engine.

Performs batched turn-level sentiment classification, computes speaker-level
sentiment summaries, generates chronological sentiment timelines, and derives
call-level sentiment evaluations.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any

from ai_service.diarization.schema import SpeakerTurn
from ai_service.sentiment.exceptions import (
    SentimentInferenceError,
    SentimentModelLoadError,
)
from ai_service.sentiment.schema import (
    CallSentiment,
    SentimentTimelinePoint,
    SpeakerSentiment,
    TurnSentiment,
)

logger = logging.getLogger("ai_call_analytics.sentiment.analyzer")

DEFAULT_SENTIMENT_MODEL = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"

# Normalization mapping for standard Hugging Face model label formats
LABEL_MAPPING = {
    "POSITIVE": "POSITIVE",
    "POS": "POSITIVE",
    "LABEL_1": "POSITIVE",
    "LABEL_2": "POSITIVE",
    "NEGATIVE": "NEGATIVE",
    "NEG": "NEGATIVE",
    "LABEL_0": "NEGATIVE",
    "NEUTRAL": "NEUTRAL",
    "NEU": "NEUTRAL",
}

# Rule-based fallback keywords for zero-network environments
POSITIVE_WORDS = {
    "thank", "thanks", "great", "excellent", "good", "perfect", "appreciate",
    "helpful", "resolved", "happy", "glad", "wonderful", "awesome", "pleased",
}
NEGATIVE_WORDS = {
    "problem", "issue", "error", "terrible", "bad", "horrible", "awful",
    "frustrated", "angry", "upset", "broken", "unhappy", "fail", "failed",
    "freeze", "frozen", "cancel", "dispute", "complaint", "wrong",
}


def _lexicon_sentiment(text: str) -> tuple[str, float]:
    """Lightweight rule-based fallback sentiment classifier."""
    words = set(text.lower().split())
    pos_score = len(words & POSITIVE_WORDS)
    neg_score = len(words & NEGATIVE_WORDS)

    if neg_score > pos_score:
        return "NEGATIVE", round(min(0.95, 0.60 + 0.1 * neg_score), 4)
    elif pos_score > neg_score:
        return "POSITIVE", round(min(0.95, 0.60 + 0.1 * pos_score), 4)
    else:
        return "NEUTRAL", 0.75


class SentimentAnalyzer:
    """
    Multilevel sentiment analysis service for customer conversations.
    """

    _cached_pipeline: Any | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_name: str = DEFAULT_SENTIMENT_MODEL,
        pipeline: Any | None = None,
        use_fallback: bool = True,
    ) -> None:
        """
        Initialize the sentiment analyzer.

        Args:
            model_name: Hugging Face model identifier.
            pipeline: Optional pre-loaded pipeline (for testing/dependency injection).
            use_fallback: If True, falls back to lexicon analysis if model fails to load.
        """
        self.model_name = model_name
        self._pipeline = pipeline
        self.use_fallback = use_fallback

    def _get_pipeline(self) -> Any:
        """Retrieve or initialize the Hugging Face sentiment pipeline with thread-safe caching."""
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if SentimentAnalyzer._cached_pipeline is not None:
                return SentimentAnalyzer._cached_pipeline

            logger.info("Loading sentiment analysis transformer model: %s", self.model_name)
            try:
                from transformers import pipeline

                pipe = pipeline(
                    "text-classification",
                    model=self.model_name,
                    truncation=True,
                    max_length=512,
                )
                SentimentAnalyzer._cached_pipeline = pipe
                return pipe
            except Exception as err:
                if self.use_fallback:
                    logger.warning("Could not load transformer model '%s' (%s). Using lexicon fallback.", self.model_name, err)
                    return None
                raise SentimentModelLoadError(f"Failed to load sentiment model '{self.model_name}': {err}") from err

    def analyze_text(self, text: str) -> tuple[str, float]:
        """
        Classify sentiment for a single text utterance.

        Returns:
            Tuple of (normalized_label, confidence_score).
        """
        clean_text = text.strip()
        if not clean_text:
            return "NEUTRAL", 1.0

        pipe = self._get_pipeline()
        if pipe is None:
            return _lexicon_sentiment(clean_text)

        try:
            results = pipe([clean_text])
            raw_item = results[0]
            raw_label = str(raw_item.get("label", "NEUTRAL")).upper()
            score = float(raw_item.get("score", 0.75))
            norm_label = LABEL_MAPPING.get(raw_label, "NEUTRAL")
            return norm_label, round(score, 4)
        except Exception as err:
            if self.use_fallback:
                return _lexicon_sentiment(clean_text)
            raise SentimentInferenceError(f"Sentiment inference failed for text: {err}") from err

    def analyze_turns(self, turns: list[SpeakerTurn]) -> CallSentiment:
        """
        Perform batched sentiment analysis across all conversational turns (Steps 4, 8, 9, 10, 28).

        Args:
            turns: List of SpeakerTurn instances from Phase 4 alignment.

        Returns:
            Complete CallSentiment analysis including turn-level, speaker-level, and timeline results.
        """
        if not turns:
            return CallSentiment(
                label="NEUTRAL",
                score=1.0,
                positive_ratio=0.0,
                neutral_ratio=1.0,
                negative_ratio=0.0,
                turns=[],
                speaker_sentiments={},
                timeline=[],
            )

        pipe = self._get_pipeline()
        turn_sentiments: list[TurnSentiment] = []

        # Step 28: Batched inference for efficiency
        texts = [t.text.strip() for t in turns]

        if pipe is not None:
            try:
                # Filter non-empty texts for inference
                non_empty_indices = [i for i, t in enumerate(texts) if t]
                non_empty_texts = [texts[i] for i in non_empty_indices]

                raw_outputs = pipe(non_empty_texts, batch_size=16) if non_empty_texts else []
                out_map = dict(zip(non_empty_indices, raw_outputs))

                for i, turn in enumerate(turns):
                    if i in out_map:
                        item = out_map[i]
                        raw_label = str(item.get("label", "NEUTRAL")).upper()
                        score = float(item.get("score", 0.75))
                        norm_label = LABEL_MAPPING.get(raw_label, "NEUTRAL")
                    else:
                        norm_label, score = "NEUTRAL", 1.0

                    turn_sentiments.append(
                        TurnSentiment(
                            turn_id=turn.turn_id,
                            speaker=turn.speaker,
                            start=turn.start,
                            end=turn.end,
                            text=turn.text,
                            label=norm_label,
                            score=score,
                        )
                    )
            except Exception as err:
                logger.warning("Batch transformer inference failed (%s). Falling back to lexicon.", err)
                turn_sentiments = []
                for turn in turns:
                    label, score = _lexicon_sentiment(turn.text)
                    turn_sentiments.append(
                        TurnSentiment(
                            turn_id=turn.turn_id,
                            speaker=turn.speaker,
                            start=turn.start,
                            end=turn.end,
                            text=turn.text,
                            label=label,
                            score=score,
                        )
                    )
        else:
            for turn in turns:
                label, score = _lexicon_sentiment(turn.text)
                turn_sentiments.append(
                    TurnSentiment(
                        turn_id=turn.turn_id,
                        speaker=turn.speaker,
                        start=turn.start,
                        end=turn.end,
                        text=turn.text,
                        label=label,
                        score=score,
                    )
                )

        # Step 9: Speaker-level aggregation
        speaker_turns: dict[str, list[TurnSentiment]] = defaultdict(list)
        for ts in turn_sentiments:
            speaker_turns[ts.speaker].append(ts)

        speaker_sentiments: dict[str, SpeakerSentiment] = {}
        for spk, spk_ts_list in speaker_turns.items():
            pos_c = sum(1 for s in spk_ts_list if s.label == "POSITIVE")
            neu_c = sum(1 for s in spk_ts_list if s.label == "NEUTRAL")
            neg_c = sum(1 for s in spk_ts_list if s.label == "NEGATIVE")
            total = len(spk_ts_list)
            avg_score = sum(s.score for s in spk_ts_list) / max(total, 1)

            speaker_sentiments[spk] = SpeakerSentiment(
                speaker=spk,
                positive_count=pos_c,
                neutral_count=neu_c,
                negative_count=neg_c,
                positive_ratio=round(pos_c / total, 3),
                neutral_ratio=round(neu_c / total, 3),
                negative_ratio=round(neg_c / total, 3),
                average_score=round(avg_score, 4),
            )

        # Step 11: Sentiment timeline
        timeline: list[SentimentTimelinePoint] = [
            SentimentTimelinePoint(
                timestamp=ts.start,
                turn_id=ts.turn_id,
                speaker=ts.speaker,
                label=ts.label,
                score=ts.score,
            )
            for ts in turn_sentiments
        ]

        # Step 10: Call-level sentiment summary
        total_turns = len(turn_sentiments)
        total_pos = sum(1 for s in turn_sentiments if s.label == "POSITIVE")
        total_neu = sum(1 for s in turn_sentiments if s.label == "NEUTRAL")
        total_neg = sum(1 for s in turn_sentiments if s.label == "NEGATIVE")

        pos_ratio = total_pos / total_turns
        neu_ratio = total_neu / total_turns
        neg_ratio = total_neg / total_turns

        # Customer Service Defensible Aggregation Logic:
        # A call with high negative turns (>= 30%) or multiple severe negative remarks is marked NEGATIVE
        if neg_ratio >= 0.30 or (total_neg > total_pos and total_neg >= 2):
            call_label = "NEGATIVE"
            neg_scores = [s.score for s in turn_sentiments if s.label == "NEGATIVE"]
            call_score = sum(neg_scores) / len(neg_scores) if neg_scores else 0.80
        elif pos_ratio >= 0.40 and total_neg == 0:
            call_label = "POSITIVE"
            pos_scores = [s.score for s in turn_sentiments if s.label == "POSITIVE"]
            call_score = sum(pos_scores) / len(pos_scores) if pos_scores else 0.85
        else:
            call_label = "NEUTRAL"
            neu_scores = [s.score for s in turn_sentiments if s.label == "NEUTRAL"]
            call_score = sum(neu_scores) / len(neu_scores) if neu_scores else 0.75

        return CallSentiment(
            label=call_label,
            score=round(call_score, 4),
            positive_ratio=round(pos_ratio, 3),
            neutral_ratio=round(neu_ratio, 3),
            negative_ratio=round(neg_ratio, 3),
            turns=turn_sentiments,
            speaker_sentiments=speaker_sentiments,
            timeline=timeline,
        )
