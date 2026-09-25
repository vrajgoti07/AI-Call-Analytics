"""
AI Call Analytics — Escalation Risk Detection Test Suite (Phase 8).

Validates feature engineering, missing data resilience, PII safety,
heuristic scoring, group-aware supervised training with leakage prevention,
explainability narrative synthesis, and PostgreSQL ORM persistence.
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.model_selection import GroupKFold

from ai_service.diarization.schema import (
    SpeakerAttributedTranscript,
    SpeakerStats,
    SpeakerTurn,
)
from ai_service.intent.schema import IntentCandidate, IntentPrediction
from ai_service.ner.schema import EntityItem, NERResult
from ai_service.risk import (
    EscalationConfig,
    EscalationFactor,
    EscalationFeatures,
    EscalationPrediction,
    EscalationRiskLevel,
    EscalationRiskService,
    HeuristicEscalationModel,
    SupervisedEscalationModel,
)
from ai_service.risk.explainer import EscalationExplainer
from ai_service.risk.extractor import EscalationFeatureExtractor
from ai_service.sentiment.schema import CallSentiment, TurnSentiment
from backend.app.models.escalation import EscalationRisk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_normal_call() -> dict:
    """Fixture providing a standard low-risk customer inquiry."""
    turns = [
        SpeakerTurn(1, "SPEAKER_00", 0.0, 3.0, "Hello, thanks for calling. How can I help?"),
        SpeakerTurn(2, "SPEAKER_01", 3.2, 8.0, "Hi, I just wanted to check my checking balance."),
        SpeakerTurn(3, "SPEAKER_00", 8.2, 12.0, "Your checking account balance is $2,400."),
        SpeakerTurn(4, "SPEAKER_01", 12.2, 15.0, "Great, thanks a lot for your help!"),
    ]
    sentiment_turns = [
        TurnSentiment(1, "SPEAKER_00", 0.0, 3.0, turns[0].text, "POSITIVE", 0.8),
        TurnSentiment(2, "SPEAKER_01", 3.2, 8.0, turns[1].text, "NEUTRAL", 0.9),
        TurnSentiment(3, "SPEAKER_00", 8.2, 12.0, turns[2].text, "NEUTRAL", 0.85),
        TurnSentiment(4, "SPEAKER_01", 12.2, 15.0, turns[3].text, "POSITIVE", 0.95),
    ]
    transcript = SpeakerAttributedTranscript(
        full_text="\n".join(f"{t.speaker}: {t.text}" for t in turns),
        turns=turns,
        speakers=["SPEAKER_00", "SPEAKER_01"],
        speaker_stats={
            "SPEAKER_00": SpeakerStats("SPEAKER_00", 6.8, 2, 45.0),
            "SPEAKER_01": SpeakerStats("SPEAKER_01", 7.6, 2, 55.0),
        },
        total_turns=4,
        audio_duration=15.0,
        speech_duration=14.4,
        overlap_duration=0.1,
    )
    sentiment = CallSentiment(
        label="POSITIVE",
        score=0.88,
        positive_ratio=0.50,
        neutral_ratio=0.50,
        negative_ratio=0.0,
        turns=sentiment_turns,
    )
    intent = IntentPrediction("balance", 0.95, [IntentCandidate("balance", 0.95)])
    entities = NERResult([EntityItem(1, "$2,400", "MONEY", 0, 6)], {"MONEY": 1})
    return {
        "call_id": "CALL-NORMAL-001",
        "transcript": transcript,
        "sentiment": sentiment,
        "intent": intent,
        "entities": entities,
        "themes": [{"label": "BALANCE / CHECKING", "keywords": ["balance", "checking"]}],
    }


@pytest.fixture
def sample_escalated_call() -> dict:
    """Fixture providing a severe friction escalation call."""
    turns = [
        SpeakerTurn(1, "SPEAKER_00", 0.0, 3.0, "Hello, customer support. How can I help?"),
        SpeakerTurn(2, "SPEAKER_01", 3.2, 14.0, "My card was blocked and my account is frozen for no reason!"),
        SpeakerTurn(3, "SPEAKER_00", 14.2, 18.0, "Our policy requires a 24-hour security hold."),
        SpeakerTurn(4, "SPEAKER_01", 17.5, 32.0, "This is unacceptable and ridiculous! I want to speak to a manager right now, transfer me to your supervisor or I will file an official complaint!"),
    ]
    sentiment_turns = [
        TurnSentiment(1, "SPEAKER_00", 0.0, 3.0, turns[0].text, "NEUTRAL", 0.7),
        TurnSentiment(2, "SPEAKER_01", 3.2, 14.0, turns[1].text, "NEGATIVE", 0.85),
        TurnSentiment(3, "SPEAKER_00", 14.2, 18.0, turns[2].text, "NEUTRAL", 0.6),
        TurnSentiment(4, "SPEAKER_01", 17.5, 32.0, turns[3].text, "NEGATIVE", 0.98),
    ]
    transcript = SpeakerAttributedTranscript(
        full_text="\n".join(f"{t.speaker}: {t.text}" for t in turns),
        turns=turns,
        speakers=["SPEAKER_00", "SPEAKER_01"],
        speaker_stats={
            "SPEAKER_00": SpeakerStats("SPEAKER_00", 6.8, 2, 30.0),
            "SPEAKER_01": SpeakerStats("SPEAKER_01", 25.3, 2, 70.0),
        },
        total_turns=4,
        audio_duration=32.0,
        speech_duration=32.1,
        overlap_duration=3.5,
        overlap_detected=True,
    )
    sentiment = CallSentiment(
        label="NEGATIVE",
        score=0.92,
        positive_ratio=0.0,
        neutral_ratio=0.50,
        negative_ratio=0.50,
        turns=sentiment_turns,
    )
    intent = IntentPrediction("freeze", 0.94, [IntentCandidate("freeze", 0.94)])
    entities = NERResult([], {})
    return {
        "call_id": "CALL-ESCALATED-001",
        "transcript": transcript,
        "sentiment": sentiment,
        "intent": intent,
        "entities": entities,
        "themes": [{"label": "CARD / ACCOUNT FREEZE", "keywords": ["freeze", "card"]}],
    }


# ---------------------------------------------------------------------------
# 1. Feature Extraction Tests
# ---------------------------------------------------------------------------
class TestEscalationFeatureExtractor:
    def test_extract_normal_call_features(self, sample_normal_call):
        extractor = EscalationFeatureExtractor()
        features, temporal = extractor.extract(
            call_id=sample_normal_call["call_id"],
            transcript=sample_normal_call["transcript"],
            sentiment=sample_normal_call["sentiment"],
            intent=sample_normal_call["intent"],
            entities=sample_normal_call["entities"],
            themes=sample_normal_call["themes"],
        )

        assert features.turn_count == 4
        assert features.call_duration == 15.0
        assert features.negative_sentiment_ratio == 0.0
        assert features.escalation_keyword_count == 0
        assert features.is_problem_intent == 0
        assert features.sentiment_slope >= 0.0  # Stable/improving
        assert len(temporal) == 3

    def test_extract_escalated_call_features(self, sample_escalated_call):
        extractor = EscalationFeatureExtractor()
        features, temporal = extractor.extract(
            call_id=sample_escalated_call["call_id"],
            transcript=sample_escalated_call["transcript"],
            sentiment=sample_escalated_call["sentiment"],
            intent=sample_escalated_call["intent"],
            entities=sample_escalated_call["entities"],
            themes=sample_escalated_call["themes"],
        )

        assert features.negative_sentiment_ratio == 0.50
        assert features.strong_negative_ratio > 0.0
        assert features.escalation_keyword_count >= 2  # "manager", "supervisor", "complaint"
        assert features.is_problem_intent == 1  # "freeze"
        assert features.sentiment_slope < 0.0  # Deteriorating
        assert features.overlap_duration > 0.0
        assert features.has_problem_theme == 1

    def test_missing_data_resilience(self):
        """Extractor should handle missing upstream data without crashing."""
        extractor = EscalationFeatureExtractor()
        features, temporal = extractor.extract(
            call_id="CALL-EMPTY-001",
            transcript=None,
            sentiment=None,
            intent=None,
            entities=None,
            themes=None,
        )

        assert features.turn_count == 0
        assert features.call_duration == 0.0
        assert features.negative_sentiment_ratio == 0.0
        assert features.is_problem_intent == 0
        assert features.escalation_keyword_count == 0
        assert temporal == []

    def test_pii_safety_in_features(self, sample_normal_call):
        """Feature dictionary snapshot must NEVER expose customer names, card numbers, or raw text."""
        extractor = EscalationFeatureExtractor()
        features, _ = extractor.extract(
            call_id=sample_normal_call["call_id"],
            transcript=sample_normal_call["transcript"],
            sentiment=sample_normal_call["sentiment"],
            intent=sample_normal_call["intent"],
            entities=sample_normal_call["entities"],
            themes=sample_normal_call["themes"],
        )

        snapshot = features.to_dict()
        snapshot_str = str(snapshot)

        # Raw dialogue fragments must not be in the numerical feature snapshot
        assert "Hello, thanks for calling" not in snapshot_str
        assert "checking balance" not in snapshot_str
        assert "$2,400" not in snapshot_str
        assert isinstance(snapshot["account_number_count"], int)
        assert isinstance(snapshot["money_entity_count"], int)


# ---------------------------------------------------------------------------
# 2. Heuristic Risk Model Tests
# ---------------------------------------------------------------------------
class TestHeuristicEscalationModel:
    def test_low_risk_call_scoring(self, sample_normal_call):
        service = EscalationRiskService()
        pred = service.analyze(
            call_id=sample_normal_call["call_id"],
            transcript=sample_normal_call["transcript"],
            sentiment=sample_normal_call["sentiment"],
            intent=sample_normal_call["intent"],
            entities=sample_normal_call["entities"],
            themes=sample_normal_call["themes"],
        )

        assert pred.risk_level == EscalationRiskLevel.LOW
        assert pred.risk_score < 35.0
        assert pred.risk_probability < 0.35
        assert pred.model_type == "heuristic"
        assert len(pred.top_factors) > 0

    def test_high_risk_call_scoring(self, sample_escalated_call):
        service = EscalationRiskService()
        pred = service.analyze(
            call_id=sample_escalated_call["call_id"],
            transcript=sample_escalated_call["transcript"],
            sentiment=sample_escalated_call["sentiment"],
            intent=sample_escalated_call["intent"],
            entities=sample_escalated_call["entities"],
            themes=sample_escalated_call["themes"],
        )

        assert pred.risk_level == EscalationRiskLevel.HIGH
        assert pred.risk_score >= 65.0
        assert pred.risk_probability >= 0.65
        assert "HIGH" in pred.explanation
        assert any(f.feature == "escalation_keywords" for f in pred.top_factors)

    def test_threshold_boundary_tiering(self):
        config = EscalationConfig(low_threshold=30.0, high_threshold=70.0)
        model = HeuristicEscalationModel(config)

        # Construct synthetic feature vectors targeting specific risk zones
        low_feat = EscalationFeatures(negative_sentiment_ratio=0.0, sentiment_slope=0.5)
        pred_low = model.predict("C-LOW", low_feat)
        assert pred_low.risk_level == EscalationRiskLevel.LOW

        high_feat = EscalationFeatures(
            negative_sentiment_ratio=0.9,
            strong_negative_ratio=0.8,
            sentiment_slope=-1.5,
            late_sentiment_score=-0.9,
            escalation_keyword_count=3,
            is_problem_intent=1,
            intent_confidence=0.95,
        )
        pred_high = model.predict("C-HIGH", high_feat)
        assert pred_high.risk_level == EscalationRiskLevel.HIGH


# ---------------------------------------------------------------------------
# 3. Explainability Tests
# ---------------------------------------------------------------------------
class TestEscalationExplainer:
    def test_evidence_based_explanation_generation(self, sample_escalated_call):
        service = EscalationRiskService()
        pred = service.analyze(
            call_id=sample_escalated_call["call_id"],
            transcript=sample_escalated_call["transcript"],
            sentiment=sample_escalated_call["sentiment"],
            intent=sample_escalated_call["intent"],
            entities=sample_escalated_call["entities"],
            themes=sample_escalated_call["themes"],
        )

        explanation = pred.explanation
        assert "Escalation risk is HIGH" in explanation
        assert "escalation phrase" in explanation
        assert "freeze" in explanation
        # Explanations must be evidence-based, avoiding psychological claims
        assert "angry person" not in explanation
        assert "bad customer" not in explanation


# ---------------------------------------------------------------------------
# 4. Supervised Model & Data Leakage Prevention Tests
# ---------------------------------------------------------------------------
class TestSupervisedEscalationModel:
    def test_group_aware_training_and_evaluation(self):
        """Train model with call-level GroupKFold to verify leakage-free validation."""
        np.random.seed(42)
        call_ids = []
        features_list = []
        labels = []

        # 30 distinct calls, each generating 2 samples
        for call_idx in range(30):
            c_id = f"CALL-{call_idx:03d}"
            is_esc = 1 if call_idx % 3 == 0 else 0
            for _ in range(2):
                feat = EscalationFeatures(
                    negative_sentiment_ratio=0.8 if is_esc else 0.1,
                    strong_negative_ratio=0.5 if is_esc else 0.0,
                    sentiment_slope=-0.5 if is_esc else 0.3,
                    escalation_keyword_count=2 if is_esc else 0,
                    is_problem_intent=is_esc,
                )
                call_ids.append(c_id)
                features_list.append(feat.to_feature_vector())
                labels.append(is_esc)

        X = np.array(features_list, dtype=np.float32)
        y = np.array(labels, dtype=np.int32)

        model = SupervisedEscalationModel()
        report = model.train(X, y, call_ids=call_ids, n_splits=5)

        assert report.sample_count == 60
        assert report.accuracy >= 0.90
        assert report.precision >= 0.90
        assert report.recall >= 0.90
        assert report.f1 >= 0.90
        assert len(report.confusion_matrix) == 2

        # Inference test
        test_feat = EscalationFeatures(
            negative_sentiment_ratio=0.85,
            strong_negative_ratio=0.6,
            sentiment_slope=-0.6,
            escalation_keyword_count=2,
            is_problem_intent=1,
        )
        pred = model.predict("TEST-CALL", test_feat)
        assert pred.model_type == "supervised"
        assert pred.risk_level == EscalationRiskLevel.HIGH
        assert pred.risk_probability > 0.50

    def test_strict_call_leakage_prevention(self):
        """Verify that samples from the same call NEVER appear in both train and validation folds."""
        call_ids = ["CALL-A", "CALL-A", "CALL-B", "CALL-B", "CALL-C", "CALL-C", "CALL-D", "CALL-D"]
        X = np.random.randn(8, len(EscalationFeatures.feature_names()))
        y = np.array([1, 1, 0, 0, 1, 1, 0, 0])

        gkf = GroupKFold(n_splits=4)
        for train_idx, val_idx in gkf.split(X, y, groups=call_ids):
            train_calls = {call_ids[i] for i in train_idx}
            val_calls = {call_ids[i] for i in val_idx}
            intersection = train_calls.intersection(val_calls)
            assert len(intersection) == 0, f"Data leakage detected! Shared calls: {intersection}"


# ---------------------------------------------------------------------------
# 5. Database Model Tests
# ---------------------------------------------------------------------------
class TestEscalationDatabaseModel:
    def test_orm_model_columns_and_instantiation(self):
        record = EscalationRisk(
            call_id="CALL-DB-001",
            model_type="heuristic",
            model_name="composite_weighted_heuristic_v1",
            model_version="1.0.0",
            feature_version="v1",
            threshold_version="v1.0",
            risk_score=78.5,
            risk_probability=0.785,
            risk_level="HIGH",
            top_factors=[{"feature": "escalation_keywords", "contribution": 0.25}],
            explanation="High escalation risk detected.",
            feature_snapshot={"negative_sentiment_ratio": 0.65},
            temporal_risk=[{"segment": "late", "score": 85.0}],
            processing_time_seconds=0.005,
        )

        assert record.call_id == "CALL-DB-001"
        assert record.risk_score == 78.5
        assert record.risk_level == "HIGH"
        assert repr(record).startswith("<EscalationRisk")
