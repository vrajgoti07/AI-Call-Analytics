"""
AI Call Analytics — Named Entity Recognition Exceptions.
"""

from __future__ import annotations


class NERError(Exception):
    """Base exception for Named Entity Recognition operations."""


class NERModelLoadError(NERError):
    """Raised when the spaCy or transformer NER model fails to load."""


class NERInferenceError(NERError):
    """Raised when entity extraction fails during inference."""
