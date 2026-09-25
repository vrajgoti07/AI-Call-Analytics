"""
AI Call Analytics — Intent Classification Module.

Provides e-banking customer intent classification trained on the 14-class
MInDS-14 taxonomy:
- Stratified training and evaluation pipeline
- Calibrated top-k prediction service
- Decoupled model artifact persistence and caching
"""

from ai_service.intent.classifier import IntentClassifier
from ai_service.intent.exceptions import (
    IntentError,
    IntentInferenceError,
    IntentModelLoadError,
)
from ai_service.intent.schema import (
    MINDS14_INTENT_LABELS,
    IntentCandidate,
    IntentPrediction,
)
from ai_service.intent.trainer import train_minds14_intent_model

__all__ = [
    "IntentClassifier",
    "IntentPrediction",
    "IntentCandidate",
    "MINDS14_INTENT_LABELS",
    "train_minds14_intent_model",
    "IntentError",
    "IntentModelLoadError",
    "IntentInferenceError",
]
