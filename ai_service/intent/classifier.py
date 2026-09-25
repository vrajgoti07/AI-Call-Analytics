"""
AI Call Analytics — Intent Classifier Service.

Provides runtime inference for customer intent detection based on the
14-class MInDS-14 banking taxonomy. Loads the persisted model artifact once,
caches it in memory, and predicts top-k intent candidates with confidence scores.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from ai_service.intent.exceptions import (
    IntentInferenceError,
    IntentModelLoadError,
)
from ai_service.intent.schema import (
    MINDS14_INTENT_LABELS,
    IntentCandidate,
    IntentPrediction,
)

logger = logging.getLogger("ai_call_analytics.intent.classifier")

DEFAULT_MODEL_PATH = Path("models/intent/minds14_intent_model.joblib")


class IntentClassifier:
    """
    Inference service for e-banking intent classification.
    """

    _cached_bundle: dict[str, Any] | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_path: Path | str = DEFAULT_MODEL_PATH,
        model_bundle: dict[str, Any] | None = None,
        auto_train: bool = True,
    ) -> None:
        """
        Initialize the intent classifier.

        Args:
            model_path: Path to serialized .joblib model bundle.
            model_bundle: Optional pre-loaded model dictionary (for DI/testing).
            auto_train: If True and model artifact missing, automatically trains it.
        """
        self.model_path = Path(model_path)
        self._bundle = model_bundle
        self.auto_train = auto_train

    def _get_bundle(self) -> dict[str, Any]:
        """Retrieve model bundle with thread-safe caching."""
        if self._bundle is not None:
            return self._bundle

        with self._lock:
            if IntentClassifier._cached_bundle is not None:
                return IntentClassifier._cached_bundle

            if not self.model_path.exists():
                if self.auto_train:
                    logger.info("Intent model artifact not found at %s. Auto-training now...", self.model_path)
                    from ai_service.intent.trainer import train_minds14_intent_model
                    train_minds14_intent_model(output_dir=self.model_path.parent)
                else:
                    raise IntentModelLoadError(
                        f"Intent model artifact not found at '{self.model_path}'. "
                        "Run 'python scripts/train_intent_classifier.py' to generate it."
                    )

            try:
                logger.info("Loading intent classification model from: %s", self.model_path)
                bundle = joblib.load(self.model_path)
                IntentClassifier._cached_bundle = bundle
                return bundle
            except Exception as err:
                raise IntentModelLoadError(f"Failed to load intent model from '{self.model_path}': {err}") from err

    def predict(self, text: str, top_k: int = 3) -> IntentPrediction:
        """
        Predict the intent of a conversational transcript or turn text (Step 12, 18).

        Args:
            text: Utterance or complete customer transcript.
            top_k: Number of highest-confidence predictions to return.

        Returns:
            IntentPrediction with predicted_intent, confidence, and ranked top_k list.
        """
        clean_text = text.strip()
        if not clean_text:
            return IntentPrediction(
                predicted_intent="unknown",
                confidence=0.0,
                top_k=[],
            )

        bundle = self._get_bundle()
        pipeline = bundle["pipeline"]
        class_names = bundle["classes"]

        try:
            probs = pipeline.predict_proba([clean_text])[0]
            top_indices = np.argsort(probs)[::-1][:top_k]

            candidates = [
                IntentCandidate(
                    intent=class_names[idx],
                    confidence=float(probs[idx]),
                )
                for idx in top_indices
            ]

            best_candidate = candidates[0] if candidates else IntentCandidate(intent="unknown", confidence=0.0)

            return IntentPrediction(
                predicted_intent=best_candidate.intent,
                confidence=best_candidate.confidence,
                top_k=candidates,
                model_name="minds14_tfidf_logistic",
                taxonomy="MInDS-14",
            )
        except Exception as err:
            logger.error("Intent prediction failed for text: %s", err)
            raise IntentInferenceError(f"Intent classification failed: {err}") from err
