#!/usr/bin/env python3
"""
AI Call Analytics — Escalation Risk Detection CLI Tool (Phase 8).

Analyzes customer calls for escalation signals across sentiment trajectories,
explicit trigger keywords, intent friction, acoustic dynamics, and repetition.

Usage:
    python scripts/detect_escalation.py --demo
    python scripts/detect_escalation.py --train-demo-supervised
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from ai_service.diarization.schema import (
    SpeakerAttributedTranscript,
    SpeakerStats,
    SpeakerTurn,
)
from ai_service.intent.schema import IntentCandidate, IntentPrediction
from ai_service.ner.schema import EntityItem, NERResult
from ai_service.risk import (
    EscalationConfig,
    EscalationFeatures,
    EscalationRiskService,
    SupervisedEscalationModel,
)
from ai_service.sentiment.schema import (
    CallSentiment,
    SentimentTimelinePoint,
    SpeakerSentiment,
    TurnSentiment,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.detect_escalation")


def create_demo_calls() -> list[dict[str, Any]]:
    """Create three realistic banking calls with distinct risk profiles."""
    calls = []

    # ---------------------------------------------------------
    # Call 1: High-Risk Escalation
    # - Customer's debit card frozen while abroad
    # - Multiple failed transactions
    # - Deteriorating sentiment (neutral -> negative -> strongly negative)
    # - Explicit supervisor / complaint demands
    # - Speech overlap / interruptions
    # ---------------------------------------------------------
    turns_1 = [
        SpeakerTurn(
            turn_id=1,
            speaker="SPEAKER_00",
            start=0.0,
            end=3.5,
            text="Thank you for calling Metro Bank. My name is Alex, how may I assist you today?",
        ),
        SpeakerTurn(
            turn_id=2,
            speaker="SPEAKER_01",
            start=4.0,
            end=12.2,
            text="Hi Alex, my debit card was declined at an ATM here in London and now my online app says account is frozen.",
        ),
        SpeakerTurn(
            turn_id=3,
            speaker="SPEAKER_00",
            start=12.5,
            end=18.0,
            text="I see. Under security policy, international activity triggers a freeze until verification.",
        ),
        SpeakerTurn(
            turn_id=4,
            speaker="SPEAKER_01",
            start=18.2,
            end=28.5,
            text="I already notified you before traveling! This is ridiculous, I am stranded and cannot pay for my hotel.",
        ),
        SpeakerTurn(
            turn_id=5,
            speaker="SPEAKER_00",
            start=28.0,
            end=34.0,
            text="I understand your frustration, but fraud security requires an international review queue.",
        ),
        SpeakerTurn(
            turn_id=6,
            speaker="SPEAKER_01",
            start=33.5,
            end=48.0,
            text="That is unacceptable! I want to speak to a manager right now. Transfer me to your supervisor or I will file an official complaint!",
        ),
    ]

    sentiment_turns_1 = [
        TurnSentiment(turn_id=1, speaker="SPEAKER_00", start=0.0, end=3.5, text=turns_1[0].text, label="POSITIVE", score=0.88),
        TurnSentiment(turn_id=2, speaker="SPEAKER_01", start=4.0, end=12.2, text=turns_1[1].text, label="NEUTRAL", score=0.65),
        TurnSentiment(turn_id=3, speaker="SPEAKER_00", start=12.5, end=18.0, text=turns_1[2].text, label="NEUTRAL", score=0.72),
        TurnSentiment(turn_id=4, speaker="SPEAKER_01", start=18.2, end=28.5, text=turns_1[3].text, label="NEGATIVE", score=0.85),
        TurnSentiment(turn_id=5, speaker="SPEAKER_00", start=28.0, end=34.0, text=turns_1[4].text, label="NEUTRAL", score=0.60),
        TurnSentiment(turn_id=6, speaker="SPEAKER_01", start=33.5, end=48.0, text=turns_1[5].text, label="NEGATIVE", score=0.96),
    ]

    call_1 = {
        "call_id": "CALL-2026-HIGH-001",
        "title": "Severe Card Freeze & Stranded Customer Dispute",
        "transcript": SpeakerAttributedTranscript(
            full_text="\n".join(f"{t.speaker}: {t.text}" for t in turns_1),
            turns=turns_1,
            speakers=["SPEAKER_00", "SPEAKER_01"],
            speaker_stats={
                "SPEAKER_00": SpeakerStats(speaker="SPEAKER_00", total_speaking_time=15.0, segment_count=3, speech_percentage=35.0),
                "SPEAKER_01": SpeakerStats(speaker="SPEAKER_01", total_speaking_time=27.9, segment_count=3, speech_percentage=65.0),
            },
            total_turns=6,
            audio_duration=48.5,
            speech_duration=42.9,
            overlap_duration=5.5,
            overlap_detected=True,
        ),
        "sentiment": CallSentiment(
            label="NEGATIVE",
            score=0.82,
            positive_ratio=0.17,
            neutral_ratio=0.50,
            negative_ratio=0.33,
            turns=sentiment_turns_1,
        ),
        "intent": IntentPrediction(
            predicted_intent="freeze",
            confidence=0.92,
            top_k=[
                IntentCandidate("freeze", 0.92),
                IntentCandidate("card_issues", 0.05),
            ],
        ),
        "entities": NERResult(
            entities=[
                EntityItem(1, "London", "GPE", 0, 6, "SPEAKER_01", 2),
                EntityItem(2, "Alex", "PERSON", 0, 4, "SPEAKER_00", 1),
            ],
            entity_counts={"GPE": 1, "PERSON": 1},
        ),
        "themes": [{"label": "CARD / ACCOUNT FREEZE / YESTERDAY UNBLOCK", "keywords": ["freeze", "card", "unblock"]}],
    }
    calls.append(call_1)

    # ---------------------------------------------------------
    # Call 2: Medium-Risk Escalation
    # - Mobile banking app error when attempting a transfer
    # - Annoyed customer tone, moderate repetition
    # - No explicit threat or supervisor demand
    # ---------------------------------------------------------
    turns_2 = [
        SpeakerTurn(
            turn_id=1,
            speaker="SPEAKER_00",
            start=0.0,
            end=3.0,
            text="Thank you for contacting customer support. How can I help you?",
        ),
        SpeakerTurn(
            turn_id=2,
            speaker="SPEAKER_01",
            start=3.5,
            end=10.0,
            text="Hi, I've been trying to send a bill payment through your mobile app but it keeps showing an error 502.",
        ),
        SpeakerTurn(
            turn_id=3,
            speaker="SPEAKER_00",
            start=10.5,
            end=16.0,
            text="Have you attempted to restart the application or clear your browser cache?",
        ),
        SpeakerTurn(
            turn_id=4,
            speaker="SPEAKER_01",
            start=16.5,
            end=25.0,
            text="Yes, I did that twice already. The app keeps crashing every single time I press confirm payment.",
        ),
        SpeakerTurn(
            turn_id=5,
            speaker="SPEAKER_00",
            start=25.5,
            end=31.0,
            text="Understood. Let me initiate a ticket with our mobile app technical team to investigate.",
        ),
    ]

    sentiment_turns_2 = [
        TurnSentiment(turn_id=1, speaker="SPEAKER_00", start=0.0, end=3.0, text=turns_2[0].text, label="POSITIVE", score=0.75),
        TurnSentiment(turn_id=2, speaker="SPEAKER_01", start=3.5, end=10.0, text=turns_2[1].text, label="NEUTRAL", score=0.70),
        TurnSentiment(turn_id=3, speaker="SPEAKER_00", start=10.5, end=16.0, text=turns_2[2].text, label="NEUTRAL", score=0.80),
        TurnSentiment(turn_id=4, speaker="SPEAKER_01", start=16.5, end=25.0, text=turns_2[3].text, label="NEGATIVE", score=0.65),
        TurnSentiment(turn_id=5, speaker="SPEAKER_00", start=25.5, end=31.0, text=turns_2[4].text, label="NEUTRAL", score=0.85),
    ]

    call_2 = {
        "call_id": "CALL-2026-MED-002",
        "title": "Mobile App Crash on Payment Confirmation",
        "transcript": SpeakerAttributedTranscript(
            full_text="\n".join(f"{t.speaker}: {t.text}" for t in turns_2),
            turns=turns_2,
            speakers=["SPEAKER_00", "SPEAKER_01"],
            speaker_stats={
                "SPEAKER_00": SpeakerStats(speaker="SPEAKER_00", total_speaking_time=14.0, segment_count=3, speech_percentage=48.0),
                "SPEAKER_01": SpeakerStats(speaker="SPEAKER_01", total_speaking_time=15.0, segment_count=2, speech_percentage=52.0),
            },
            total_turns=5,
            audio_duration=31.5,
            speech_duration=29.0,
            overlap_duration=1.2,
            overlap_detected=False,
        ),
        "sentiment": CallSentiment(
            label="NEUTRAL",
            score=0.70,
            positive_ratio=0.20,
            neutral_ratio=0.60,
            negative_ratio=0.20,
            turns=sentiment_turns_2,
        ),
        "intent": IntentPrediction(
            predicted_intent="app_error",
            confidence=0.88,
            top_k=[
                IntentCandidate("app_error", 0.88),
                IntentCandidate("pay_bill", 0.08),
            ],
        ),
        "entities": NERResult(
            entities=[EntityItem(1, "502", "CARDINAL", 0, 3, "SPEAKER_01", 2)],
            entity_counts={"CARDINAL": 1},
        ),
        "themes": [{"label": "APP / ERROR / PAYMENT MOBILE", "keywords": ["error", "app", "payment"]}],
    }
    calls.append(call_2)

    # ---------------------------------------------------------
    # Call 3: Low-Risk Standard Inquiry
    # - Calm checking account balance inquiry
    # - Positive sentiment trajectory
    # - Clear resolution, no friction
    # ---------------------------------------------------------
    turns_3 = [
        SpeakerTurn(
            turn_id=1,
            speaker="SPEAKER_00",
            start=0.0,
            end=3.2,
            text="Good afternoon, welcome to Premier Banking. How may I direct your call?",
        ),
        SpeakerTurn(
            turn_id=2,
            speaker="SPEAKER_01",
            start=3.5,
            end=8.0,
            text="Hi there! I would just like to quickly check my current checking balance please.",
        ),
        SpeakerTurn(
            turn_id=3,
            speaker="SPEAKER_00",
            start=8.5,
            end=14.0,
            text="Certainly! Your checking account balance is currently three thousand four hundred dollars.",
        ),
        SpeakerTurn(
            turn_id=4,
            speaker="SPEAKER_01",
            start=14.5,
            end=18.0,
            text="Wonderful, that's exactly what I needed to confirm. Thank you so much!",
        ),
        SpeakerTurn(
            turn_id=5,
            speaker="SPEAKER_00",
            start=18.2,
            end=21.0,
            text="You're very welcome! Have a wonderful day.",
        ),
    ]

    sentiment_turns_3 = [
        TurnSentiment(turn_id=1, speaker="SPEAKER_00", start=0.0, end=3.2, text=turns_3[0].text, label="POSITIVE", score=0.85),
        TurnSentiment(turn_id=2, speaker="SPEAKER_01", start=3.5, end=8.0, text=turns_3[1].text, label="NEUTRAL", score=0.90),
        TurnSentiment(turn_id=3, speaker="SPEAKER_00", start=8.5, end=14.0, text=turns_3[2].text, label="NEUTRAL", score=0.92),
        TurnSentiment(turn_id=4, speaker="SPEAKER_01", start=14.5, end=18.0, text=turns_3[3].text, label="POSITIVE", score=0.96),
        TurnSentiment(turn_id=5, speaker="SPEAKER_00", start=18.2, end=21.0, text=turns_3[4].text, label="POSITIVE", score=0.95),
    ]

    call_3 = {
        "call_id": "CALL-2026-LOW-003",
        "title": "Routine Account Balance Confirmation",
        "transcript": SpeakerAttributedTranscript(
            full_text="\n".join(f"{t.speaker}: {t.text}" for t in turns_3),
            turns=turns_3,
            speakers=["SPEAKER_00", "SPEAKER_01"],
            speaker_stats={
                "SPEAKER_00": SpeakerStats(speaker="SPEAKER_00", total_speaking_time=11.5, segment_count=3, speech_percentage=55.0),
                "SPEAKER_01": SpeakerStats(speaker="SPEAKER_01", total_speaking_time=8.0, segment_count=2, speech_percentage=45.0),
            },
            total_turns=5,
            audio_duration=21.5,
            speech_duration=19.5,
            overlap_duration=0.2,
            overlap_detected=False,
        ),
        "sentiment": CallSentiment(
            label="POSITIVE",
            score=0.92,
            positive_ratio=0.60,
            neutral_ratio=0.40,
            negative_ratio=0.0,
            turns=sentiment_turns_3,
        ),
        "intent": IntentPrediction(
            predicted_intent="balance",
            confidence=0.97,
            top_k=[
                IntentCandidate("balance", 0.97),
                IntentCandidate("latest_transactions", 0.02),
            ],
        ),
        "entities": NERResult(
            entities=[EntityItem(1, "$3,400", "MONEY", 0, 6, "SPEAKER_00", 3)],
            entity_counts={"MONEY": 1},
        ),
        "themes": [{"label": "BALANCE / AVAILABLE / CHECKING ACCOUNT", "keywords": ["balance", "checking", "available"]}],
    }
    calls.append(call_3)

    return calls


def run_demo() -> None:
    """Run escalation detection on demo calls."""
    logger.info("Initializing EscalationRiskService...")
    config = EscalationConfig()
    service = EscalationRiskService(config)

    calls = create_demo_calls()

    print("\n" + "=" * 80)
    print("                PHASE 8 — ESCALATION RISK DETECTION SUMMARY")
    print("=" * 80)
    print(f"Model Type:        {config.model_type.upper()}")
    print(f"Model Name:        {config.model_name}")
    print(f"Feature Schema:    {config.feature_schema_version}")
    print(f"Thresholds:        LOW < {config.low_threshold:.0f} <= MEDIUM < {config.high_threshold:.0f} <= HIGH")
    print("=" * 80)

    for call_data in calls:
        pred = service.analyze(
            call_id=call_data["call_id"],
            transcript=call_data["transcript"],
            sentiment=call_data["sentiment"],
            intent=call_data["intent"],
            entities=call_data["entities"],
            themes=call_data["themes"],
        )

        level_str = pred.risk_level.value
        print(f"\n[Call]: {pred.call_id} — {call_data['title']}")
        print(f"  Risk Score:       {pred.risk_score:.1f} / 100 ({pred.risk_probability:.2%})")
        print(f"  Risk Level:       {level_str}")
        print(f"  Processing Time:  {pred.processing_time_seconds:.3f}s")
        print("  Key Risk Factors:")
        for factor in pred.top_factors[:3]:
            print(f"    * {factor.display_name} (impact: {factor.contribution:+.3f}): {factor.description}")
        print("  Evidence Explanation:")
        for line in pred.explanation.splitlines():
            print(f"    {line}")
        print("-" * 80)


def run_train_supervised() -> None:
    """Demonstrate supervised model training on synthetic multi-call dataset with leakage prevention."""
    logger.info("Generating synthetic training dataset for supervised evaluation...")
    np.random.seed(42)

    # 40 distinct calls, each generating 1-3 turns/chunks
    call_ids: list[str] = []
    features_list: list[list[float]] = []
    labels: list[int] = []

    for call_idx in range(40):
        c_id = f"CALL-TRAIN-{call_idx:03d}"
        # 30% escalation rate
        is_escalated = 1 if call_idx % 3 == 0 else 0

        # Generate 1 to 2 samples per call to verify GroupKFold leakage prevention
        n_chunks = np.random.randint(1, 3)
        for _ in range(n_chunks):
            feat = EscalationFeatures(
                call_duration=float(np.random.uniform(60, 300)),
                turn_count=int(np.random.randint(4, 25)),
                speaker_count=2,
                speech_duration=float(np.random.uniform(50, 280)),
                overlap_duration=float(np.random.uniform(5, 25) if is_escalated else np.random.uniform(0, 4)),
                overlap_ratio=float(np.random.uniform(0.10, 0.25) if is_escalated else np.random.uniform(0.0, 0.05)),
                avg_turn_duration=float(np.random.uniform(8, 20)),
                max_turn_duration=float(np.random.uniform(45, 80) if is_escalated else np.random.uniform(10, 35)),
                speaker_switch_count=int(np.random.randint(3, 20)),
                negative_sentiment_ratio=float(np.random.uniform(0.5, 0.9) if is_escalated else np.random.uniform(0.0, 0.25)),
                strong_negative_ratio=float(np.random.uniform(0.3, 0.7) if is_escalated else 0.0),
                positive_sentiment_ratio=float(np.random.uniform(0.0, 0.15) if is_escalated else np.random.uniform(0.4, 0.9)),
                sentiment_volatility=float(np.random.uniform(0.3, 0.6)),
                min_sentiment_score=float(np.random.uniform(-0.95, -0.6) if is_escalated else np.random.uniform(-0.3, 0.2)),
                final_turn_sentiment=float(np.random.uniform(-0.95, -0.4) if is_escalated else np.random.uniform(0.1, 0.9)),
                early_sentiment_score=float(np.random.uniform(-0.2, 0.4)),
                middle_sentiment_score=float(np.random.uniform(-0.5, 0.2)),
                late_sentiment_score=float(np.random.uniform(-0.9, -0.4) if is_escalated else np.random.uniform(0.2, 0.8)),
                sentiment_slope=float(np.random.uniform(-0.8, -0.2) if is_escalated else np.random.uniform(0.1, 0.6)),
                is_problem_intent=is_escalated,
                intent_confidence=float(np.random.uniform(0.8, 0.98)),
                escalation_keyword_count=int(np.random.randint(1, 4) if is_escalated else 0),
                repetition_score=float(np.random.uniform(0.3, 0.6) if is_escalated else np.random.uniform(0.05, 0.2)),
                theme_count=int(np.random.randint(1, 3)),
                has_problem_theme=is_escalated,
                entity_count=int(np.random.randint(1, 5)),
                account_number_count=int(np.random.randint(1, 3) if is_escalated else 0),
                money_entity_count=int(np.random.randint(0, 3)),
            )
            call_ids.append(c_id)
            features_list.append(feat.to_feature_vector())
            labels.append(is_escalated)

    X = np.array(features_list, dtype=np.float32)
    y = np.array(labels, dtype=np.int32)

    model = SupervisedEscalationModel()
    report = model.train(X, y, call_ids=call_ids, n_splits=5)

    print("\n" + "=" * 80)
    print("         SUPERVISED ESCALATION MODEL EVALUATION REPORT (GroupKFold)")
    print("=" * 80)
    print(f"Total Samples:       {report.sample_count} across {len(set(call_ids))} distinct calls")
    print(f"Class Distribution:  {report.positive_count} Escalations ({report.positive_count / report.sample_count:.1%}), {report.negative_count} Normal")
    print(f"Accuracy:            {report.accuracy:.4f}")
    print(f"Precision:           {report.precision:.4f}")
    print(f"Recall:              {report.recall:.4f}")
    print(f"F1 Score:            {report.f1:.4f}")
    print(f"ROC-AUC:             {report.roc_auc:.4f}" if report.roc_auc is not None else "ROC-AUC: N/A")
    print(f"PR-AUC:              {report.pr_auc:.4f}" if report.pr_auc is not None else "PR-AUC: N/A")
    print(f"Confusion Matrix:    TN={report.confusion_matrix[0][0]}, FP={report.confusion_matrix[0][1]}")
    print(f"                     FN={report.confusion_matrix[1][0]}, TP={report.confusion_matrix[1][1]}")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Call Analytics Escalation Risk CLI")
    parser.add_argument("--demo", action="store_true", help="Run escalation detection on demo banking calls")
    parser.add_argument("--train-demo-supervised", action="store_true", help="Train and evaluate supervised model")

    args = parser.parse_args()

    if args.train_demo_supervised:
        run_train_supervised()
    else:
        run_demo()


if __name__ == "__main__":
    main()
