"""
AI Call Analytics — Evaluation Framework Test Suite (Phase 9).

Validates metric calculations (WER, CER, F1, MRR, Silhouette),
text normalizer rules, missing ground truth reporting ('GROUND_TRUTH_UNAVAILABLE'),
structural checks, and report serialization.
"""

from __future__ import annotations

import numpy as np
import pytest

from ai_service.diarization.schema import SpeakerAttributedTranscript, SpeakerTurn
from ai_service.evaluation import (
    ASREvaluator,
    DiarizationEvaluator,
    EscalationEvaluator,
    EvaluationConfig,
    NLPEvaluator,
    RetrievalEvaluator,
    SystemEvaluationReport,
    TextNormalizer,
    ThemeEvaluator,
    calculate_cer,
    calculate_classification_metrics,
    calculate_clustering_metrics,
    calculate_retrieval_metrics,
    calculate_wer,
)


# ---------------------------------------------------------------------------
# 1. Metric Correctness Tests
# ---------------------------------------------------------------------------
class TestMetricCorrectness:
    def test_wer_exact_match(self):
        wer, s, d, i, n = calculate_wer("hello world", "hello world")
        assert wer == 0.0
        assert s == 0 and d == 0 and i == 0
        assert n == 2

    def test_wer_substitutions_deletions_insertions(self):
        # Substitution test: "customer" -> "client"
        wer_s, s, d, i, n = calculate_wer("call customer service", "call client service")
        assert n == 3
        assert s == 1 and d == 0 and i == 0
        assert wer_s == pytest.approx(1 / 3, rel=1e-3)

        # Deletion test: "account" deleted
        wer_d, s, d, i, n = calculate_wer("check my account balance", "check my balance")
        assert n == 4
        assert s == 0 and d == 1 and i == 0
        assert wer_d == 0.25

        # Insertion test: "money" inserted
        wer_i, s, d, i, n = calculate_wer("send wire transfer", "send money wire transfer")
        assert n == 3
        assert s == 0 and d == 0 and i == 1
        assert wer_i == pytest.approx(1 / 3, rel=1e-3)

    def test_wer_empty_strings(self):
        wer, s, d, i, n = calculate_wer("", "")
        assert wer == 0.0
        wer_del, _, _, _, _ = calculate_wer("hello world", "")
        assert wer_del == 1.0

    def test_cer_calculation(self):
        cer = calculate_cer("cat", "cot")
        assert cer == pytest.approx(1 / 3, rel=1e-3)
        assert calculate_cer("test", "test") == 0.0

    def test_classification_metrics(self):
        y_true = ["A", "B", "A", "B", "A"]
        y_pred = ["A", "B", "B", "B", "A"]
        res = calculate_classification_metrics(y_true, y_pred, labels=["A", "B"])

        assert res["sample_count"] == 5
        assert res["accuracy"] == 0.80  # 4 / 5
        assert res["macro_f1"] > 0.70
        assert len(res["confusion_matrix"]) == 2

    def test_retrieval_metrics_mrr_and_recall(self):
        # 2 queries
        relevant = [{"c1", "c2"}, {"c3"}]
        # Query 1: hit at rank 1 (c1) -> RR = 1.0, Recall@1 = 1/2 = 0.5, Recall@5 = 2/2 = 1.0
        # Query 2: hit at rank 2 (c3) -> RR = 0.5, Recall@1 = 0.0, Recall@5 = 1/1 = 1.0
        retrieved = [
            ["c1", "c2", "c5"],
            ["c9", "c3", "c1"],
        ]
        res = calculate_retrieval_metrics(relevant, retrieved, k_values=(1, 5))
        assert res["mrr"] == 0.75  # (1.0 + 0.5) / 2
        assert res["recall@1"] == 0.25  # (0.5 + 0.0) / 2
        assert res["recall@5"] == 1.0

    def test_clustering_metrics_with_noise(self):
        # 2 distinct clusters plus noise points (-1)
        embeddings = np.array([
            [1.0, 0.0], [0.9, 0.1], [0.8, 0.2],  # Cluster 0
            [0.0, 1.0], [0.1, 0.9], [0.2, 0.8],  # Cluster 1
            [0.5, 0.5],                           # Noise (-1)
        ])
        labels = np.array([0, 0, 0, 1, 1, 1, -1])
        res = calculate_clustering_metrics(embeddings, labels)

        assert res["n_clusters"] == 2
        assert res["noise_count"] == 1
        assert res["noise_percentage"] == round(1 / 7 * 100, 2)
        assert res["silhouette_score"] is not None
        assert res["silhouette_score"] > 0.50


# ---------------------------------------------------------------------------
# 2. Text Normalizer Tests
# ---------------------------------------------------------------------------
class TestTextNormalizer:
    def test_contractions_and_punctuation(self):
        raw = "I can't access my account, and I'm very frustrated!"
        norm = TextNormalizer.normalize(raw)
        assert norm == "i cannot access my account and i am very frustrated"

    def test_whitespace_and_casing(self):
        raw = "  PLEASE   CHECK   MY   BALANCE...  "
        norm = TextNormalizer.normalize(raw)
        assert norm == "please check my balance"


# ---------------------------------------------------------------------------
# 3. Missing Ground Truth Handling Tests
# ---------------------------------------------------------------------------
class TestMissingGroundTruthHandling:
    def test_diarization_reports_ground_truth_unavailable(self):
        evaluator = DiarizationEvaluator()
        transcript = SpeakerAttributedTranscript(
            full_text="SPEAKER_00: Test.",
            turns=[SpeakerTurn(1, "SPEAKER_00", 0.0, 2.0, "Test.")],
            speakers=["SPEAKER_00"],
            total_turns=1,
            audio_duration=3.0,
            speech_duration=2.0,
        )
        res = evaluator.evaluate_structural([transcript])
        assert res.metrics["der"] is None
        assert res.details["ground_truth_status"] == "UNAVAILABLE"
        assert res.evaluation_type == "structural"
        assert res.status == "PASSED"

    def test_sentiment_reports_ground_truth_unavailable(self):
        evaluator = NLPEvaluator()
        res = evaluator.evaluate_sentiment()
        assert res.status == "GROUND_TRUTH_UNAVAILABLE"
        assert res.metrics["accuracy"] is None
        assert "unavailable" in res.summary.lower()

    def test_ner_reports_ground_truth_unavailable(self):
        evaluator = NLPEvaluator()
        res = evaluator.evaluate_ner()
        assert res.status == "GROUND_TRUTH_UNAVAILABLE"
        assert res.metrics["entity_f1"] is None


# ---------------------------------------------------------------------------
# 4. Report Serialization Tests
# ---------------------------------------------------------------------------
class TestReportSerialization:
    def test_json_and_markdown_export(self, tmp_path):
        report = SystemEvaluationReport(git_commit="test_commit_hash")
        report.latency_breakdown_seconds = {"intent": 0.05, "retrieval": 0.02}
        report.total_pipeline_latency_seconds = 0.07

        evaluator = RetrievalEvaluator()
        res = evaluator.evaluate()
        report.add_result(res)

        json_path = tmp_path / "eval.json"
        md_path = tmp_path / "eval.md"

        report.save_json(json_path)
        report.save_markdown(md_path)

        assert json_path.exists()
        assert md_path.exists()

        content_json = json_path.read_text(encoding="utf-8")
        content_md = md_path.read_text(encoding="utf-8")

        assert "test_commit_hash" in content_json
        assert "MRR" in content_md
        assert "Quality Matrix Summary" in content_md
