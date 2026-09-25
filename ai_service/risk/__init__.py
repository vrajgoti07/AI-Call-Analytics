"""
AI Call Analytics — Escalation Risk Detection (Phase 8).

Provides signal extraction, multi-factor risk scoring, explainability,
and calibrated risk predictions for customer conversations.
"""

from __future__ import annotations

from ai_service.risk.config import (
    DEFAULT_ESCALATION_TRIGGER_PHRASES,
    DEFAULT_PROBLEM_INTENTS,
    FEATURE_SCHEMA_VERSION,
    THRESHOLD_VERSION,
    EscalationConfig,
)
from ai_service.risk.exceptions import (
    EscalationPersistenceError,
    EscalationRiskError,
    FeatureExtractionError,
    InsufficientDataError,
    InvalidFeatureSchemaError,
    ModelInferenceError,
    ModelTrainingError,
)
from ai_service.risk.explainer import EscalationExplainer
from ai_service.risk.extractor import EscalationFeatureExtractor
from ai_service.risk.heuristic_model import HeuristicEscalationModel
from ai_service.risk.schema import (
    EscalationFactor,
    EscalationFeatures,
    EscalationPrediction,
    EscalationRiskLevel,
    TemporalRiskPoint,
)
from ai_service.risk.service import EscalationRiskService
from ai_service.risk.supervised_model import SupervisedEscalationModel, SupervisedEvaluationReport

__all__ = [
    "DEFAULT_ESCALATION_TRIGGER_PHRASES",
    "DEFAULT_PROBLEM_INTENTS",
    "FEATURE_SCHEMA_VERSION",
    "THRESHOLD_VERSION",
    "EscalationConfig",
    "EscalationFactor",
    "EscalationFeatures",
    "EscalationPersistenceError",
    "EscalationPrediction",
    "EscalationRiskError",
    "EscalationRiskLevel",
    "EscalationRiskService",
    "EscalationExplainer",
    "EscalationFeatureExtractor",
    "FeatureExtractionError",
    "HeuristicEscalationModel",
    "InsufficientDataError",
    "InvalidFeatureSchemaError",
    "ModelInferenceError",
    "ModelTrainingError",
    "SupervisedEscalationModel",
    "SupervisedEvaluationReport",
    "TemporalRiskPoint",
]
