"""
AI Call Analytics — Escalation Risk Exceptions.

Defines custom exception classes for the Phase 8 Escalation Risk Detection pipeline.
"""

from __future__ import annotations


class EscalationRiskError(Exception):
    """Base exception for all escalation risk analysis errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class FeatureExtractionError(EscalationRiskError):
    """Raised when extracting features from upstream transcript or NLP results fails."""
    pass


class InvalidFeatureSchemaError(EscalationRiskError):
    """Raised when input feature schema or vector dimensions do not match the expected version."""
    pass


class ModelInferenceError(EscalationRiskError):
    """Raised when risk model evaluation or scoring fails."""
    pass


class ModelTrainingError(EscalationRiskError):
    """Raised when supervised escalation model training or validation fails."""
    pass


class InsufficientDataError(EscalationRiskError):
    """Raised when call data contains too few turns or samples to compute risk."""
    pass


class EscalationPersistenceError(EscalationRiskError):
    """Raised when saving escalation risk results to the database fails."""
    pass
