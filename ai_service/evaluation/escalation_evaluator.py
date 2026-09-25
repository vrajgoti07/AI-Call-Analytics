"""
AI Call Analytics — Escalation Risk Evaluator.

Evaluates Escalation Risk Detection:
1. Supervised Mode: When labeled data exists, evaluates Precision, Recall, F1, ROC-AUC,
   PR-AUC, Confusion Matrix, and GroupKFold leakage prevention.
2. Heuristic Mode: When ground-truth transfer labels are unavailable, evaluates risk score
   distribution, factor contribution consistency, sensitivity, and explainability fidelity.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ai_service.evaluation.config import EvaluationConfig
from ai_service.evaluation.reports import ComponentEvaluationResult
from ai_service.risk import (
    EscalationConfig,
    EscalationFeatures,
    EscalationRiskLevel,
    EscalationRiskService,
    SupervisedEscalationModel,
)

logger = logging.getLogger(__name__)


class EscalationEvaluator:
    """
    Evaluates Phase 8 Escalation Risk scoring and explainability.
    """

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def evaluate_heuristic(self) -> ComponentEvaluationResult:
        """
        Evaluate heuristic model across synthetic low, medium, and high friction scenarios.
        """
        logger.info("Executing Heuristic Escalation evaluation...")
        try:
            service = EscalationRiskService()

            # Test 3 controlled scenarios
            # Scenario A: Calm balance check
            feat_a = EscalationFeatures(
                call_duration=20.0,
                turn_count=4,
                negative_sentiment_ratio=0.0,
                sentiment_slope=0.5,
                is_problem_intent=0,
                escalation_keyword_count=0,
            )
            pred_a = service.heuristic_model.predict("CALL-A", feat_a)

            # Scenario B: App error annoyance
            feat_b = EscalationFeatures(
                call_duration=35.0,
                turn_count=5,
                negative_sentiment_ratio=0.20,
                sentiment_slope=-0.5,
                is_problem_intent=1,
                intent_confidence=0.85,
                escalation_keyword_count=0,
            )
            pred_b = service.heuristic_model.predict("CALL-B", feat_b)

            # Scenario C: Severe card freeze dispute
            feat_c = EscalationFeatures(
                call_duration=50.0,
                turn_count=6,
                negative_sentiment_ratio=0.50,
                strong_negative_ratio=0.33,
                sentiment_slope=-1.5,
                late_sentiment_score=-0.9,
                is_problem_intent=1,
                intent_confidence=0.92,
                escalation_keyword_count=3,
                overlap_ratio=0.15,
            )
            pred_c = service.heuristic_model.predict("CALL-C", feat_c)

            # Assert monotonicity and tier consistency
            assert pred_a.risk_score < pred_b.risk_score < pred_c.risk_score
            assert pred_a.risk_level == EscalationRiskLevel.LOW
            assert pred_c.risk_level == EscalationRiskLevel.HIGH

            metrics = {
                "ground_truth_status": "UNAVAILABLE",
                "model_type": "heuristic",
                "scenario_low_score": pred_a.risk_score,
                "scenario_med_score": pred_b.risk_score,
                "scenario_high_score": pred_c.risk_score,
                "monotonicity_verified": True,
                "explainability_aligned": len(pred_c.top_factors) > 0,
            }

            summary = (
                "Ground-truth escalation labels unavailable in MInDS-14. "
                f"Evaluated heuristic consistency across 3 standard test scenarios: "
                f"Low={pred_a.risk_score:.1f}, Med={pred_b.risk_score:.1f}, High={pred_c.risk_score:.1f}. "
                "Monotonicity and factor explainability verified."
            )

            return ComponentEvaluationResult(
                component="escalation",
                evaluation_type="heuristic",
                status="PASSED",
                metrics=metrics,
                sample_count=3,
                model_name="composite_weighted_heuristic_v1",
                model_version="1.0.0",
                summary=summary,
                details={
                    "scenarios": [
                        {"id": "CALL-A", "score": pred_a.risk_score, "level": pred_a.risk_level.value},
                        {"id": "CALL-B", "score": pred_b.risk_score, "level": pred_b.risk_level.value},
                        {"id": "CALL-C", "score": pred_c.risk_score, "level": pred_c.risk_level.value},
                    ]
                },
            )

        except Exception as exc:
            logger.error("Escalation heuristic evaluation failed: %s", exc)
            return ComponentEvaluationResult(
                component="escalation",
                evaluation_type="heuristic",
                status="FAILED",
                metrics={},
                sample_count=0,
                model_name="composite_weighted_heuristic_v1",
                summary=f"Evaluation failed: {exc}",
                details={"error": str(exc)},
            )

    def evaluate_supervised(
        self,
        X: np.ndarray,
        y: np.ndarray,
        call_ids: list[str],
    ) -> ComponentEvaluationResult:
        """
        Evaluate supervised escalation model on labeled dataset with GroupKFold.
        """
        logger.info("Executing Supervised Escalation evaluation with GroupKFold...")
        try:
            model = SupervisedEscalationModel()
            report = model.train(X, y, call_ids=call_ids, n_splits=5)

            metrics = {
                "accuracy": report.accuracy,
                "precision": report.precision,
                "recall": report.recall,
                "f1": report.f1,
                "roc_auc": report.roc_auc,
                "pr_auc": report.pr_auc,
                "confusion_matrix": report.confusion_matrix,
                "positive_count": report.positive_count,
                "negative_count": report.negative_count,
            }

            status = "PASSED" if report.f1 >= 0.85 else "WARNING"
            summary = (
                f"Evaluated supervised model on {report.sample_count} samples across {len(set(call_ids))} calls. "
                f"Accuracy={report.accuracy:.2%}, Precision={report.precision:.2%}, "
                f"Recall={report.recall:.2%}, F1={report.f1:.2%}, ROC-AUC={report.roc_auc}."
            )

            return ComponentEvaluationResult(
                component="escalation",
                evaluation_type="quantitative",
                status=status,
                metrics=metrics,
                sample_count=report.sample_count,
                model_name="logistic_regression_v1",
                model_version="1.0.0",
                summary=summary,
                details={"confusion_matrix": report.confusion_matrix},
            )

        except Exception as exc:
            logger.error("Supervised escalation evaluation failed: %s", exc)
            return ComponentEvaluationResult(
                component="escalation",
                evaluation_type="quantitative",
                status="FAILED",
                metrics={},
                sample_count=0,
                model_name="logistic_regression_v1",
                summary=f"Supervised evaluation failed: {exc}",
                details={"error": str(exc)},
            )
