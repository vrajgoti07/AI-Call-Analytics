"""
AI Call Analytics — Sentiment Analysis Exceptions.
"""

from __future__ import annotations


class SentimentError(Exception):
    """Base exception for sentiment analysis operations."""


class SentimentModelLoadError(SentimentError):
    """Raised when the sentiment model fails to download or initialize."""


class SentimentInferenceError(SentimentError):
    """Raised when sentiment inference fails during processing."""
