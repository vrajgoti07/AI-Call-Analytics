"""
AI Call Analytics — Sentiment Analysis Module.

Provides multilevel sentiment classification for conversational customer calls:
- Turn-level sentiment scoring
- Per-speaker sentiment breakdown
- Chronological sentiment trajectory timeline
- Defensible call-level sentiment aggregation
"""

from ai_service.sentiment.analyzer import SentimentAnalyzer
from ai_service.sentiment.exceptions import (
    SentimentError,
    SentimentInferenceError,
    SentimentModelLoadError,
)
from ai_service.sentiment.schema import (
    CallSentiment,
    SentimentTimelinePoint,
    SpeakerSentiment,
    TurnSentiment,
)

__all__ = [
    "SentimentAnalyzer",
    "TurnSentiment",
    "SpeakerSentiment",
    "SentimentTimelinePoint",
    "CallSentiment",
    "SentimentError",
    "SentimentModelLoadError",
    "SentimentInferenceError",
]
