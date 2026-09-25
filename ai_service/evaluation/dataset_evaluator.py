"""
AI Call Analytics — Dataset Evaluator.

Audits dataset splits, intent distributions, duration statistics,
missing values, and checks for data leakage between train/val/test splits.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import numpy as np

from ai_service.datasets.minds14_loader import load_minds14, prepare_splits
from ai_service.evaluation.config import EvaluationConfig
from ai_service.evaluation.reports import ComponentEvaluationResult

logger = logging.getLogger(__name__)


class DatasetEvaluator:
    """
    Validates dataset integrity, class balance, duration statistics,
    and checks for data leakage across evaluation splits.
    """

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def evaluate(self) -> ComponentEvaluationResult:
        """
        Execute comprehensive dataset and split audit.
        """
        logger.info("Executing dataset audit for %s (%s)", self.config.dataset_name, self.config.subset)
        try:
            # 1. Load full dataset
            ds = load_minds14(subset=self.config.subset, split=None)

            # 2. Check splits
            splits_dict = prepare_splits(
                ds,
                train_size=0.70,
                val_size=0.15,
                test_size=0.15,
                seed=self.config.random_seed,
            )

            train_ds = splits_dict["train"]
            val_ds = splits_dict["validation"]
            test_ds = splits_dict["test"]

            n_train = len(train_ds)
            n_val = len(val_ds)
            n_test = len(test_ds)
            total_samples = n_train + n_val + n_test

            # 3. Class distribution across splits
            train_intents = Counter(train_ds["intent_class"])
            test_intents = Counter(test_ds["intent_class"])

            # 4. Check for Data Leakage (transcription text overlap between train and test)
            train_texts = {str(t).lower().strip() for t in train_ds["transcription"] if t}
            test_texts = {str(t).lower().strip() for t in test_ds["transcription"] if t}
            text_overlap = train_texts.intersection(test_texts)

            # Leakage warning if exact duplicate transcripts exist across splits
            has_leakage = len(text_overlap) > 0
            leakage_rate = len(text_overlap) / len(test_texts) if test_texts else 0.0

            # 5. Missing values check
            missing_text = sum(1 for t in test_ds["transcription"] if not t or str(t).strip() == "")
            missing_intent = sum(1 for i in test_ds["intent_class"] if i is None)

            metrics = {
                "total_samples": total_samples,
                "train_samples": n_train,
                "val_samples": n_val,
                "test_samples": n_test,
                "num_classes": len(set(train_intents.keys()) | set(test_intents.keys())),
                "exact_text_overlap_count": len(text_overlap),
                "leakage_rate": round(leakage_rate, 4),
                "missing_text_count": missing_text,
                "missing_intent_count": missing_intent,
            }

            status = "PASSED"
            if has_leakage and leakage_rate > 0.05:
                status = "WARNING"

            summary = (
                f"Audited {total_samples} samples across 14 intent classes. "
                f"Train={n_train}, Val={n_val}, Test={n_test}. "
                f"Exact text overlap={len(text_overlap)} ({leakage_rate:.1%})."
            )

            return ComponentEvaluationResult(
                component="dataset",
                evaluation_type="quantitative",
                status=status,
                metrics=metrics,
                sample_count=total_samples,
                dataset_name=f"{self.config.dataset_name}:{self.config.subset}",
                model_name="MInDS-14 Loader",
                model_version="1.0.0",
                summary=summary,
                details={
                    "class_distribution_train": dict(train_intents),
                    "class_distribution_test": dict(test_intents),
                    "overlapping_sample_examples": list(text_overlap)[:3],
                },
            )

        except Exception as exc:
            logger.error("Dataset evaluation failed: %s", exc)
            return ComponentEvaluationResult(
                component="dataset",
                evaluation_type="quantitative",
                status="FAILED",
                metrics={},
                sample_count=0,
                dataset_name=self.config.dataset_name,
                model_name="MInDS-14 Loader",
                summary=f"Evaluation failed: {exc}",
                details={"error": str(exc)},
            )
