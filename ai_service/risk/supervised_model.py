"""
AI Call Analytics — Supervised Escalation Model.

Provides supervised training, group-aware cross-validation (leakage-free),
evaluation metrics (Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix),
and calibrated inference for labeled escalation datasets.
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from ai_service.risk.config import EscalationConfig
from ai_service.risk.exceptions import InvalidFeatureSchemaError, ModelTrainingError
from ai_service.risk.schema import (
    EscalationFactor,
    EscalationFeatures,
    EscalationPrediction,
    EscalationRiskLevel,
    TemporalRiskPoint,
)

logger = logging.getLogger(__name__)


@dataclass
class SupervisedEvaluationReport:
    """Evaluation telemetry on validation or test split."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    pr_auc: float | None
    confusion_matrix: list[list[int]]
    sample_count: int
    positive_count: int
    negative_count: int
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize evaluation report."""
        return {
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "roc_auc": round(self.roc_auc, 4) if self.roc_auc is not None else None,
            "pr_auc": round(self.pr_auc, 4) if self.pr_auc is not None else None,
            "confusion_matrix": self.confusion_matrix,
            "sample_count": self.sample_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "threshold": round(self.threshold, 4),
        }


class SupervisedEscalationModel:
    """
    Supervised machine learning model for escalation risk detection.
    Trains on labeled feature vectors using GroupKFold to guarantee zero data leakage across calls.
    """

    def __init__(
        self,
        config: EscalationConfig | None = None,
        model_name: str = "logistic_regression_v1",
    ) -> None:
        self.config = config or EscalationConfig()
        self.model_name = model_name
        self.feature_names = EscalationFeatures.feature_names()
        self.scaler = StandardScaler()
        self.classifier = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
        self.is_fitted = False
        self.decision_threshold = 0.50
        self.training_metadata: dict[str, Any] = {}

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        call_ids: list[str],
        n_splits: int = 5,
    ) -> SupervisedEvaluationReport:
        """
        Train the model using call-grouped cross validation to prevent leakage.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Binary escalation labels of shape (n_samples,).
            call_ids: List of call identifiers for group-aware splitting.
            n_splits: Number of CV folds.

        Returns:
            Validation `SupervisedEvaluationReport`.
        """
        if len(X) < 10:
            raise ModelTrainingError(
                f"Insufficient training samples: got {len(X)}, required at least 10"
            )

        if X.shape[1] != len(self.feature_names):
            raise InvalidFeatureSchemaError(
                f"Feature matrix dimension ({X.shape[1]}) does not match schema length ({len(self.feature_names)})"
            )

        # Unique calls
        unique_calls = list(set(call_ids))
        effective_splits = min(n_splits, len(unique_calls))
        if effective_splits < 2:
            raise ModelTrainingError("At least 2 distinct call groups are required for cross-validation")

        logger.info(
            "Training supervised escalation model on %d samples across %d distinct calls with %d-fold GroupKFold",
            len(X),
            len(unique_calls),
            effective_splits,
        )

        gkf = GroupKFold(n_splits=effective_splits)
        oof_preds = np.zeros(len(y))
        oof_probs = np.zeros(len(y))

        for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=call_ids)):
            X_train, y_train = X[train_idx], y[train_idx]
            X_val, y_val = X[val_idx], y[val_idx]

            # Fit scaler and model only on training fold (zero leakage)
            scaler_fold = StandardScaler()
            X_train_scaled = scaler_fold.fit_transform(X_train)
            X_val_scaled = scaler_fold.transform(X_val)

            clf_fold = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
            clf_fold.fit(X_train_scaled, y_train)

            probs_val = clf_fold.predict_proba(X_val_scaled)[:, 1]
            oof_probs[val_idx] = probs_val
            oof_preds[val_idx] = (probs_val >= self.decision_threshold).astype(int)

        # Final fit on complete dataset
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.classifier.fit(X_scaled, y)
        self.is_fitted = True

        # Calculate cross-validated evaluation metrics
        acc = float(np.mean(oof_preds == y))
        prec = float(precision_score(y, oof_preds, zero_division=0))
        rec = float(recall_score(y, oof_preds, zero_division=0))
        f1 = float(f1_score(y, oof_preds, zero_division=0))

        try:
            roc = float(roc_auc_score(y, oof_probs))
        except Exception:
            roc = None

        try:
            pr = float(average_precision_score(y, oof_probs))
        except Exception:
            pr = None

        cm = confusion_matrix(y, oof_preds).tolist()

        report = SupervisedEvaluationReport(
            accuracy=acc,
            precision=prec,
            recall=rec,
            f1=f1,
            roc_auc=roc,
            pr_auc=pr,
            confusion_matrix=cm,
            sample_count=len(y),
            positive_count=int(np.sum(y == 1)),
            negative_count=int(np.sum(y == 0)),
            threshold=self.decision_threshold,
        )

        self.training_metadata = {
            "evaluation": report.to_dict(),
            "n_samples": len(y),
            "n_calls": len(unique_calls),
            "feature_names": list(self.feature_names),
        }

        logger.info(
            "Supervised model trained: Acc=%.3f, Prec=%.3f, Rec=%.3f, F1=%.3f, ROC-AUC=%s",
            acc,
            prec,
            rec,
            f1,
            f"{roc:.3f}" if roc is not None else "N/A",
        )

        return report

    def predict(
        self,
        call_id: str,
        features: EscalationFeatures,
        temporal_risk: list[TemporalRiskPoint] | None = None,
    ) -> EscalationPrediction:
        """
        Predict escalation risk for a single call using the trained model.
        """
        if not self.is_fitted:
            raise ModelTrainingError("Cannot run inference: supervised model is not yet fitted")

        x_vec = np.array([features.to_feature_vector()], dtype=np.float32)
        x_scaled = self.scaler.transform(x_vec)

        prob = float(self.classifier.predict_proba(x_scaled)[0, 1])
        risk_score = round(prob * 100.0, 2)

        # Risk tiering
        if risk_score >= self.config.high_threshold:
            risk_level = EscalationRiskLevel.HIGH
        elif risk_score >= self.config.low_threshold:
            risk_level = EscalationRiskLevel.MEDIUM
        else:
            risk_level = EscalationRiskLevel.LOW

        # Compute feature contributions: coef * scaled_val
        coefs = self.classifier.coef_[0]
        contributions: list[EscalationFactor] = []

        for name, val, c_val, coef in zip(self.feature_names, features.to_feature_vector(), x_scaled[0], coefs):
            contrib = float(coef * c_val)
            if abs(contrib) > 0.01:
                contributions.append(
                    EscalationFactor(
                        feature=name,
                        value=float(val),
                        contribution=round(contrib, 4),
                        display_name=name.replace("_", " ").title(),
                        description=f"Standardized contribution {contrib:+.3f} (coef {coef:+.3f})",
                    )
                )

        contributions.sort(key=lambda f: abs(f.contribution), reverse=True)

        return EscalationPrediction(
            call_id=call_id,
            model_type="supervised",
            model_name=self.model_name,
            model_version=self.config.model_version,
            feature_version=self.config.feature_schema_version,
            risk_score=risk_score,
            risk_probability=round(prob, 4),
            risk_level=risk_level,
            threshold_version=self.config.threshold_version,
            top_factors=contributions[:5],
            explanation="",
            feature_snapshot=features.to_dict(),
            temporal_risk=temporal_risk or [],
            metadata={
                "decision_threshold": self.decision_threshold,
                "training_metadata": self.training_metadata,
            },
        )

    def save(self, filepath: str | Path) -> None:
        """Save model artifact to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "classifier": self.classifier,
                    "scaler": self.scaler,
                    "is_fitted": self.is_fitted,
                    "decision_threshold": self.decision_threshold,
                    "feature_names": self.feature_names,
                    "training_metadata": self.training_metadata,
                    "config": self.config.to_dict(),
                },
                f,
            )
        logger.info("Saved supervised escalation model to %s", path)

    def load(self, filepath: str | Path) -> None:
        """Load model artifact from disk."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.classifier = data["classifier"]
        self.scaler = data["scaler"]
        self.is_fitted = data["is_fitted"]
        self.decision_threshold = data["decision_threshold"]
        self.feature_names = data["feature_names"]
        self.training_metadata = data.get("training_metadata", {})
        logger.info("Loaded supervised escalation model from %s", path)
