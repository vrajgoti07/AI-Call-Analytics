"""
AI Call Analytics — Intent Classification Exceptions.
"""

from __future__ import annotations


class IntentError(Exception):
    """Base exception for intent classification operations."""


class IntentModelLoadError(IntentError):
    """Raised when the intent model artifact cannot be found or loaded."""


class IntentInferenceError(IntentError):
    """Raised when intent prediction fails during inference."""
