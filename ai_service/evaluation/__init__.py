"""
AI Call Analytics — Model Evaluation & AI Quality Validation (Phase 9).

Provides standardized metrics, dataset leakage audits, component evaluators,
latency profiling, and JSON/Markdown report generators.
"""

from __future__ import annotations

from ai_service.evaluation.asr_evaluator import ASREvaluator
from ai_service.evaluation.config import EvaluationConfig
from ai_service.evaluation.dataset_evaluator import DatasetEvaluator
from ai_service.evaluation.diarization_evaluator import DiarizationEvaluator
from ai_service.evaluation.escalation_evaluator import EscalationEvaluator
from ai_service.evaluation.metrics import (
    calculate_cer,
    calculate_classification_metrics,
    calculate_clustering_metrics,
    calculate_retrieval_metrics,
    calculate_wer,
)
from ai_service.evaluation.nlp_evaluator import NLPEvaluator
from ai_service.evaluation.normalizer import TextNormalizer
from ai_service.evaluation.reports import ComponentEvaluationResult, SystemEvaluationReport
from ai_service.evaluation.retrieval_evaluator import RetrievalEvaluator
from ai_service.evaluation.runner import EvaluationRunner
from ai_service.evaluation.theme_evaluator import ThemeEvaluator

__all__ = [
    "ASREvaluator",
    "ComponentEvaluationResult",
    "DatasetEvaluator",
    "DiarizationEvaluator",
    "EscalationEvaluator",
    "EvaluationConfig",
    "EvaluationRunner",
    "NLPEvaluator",
    "RetrievalEvaluator",
    "SystemEvaluationReport",
    "TextNormalizer",
    "ThemeEvaluator",
    "calculate_cer",
    "calculate_classification_metrics",
    "calculate_clustering_metrics",
    "calculate_retrieval_metrics",
    "calculate_wer",
]
