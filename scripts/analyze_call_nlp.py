#!/usr/bin/env python3
"""
AI Call Analytics — Conversational NLP Analysis CLI Tool (Phase 5).

Analyzes speaker-attributed call transcripts for:
1. Turn-level, speaker-level, and call-level sentiment
2. 14-class MInDS-14 banking intent classification
3. Named Entity Recognition with speaker and turn mapping
4. Speaker conversational analytics

Usage:
    python scripts/analyze_call_nlp.py --demo
    python scripts/analyze_call_nlp.py --transcript output/aligned_call.json --output output/nlp_analysis.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_service.diarization.schema import SpeakerAttributedTranscript, SpeakerStats, SpeakerTurn
from ai_service.pipeline import NLPAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.analyze_call_nlp")


def create_demo_transcript() -> SpeakerAttributedTranscript:
    """Generate a realistic banking customer support transcript for demonstration."""
    turns = [
        SpeakerTurn(
            turn_id=1,
            speaker="SPEAKER_00",
            start=0.0,
            end=3.5,
            text="Thank you for calling Apex Bank support. My name is Sarah. How can I help you today?",
        ),
        SpeakerTurn(
            turn_id=2,
            speaker="SPEAKER_01",
            start=3.8,
            end=12.2,
            text="Hi Sarah, I have a big problem with my credit card. It was frozen yesterday when I tried to pay $450 at Best Buy, and I really need to unfreeze it.",
        ),
        SpeakerTurn(
            turn_id=3,
            speaker="SPEAKER_00",
            start=12.5,
            end=17.0,
            text="I completely understand your frustration and I would be glad to help unfreeze your card. Could you verify your account number?",
        ),
        SpeakerTurn(
            turn_id=4,
            speaker="SPEAKER_01",
            start=17.4,
            end=25.0,
            text="Sure, my account number is 9876543210. You can also reach me at john.doe@example.com or 555-123-4567.",
        ),
        SpeakerTurn(
            turn_id=5,
            speaker="SPEAKER_00",
            start=25.5,
            end=33.0,
            text="Thank you for providing that. I have lifted the security freeze on your card and verified the transaction. Is there anything else I can resolve for you?",
        ),
        SpeakerTurn(
            turn_id=6,
            speaker="SPEAKER_01",
            start=33.5,
            end=38.0,
            text="That was super quick! Thank you so much for your excellent help, Sarah. Have a wonderful day!",
        ),
    ]

    full_dialogue = "\n".join(f"{t.speaker}: {t.text}" for t in turns)
    speaker_stats = {
        "SPEAKER_00": SpeakerStats(
            speaker="SPEAKER_00",
            total_speaking_time=19.5,
            segment_count=3,
            speech_percentage=54.2,
        ),
        "SPEAKER_01": SpeakerStats(
            speaker="SPEAKER_01",
            total_speaking_time=16.5,
            segment_count=3,
            speech_percentage=45.8,
        ),
    }

    return SpeakerAttributedTranscript(
        full_text=full_dialogue,
        turns=turns,
        speakers=["SPEAKER_00", "SPEAKER_01"],
        speaker_stats=speaker_stats,
        total_turns=len(turns),
        audio_duration=38.5,
        speech_duration=36.0,
        transcription_metadata={"language": "en", "model": "whisper-base"},
        diarization_metadata={"model": "pyannote/speaker-diarization-3.1"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Call Analytics — NLP Analysis Tool")
    parser.add_argument("--transcript", type=str, help="Path to input speaker-attributed transcript JSON")
    parser.add_argument("--demo", action="store_true", help="Run analysis on a realistic built-in banking demo call")
    parser.add_argument("--output", type=str, help="Path to save output JSON")
    parser.add_argument("--top-k", type=int, default=3, help="Top-k intent candidates (default: 3)")

    args = parser.parse_args()

    if not args.transcript and not args.demo:
        parser.print_help()
        sys.exit(1)

    if args.demo:
        logger.info("Generating realistic customer support demo transcript...")
        transcript = create_demo_transcript()
    else:
        transcript_path = Path(args.transcript)
        if not transcript_path.exists():
            logger.error("Transcript file not found: %s", transcript_path)
            sys.exit(1)
        with open(transcript_path, encoding="utf-8") as f:
            data = json.load(f)
        # Parse turns
        turns = [
            SpeakerTurn(
                turn_id=t.get("turn_id", idx),
                speaker=t.get("speaker", "UNKNOWN"),
                start=float(t.get("start", 0.0)),
                end=float(t.get("end", 0.0)),
                text=t.get("text", ""),
            )
            for idx, t in enumerate(data.get("turns", []), 1)
        ]
        spk_stats = {
            k: SpeakerStats(
                speaker=v["speaker"],
                total_speaking_time=v["total_speaking_time"],
                segment_count=v["segment_count"],
                speech_percentage=v["speech_percentage"],
            )
            for k, v in data.get("speaker_stats", {}).items()
        }
        transcript = SpeakerAttributedTranscript(
            full_text=data.get("full_text", ""),
            turns=turns,
            speakers=data.get("speakers", []),
            speaker_stats=spk_stats,
            total_turns=len(turns),
            audio_duration=float(data.get("audio_duration", 0.0)),
            speech_duration=float(data.get("speech_duration", 0.0)),
            transcription_metadata=data.get("transcription_metadata", {}),
            diarization_metadata=data.get("diarization_metadata", {}),
        )

    analyzer = NLPAnalyzer()
    result = analyzer.analyze(transcript, top_k_intents=args.top_k)

    # Pretty print summary
    print("\n" + "=" * 70)
    print("AI CALL ANALYTICS — PHASE 5 NLP ANALYSIS REPORT")
    print("=" * 70)

    # 1. Status & Metadata
    meta = result.metadata
    print(f"\n[Lifecycle Status]: {meta.status if meta else 'UNKNOWN'}")
    print(f"Language:           {meta.language if meta else 'en'} (Supported: {meta.is_language_supported if meta else True})")
    print(f"Processing Time:    {meta.processing_time_seconds:.3f}s" if meta else "N/A")
    print(f"Total Turns:        {meta.total_turns if meta else len(transcript.turns)}")

    # 2. Intent Classification
    print("\n" + "-" * 40)
    print("INTENT CLASSIFICATION (MInDS-14 Taxonomy)")
    print("-" * 40)
    if result.intent:
        print(f"Primary Intent:     {result.intent.predicted_intent.upper()} (Confidence: {result.intent.confidence:.4f})")
        print("Top Candidates:")
        for cand in result.intent.top_k:
            bar = "#" * int(cand.confidence * 20)
            print(f"  • {cand.intent:<20} {cand.confidence:6.4f}  |{bar:<20}|")
    else:
        print("Intent: UNAVAILABLE")

    # 3. Sentiment Analysis
    print("\n" + "-" * 40)
    print("SENTIMENT ANALYSIS")
    print("-" * 40)
    if result.sentiment:
        print(f"Call-Level Sentiment: {result.sentiment.label} (Confidence: {result.sentiment.score:.4f})")
        print(f"Turn Distribution:    Positive: {result.sentiment.positive_ratio*100:.1f}%, Neutral: {result.sentiment.neutral_ratio*100:.1f}%, Negative: {result.sentiment.negative_ratio*100:.1f}%")
        print(f"Aggregation Method:   {result.sentiment.aggregation_method}")
        print("\nTurn-by-Turn Sentiment Timeline:")
        for turn in result.sentiment.turns:
            print(f"  [{turn.start:05.1f}s - {turn.end:05.1f}s] {turn.speaker}: {turn.label:<8} (score={turn.score:.2f}) | \"{turn.text[:45]}...\"")
    else:
        print("Sentiment: UNAVAILABLE")

    # 4. Named Entity Recognition
    print("\n" + "-" * 40)
    print("NAMED ENTITY RECOGNITION (NER)")
    print("-" * 40)
    if result.entities:
        print(f"Total Entities Found: {len(result.entities.entities)}")
        print(f"Category Breakdown:   {result.entities.entity_counts}")
        print("\nExtracted Entities (Attributed & PII Masked):")
        for ent in result.entities.entities:
            # Mask PII for terminal display
            display_text = ent.text
            if ent.label == "ACCOUNT_NUMBER":
                display_text = f"****{ent.text[-4:]}" if len(ent.text) >= 4 else "********"
            elif ent.label == "EMAIL":
                parts = ent.text.split("@")
                display_text = f"{parts[0][:2]}***@{parts[1]}" if len(parts) == 2 else "***@***"
            elif ent.label == "PHONE":
                display_text = f"***-***-{ent.text[-4:]}" if len(ent.text) >= 4 else "***-***-****"

            print(f"  • [{ent.label:<14}] \"{display_text}\" (Offsets: {ent.start}-{ent.end}, Speaker: {ent.speaker}, Turn: {ent.turn_id})")
    else:
        print("NER: UNAVAILABLE")

    # 5. Speaker Analysis Summary
    print("\n" + "-" * 40)
    print("SPEAKER CONVERSATIONAL TELEMETRY")
    print("-" * 40)
    for spk, stats in result.speaker_analysis.items():
        print(f"\nSpeaker: {spk}")
        print(f"  Speaking Time:     {stats.speaking_time:.1f}s ({stats.speech_percentage:.1f}%)")
        print(f"  Dominant Sentiment: {stats.sentiment_label or 'N/A'} (Score: {stats.sentiment_score or 0.0:.2f})")
        print(f"  Turn Counts:       Pos={stats.positive_turns}, Neu={stats.neutral_turns}, Neg={stats.negative_turns} (Neg Ratio={stats.negative_turn_ratio:.2f})")
        print(f"  Entities Mentioned: {stats.entity_count} {stats.entities_by_type}")

    print("\n" + "=" * 70)

    # Save to file if requested
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info("Complete CallNLPAnalysis saved to %s", out_path)


if __name__ == "__main__":
    main()
