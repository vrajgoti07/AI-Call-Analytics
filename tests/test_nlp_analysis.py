"""
AI Call Analytics — Unit and Integration Tests for Phase 5 NLP Analysis.

Validates:
1. Sentiment analysis (turn-level, speaker-level, call-level, timeline)
2. Intent classification (MInDS-14 14-class taxonomy, top-k candidate ranking)
3. Named Entity Recognition (SpaCy entities + banking regex rules, character offsets, speaker attribution)
4. Unified NLP pipeline orchestrator (multi-language handling, error isolation, speaker summaries)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from ai_service.diarization.schema import SpeakerAttributedTranscript, SpeakerStats, SpeakerTurn
from ai_service.intent import (
    MINDS14_INTENT_LABELS,
    IntentCandidate,
    IntentClassifier,
    IntentInferenceError,
    IntentModelLoadError,
    IntentPrediction,
)
from ai_service.ner import (
    SUPPORTED_ENTITY_LABELS,
    EntityExtractor,
    EntityItem,
    NERError,
    NERInferenceError,
    NERResult,
)
from ai_service.pipeline import (
    AnalysisStatus,
    CallNLPAnalysis,
    ComponentStatus,
    NLPAnalyzer,
    SpeakerAnalysisSummary,
)
from ai_service.sentiment import (
    CallSentiment,
    SentimentAnalyzer,
    SentimentError,
    SentimentInferenceError,
    SentimentTimelinePoint,
    SpeakerSentiment,
    TurnSentiment,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_speaker_turns() -> list[SpeakerTurn]:
    """Sample speaker turns representing a banking customer service call."""
    return [
        SpeakerTurn(
            turn_id=1,
            speaker="SPEAKER_00",
            start=0.0,
            end=4.0,
            text="Thank you for calling customer service. How can I help you?",
        ),
        SpeakerTurn(
            turn_id=2,
            speaker="SPEAKER_01",
            start=4.5,
            end=12.0,
            text="Hi, I am having a terrible problem with my card. It was frozen yesterday and I need to pay $250.",
        ),
        SpeakerTurn(
            turn_id=3,
            speaker="SPEAKER_00",
            start=12.5,
            end=18.0,
            text="I would be glad to help unfreeze your card. Could you verify your account number?",
        ),
        SpeakerTurn(
            turn_id=4,
            speaker="SPEAKER_01",
            start=18.5,
            end=25.0,
            text="Yes, my account is 1234567890. You can reach me at user@example.com or 555-234-5678.",
        ),
        SpeakerTurn(
            turn_id=5,
            speaker="SPEAKER_01",
            start=25.5,
            end=29.0,
            text="Thank you so much, that is wonderful!",
        ),
    ]


@pytest.fixture
def sample_transcript(sample_speaker_turns: list[SpeakerTurn]) -> SpeakerAttributedTranscript:
    """Sample SpeakerAttributedTranscript from Phase 4 alignment."""
    full_text = "\n".join(f"{t.speaker}: {t.text}" for t in sample_speaker_turns)
    speaker_stats = {
        "SPEAKER_00": SpeakerStats(
            speaker="SPEAKER_00",
            total_speaking_time=9.5,
            segment_count=2,
            speech_percentage=43.2,
        ),
        "SPEAKER_01": SpeakerStats(
            speaker="SPEAKER_01",
            total_speaking_time=12.5,
            segment_count=3,
            speech_percentage=56.8,
        ),
    }
    return SpeakerAttributedTranscript(
        full_text=full_text,
        turns=sample_speaker_turns,
        speakers=["SPEAKER_00", "SPEAKER_01"],
        speaker_stats=speaker_stats,
        total_turns=len(sample_speaker_turns),
        audio_duration=30.0,
        speech_duration=22.0,
        transcription_metadata={"language": "en", "model": "whisper-base"},
        diarization_metadata={"model": "pyannote/speaker-diarization-3.1"},
    )


# ============================================================================
# 1. Sentiment Analysis Tests (Step 4 - 11, 31)
# ============================================================================

class TestSentimentAnalysis:
    """Test suite for turn-level, speaker-level, and call-level sentiment analysis."""

    def test_lexicon_fallback_positive_and_negative(self) -> None:
        """Verify fallback rule-based classifier distinguishes positive and negative sentiment."""
        analyzer = SentimentAnalyzer(pipeline=None, use_fallback=True)
        # Mock _get_pipeline returning None so lexicon is used
        with patch.object(analyzer, "_get_pipeline", return_value=None):
            label_pos, score_pos = analyzer.analyze_text("Thank you so much, this is wonderful and great!")
            assert label_pos == "POSITIVE"
            assert 0.0 <= score_pos <= 1.0

            label_neg, score_neg = analyzer.analyze_text("I have a terrible problem, my card is frozen and broken.")
            assert label_neg == "NEGATIVE"
            assert 0.0 <= score_neg <= 1.0

            label_neu, score_neu = analyzer.analyze_text("Could you state your account number?")
            assert label_neu == "NEUTRAL"
            assert 0.0 <= score_neu <= 1.0

    def test_empty_text_sentiment(self) -> None:
        """Verify empty or whitespace-only text returns NEUTRAL with confidence 1.0."""
        analyzer = SentimentAnalyzer(use_fallback=True)
        label, score = analyzer.analyze_text("   ")
        assert label == "NEUTRAL"
        assert score == 1.0

    def test_analyze_turns_empty(self) -> None:
        """Verify analyzing an empty turn list returns valid neutral CallSentiment."""
        analyzer = SentimentAnalyzer(use_fallback=True)
        res = analyzer.analyze_turns([])
        assert res.label == "NEUTRAL"
        assert res.score == 1.0
        assert len(res.turns) == 0
        assert len(res.speaker_sentiments) == 0

    def test_turn_and_speaker_aggregation(self, sample_speaker_turns: list[SpeakerTurn]) -> None:
        """Verify turn-level sentiment, timeline, and speaker-level aggregation."""
        # Create a mock pipeline returning predictable outputs
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"label": "POSITIVE", "score": 0.95},
            {"label": "NEGATIVE", "score": 0.88},
            {"label": "NEUTRAL", "score": 0.70},
            {"label": "NEUTRAL", "score": 0.65},
            {"label": "POSITIVE", "score": 0.98},
        ]

        analyzer = SentimentAnalyzer(pipeline=mock_pipe)
        result = analyzer.analyze_turns(sample_speaker_turns)

        assert isinstance(result, CallSentiment)
        assert len(result.turns) == 5
        assert len(result.timeline) == 5

        # Check turn labels
        assert result.turns[0].label == "POSITIVE"
        assert result.turns[1].label == "NEGATIVE"
        assert result.turns[4].label == "POSITIVE"

        # Check speaker aggregation
        assert "SPEAKER_00" in result.speaker_sentiments
        assert "SPEAKER_01" in result.speaker_sentiments

        spk0 = result.speaker_sentiments["SPEAKER_00"]
        assert spk0.positive_count == 1
        assert spk0.neutral_count == 1
        assert spk0.negative_count == 0

        spk1 = result.speaker_sentiments["SPEAKER_01"]
        assert spk1.negative_count == 1
        assert spk1.positive_count == 1

        # Check timeline timestamps
        assert result.timeline[0].timestamp == sample_speaker_turns[0].start
        assert result.timeline[1].timestamp == sample_speaker_turns[1].start

    def test_call_sentiment_serialization(self) -> None:
        """Verify to_dict produces valid, JSON-serializable dictionaries."""
        call_sent = CallSentiment(
            label="POSITIVE",
            score=0.92,
            positive_ratio=0.6,
            neutral_ratio=0.2,
            negative_ratio=0.2,
            turns=[
                TurnSentiment(
                    turn_id=1,
                    speaker="SPEAKER_00",
                    start=0.0,
                    end=2.0,
                    text="Hello",
                    label="POSITIVE",
                    score=0.92,
                )
            ],
            speaker_sentiments={
                "SPEAKER_00": SpeakerSentiment(
                    speaker="SPEAKER_00",
                    positive_count=1,
                    neutral_count=0,
                    negative_count=0,
                    positive_ratio=1.0,
                    neutral_ratio=0.0,
                    negative_ratio=0.0,
                    average_score=0.92,
                )
            },
            timeline=[
                SentimentTimelinePoint(
                    timestamp=0.0,
                    turn_id=1,
                    speaker="SPEAKER_00",
                    label="POSITIVE",
                    score=0.92,
                )
            ],
        )
        d = call_sent.to_dict()
        assert d["label"] == "POSITIVE"
        assert len(d["turns"]) == 1
        assert d["turns"][0]["label"] == "POSITIVE"
        assert "SPEAKER_00" in d["speaker_sentiments"]


# ============================================================================
# 2. Intent Classification Tests (Step 12 - 18, 32)
# ============================================================================

class TestIntentClassification:
    """Test suite for MInDS-14 intent classification."""

    def test_minds14_taxonomy_constants(self) -> None:
        """Verify official MInDS-14 taxonomy contains exactly 14 classes."""
        assert len(MINDS14_INTENT_LABELS) == 14
        assert "freeze" in MINDS14_INTENT_LABELS
        assert "pay_bill" in MINDS14_INTENT_LABELS
        assert "latest_transactions" in MINDS14_INTENT_LABELS
        assert "card_issues" in MINDS14_INTENT_LABELS

    def test_intent_prediction_empty_text(self) -> None:
        """Verify empty text returns unknown intent with 0.0 confidence."""
        classifier = IntentClassifier(auto_train=False)
        pred = classifier.predict("   ")
        assert pred.predicted_intent == "unknown"
        assert pred.confidence == 0.0
        assert len(pred.top_k) == 0

    def test_intent_prediction_with_mock_bundle(self) -> None:
        """Verify top-k intent ranking and candidate serialization."""
        mock_pipeline = MagicMock()
        # Mock predict_proba returning 14 probabilities
        import numpy as np
        probs = np.zeros(14)
        probs[9] = 0.85  # freeze
        probs[6] = 0.10  # card_issues
        probs[13] = 0.05  # pay_bill
        mock_pipeline.predict_proba.return_value = [probs]

        mock_bundle = {
            "pipeline": mock_pipeline,
            "classes": MINDS14_INTENT_LABELS,
        }

        classifier = IntentClassifier(model_bundle=mock_bundle)
        pred = classifier.predict("Please help, my credit card was frozen.", top_k=3)

        assert pred.predicted_intent == "freeze"
        assert pytest.approx(pred.confidence, abs=1e-3) == 0.85
        assert len(pred.top_k) == 3
        assert pred.top_k[0].intent == "freeze"
        assert pred.top_k[1].intent == "card_issues"
        assert pred.top_k[2].intent == "pay_bill"

        d = pred.to_dict()
        assert d["predicted_intent"] == "freeze"
        assert len(d["top_k"]) == 3

    def test_real_trained_intent_artifact(self) -> None:
        """Verify inference using the persisted trained model artifact."""
        from pathlib import Path
        model_path = Path("models/intent/minds14_intent_model.joblib")
        if not model_path.exists():
            pytest.skip("Trained intent model artifact not found.")

        classifier = IntentClassifier(model_path=model_path)
        # Test freeze intent
        pred_freeze = classifier.predict("I want to freeze my credit card immediately because I lost it.", top_k=3)
        assert pred_freeze.predicted_intent in MINDS14_INTENT_LABELS
        assert 0.0 <= pred_freeze.confidence <= 1.0
        assert len(pred_freeze.top_k) == 3

        # Test balance intent
        pred_balance = classifier.predict("Can you please tell me how much money is currently left in my account?", top_k=3)
        assert pred_balance.predicted_intent in MINDS14_INTENT_LABELS
        assert 0.0 <= pred_balance.confidence <= 1.0


# ============================================================================
# 3. Named Entity Recognition Tests (Step 19 - 24, 33)
# ============================================================================

class TestNamedEntityRecognition:
    """Test suite for Named Entity Recognition and regex pattern extraction."""

    def test_supported_entity_labels(self) -> None:
        """Verify supported entity types include banking and standard entities."""
        assert "PERSON" in SUPPORTED_ENTITY_LABELS
        assert "MONEY" in SUPPORTED_ENTITY_LABELS
        assert "EMAIL" in SUPPORTED_ENTITY_LABELS
        assert "PHONE" in SUPPORTED_ENTITY_LABELS
        assert "ACCOUNT_NUMBER" in SUPPORTED_ENTITY_LABELS

    def test_empty_text_ner(self) -> None:
        """Verify empty text produces no entities without error."""
        extractor = EntityExtractor()
        ents = extractor.extract_from_text("   ")
        assert ents == []

    def test_regex_banking_entities(self) -> None:
        """Verify email, phone, and account number extraction with exact character offsets."""
        extractor = EntityExtractor()
        text = "Contact support at help@apexbank.com or call 555-876-5432 regarding account 9876543210."
        ents = extractor.extract_from_text(text, speaker="SPEAKER_00", turn_id=1)

        labels = {e.label for e in ents}
        assert "EMAIL" in labels
        assert "PHONE" in labels
        assert "ACCOUNT_NUMBER" in labels

        # Validate exact string matching by slice
        for e in ents:
            assert text[e.start:e.end] == e.text
            assert e.speaker == "SPEAKER_00"
            assert e.turn_id == 1

    def test_spacy_named_entities(self) -> None:
        """Verify SpaCy detects money and dates."""
        extractor = EntityExtractor()
        text = "I transferred $350 to John Smith on January 15th."
        ents = extractor.extract_from_text(text)

        labels = [e.label for e in ents]
        # At least MONEY or DATE should be extracted by en_core_web_sm
        assert any(l in ["MONEY", "DATE", "PERSON"] for l in labels)

        # Offsets must be exact slices
        for e in ents:
            assert text[e.start:e.end] == e.text

    def test_extract_from_turns(self, sample_speaker_turns: list[SpeakerTurn]) -> None:
        """Verify multi-turn entity extraction preserves speaker and turn attribution."""
        extractor = EntityExtractor()
        result = extractor.extract_from_turns(sample_speaker_turns)

        assert isinstance(result, NERResult)
        assert len(result.entities) > 0

        # Check turn_id and speaker attribution
        for e in result.entities:
            assert e.speaker in ["SPEAKER_00", "SPEAKER_01"]
            assert e.turn_id in [1, 2, 3, 4, 5]

        # Check entity serialization
        d = result.to_dict()
        assert "entities" in d
        assert "entity_counts" in d


# ============================================================================
# 4. Unified NLP Orchestrator Tests (Step 25 - 30)
# ============================================================================

class TestNLPAnalyzerOrchestrator:
    """Test suite for the unified NLPAnalyzer orchestrator."""

    def test_complete_analysis_success(self, sample_transcript: SpeakerAttributedTranscript) -> None:
        """Verify end-to-end analysis produces valid CallNLPAnalysis with SUCCESS status."""
        analyzer = NLPAnalyzer()
        res = analyzer.analyze(sample_transcript)

        assert isinstance(res, CallNLPAnalysis)
        assert res.metadata is not None
        assert res.metadata.status in [AnalysisStatus.SUCCESS.value, AnalysisStatus.PARTIAL_SUCCESS.value]
        assert res.metadata.is_language_supported is True
        assert res.metadata.language == "en"

        # Check subcomponents
        assert res.sentiment is not None
        assert res.intent is not None
        assert res.entities is not None

        # Check speaker telemetry
        assert "SPEAKER_00" in res.speaker_analysis
        assert "SPEAKER_01" in res.speaker_analysis
        spk0 = res.speaker_analysis["SPEAKER_00"]
        assert spk0.speaking_time > 0
        assert spk0.speech_percentage > 0

        # Check serialization
        d = res.to_dict()
        assert d["metadata"]["status"] in ["SUCCESS", "PARTIAL_SUCCESS"]
        assert "sentiment" in d
        assert "intent" in d
        assert "entities" in d
        assert "speaker_analysis" in d

    def test_unsupported_language_policy(self, sample_transcript: SpeakerAttributedTranscript) -> None:
        """Verify non-English call is flagged as NOT_SUPPORTED with clear warning (Step 25)."""
        sample_transcript.transcription_metadata["language"] = "de"  # German
        analyzer = NLPAnalyzer()
        res = analyzer.analyze(sample_transcript)

        assert res.metadata is not None
        assert res.metadata.status == AnalysisStatus.NOT_SUPPORTED.value
        assert res.metadata.is_language_supported is False
        assert any("not officially supported" in w for w in res.warnings)

    def test_error_isolation_sentiment_failure(self, sample_transcript: SpeakerAttributedTranscript) -> None:
        """Verify error in Sentiment does not fail Intent or NER (Step 29)."""
        mock_sentiment = MagicMock()
        mock_sentiment.analyze_turns.side_effect = RuntimeError("GPU memory exhausted")

        analyzer = NLPAnalyzer(sentiment_analyzer=mock_sentiment)
        res = analyzer.analyze(sample_transcript)

        assert res.sentiment is None
        assert res.intent is not None  # Succeeded
        assert res.entities is not None  # Succeeded
        assert res.metadata.status == AnalysisStatus.PARTIAL_SUCCESS.value
        assert res.metadata.component_statuses["sentiment"].status == ComponentStatus.FAILED.value
        assert res.metadata.component_statuses["intent"].status == ComponentStatus.SUCCESS.value
        assert res.metadata.component_statuses["ner"].status == ComponentStatus.SUCCESS.value

    def test_error_isolation_ner_failure(self, sample_transcript: SpeakerAttributedTranscript) -> None:
        """Verify error in NER does not fail Sentiment or Intent (Step 29)."""
        mock_ner = MagicMock()
        mock_ner.extract_from_turns.side_effect = ValueError("Corrupted token stream")

        analyzer = NLPAnalyzer(entity_extractor=mock_ner)
        res = analyzer.analyze(sample_transcript)

        assert res.entities is None
        assert res.sentiment is not None  # Succeeded
        assert res.intent is not None  # Succeeded
        assert res.metadata.status == AnalysisStatus.PARTIAL_SUCCESS.value
        assert res.metadata.component_statuses["ner"].status == ComponentStatus.FAILED.value
