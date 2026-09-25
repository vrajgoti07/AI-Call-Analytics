#!/usr/bin/env python3
"""
AI Call Analytics — Speaker Diarization & Whisper Alignment CLI Tool.

Processes standardized call recordings (16 kHz, mono, PCM16 WAV), executes
Whisper speech-to-text and pyannote speaker diarization, aligns transcripts
with acoustic speaker boundaries, and outputs structured conversational turns.

Usage:
    python scripts/diarize_and_align.py --input data/processed/demo/demo_minds14_sample_0/audio.wav
    python scripts/diarize_and_align.py --demo-minds14
    python scripts/diarize_and_align.py --input path/to/call.wav --output output/aligned.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure utf-8 encoding on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_service.asr import WhisperConfig, WhisperTranscriber
from ai_service.diarization import (
    DiarizationConfig,
    DiarizationError,
    DiarizationModelLoadError,
    PyannoteDiarizer,
    TranscriptAligner,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.diarize")


def run_pipeline(
    audio_path: Path,
    output_path: Path | None = None,
    hf_token: str | None = None,
    whisper_model: str = "tiny",
    diarization_model: str = "pyannote/speaker-diarization-3.1",
    min_speakers: int | None = None,
    max_speakers: int | None = None,
    policy: str = "dominant",
) -> None:
    """Execute end-to-end Whisper ASR + Pyannote Diarization + Temporal Alignment."""
    print("=" * 70)
    print("  AI Call Analytics: End-to-End ASR + Diarization + Alignment")
    print("=" * 70)
    print(f"Target Audio: {audio_path.name}")

    t_start = time.perf_counter()

    # Step 1: Phase 3 Speech-to-Text (ASR)
    print("\n[Step 1/3] Running Whisper ASR...")
    asr_config = WhisperConfig(
        model_size=whisper_model,
        device="cpu",
        compute_type="int8",
        word_timestamps=True,
    )
    transcriber = WhisperTranscriber(asr_config)
    t_asr = time.perf_counter()
    transcription = transcriber.transcribe(audio_path)
    asr_elapsed = time.perf_counter() - t_asr
    print(f"   Transcribed {len(transcription.segments)} segments in {asr_elapsed:.2f}s (lang={transcription.language})")

    # Step 2: Phase 4 Speaker Diarization
    print("\n[Step 2/3] Running Pyannote Speaker Diarization...")
    diar_config = DiarizationConfig.from_env()
    if hf_token:
        diar_config.hf_token = hf_token
    diar_config.model_name = diarization_model
    diar_config.min_speakers = min_speakers
    diar_config.max_speakers = max_speakers
    diar_config.cross_speaker_policy = policy

    diarizer = PyannoteDiarizer(diar_config)
    t_diar = time.perf_counter()
    try:
        diarization = diarizer.diarize(audio_path)
        diar_elapsed = time.perf_counter() - t_diar
        print(f"   Diarization complete in {diar_elapsed:.2f}s:")
        print(f"   Found {len(diarization.speakers)} speakers across {len(diarization.speaker_segments)} segments")
        print(f"   Multi-speaker overlap: {diarization.overlap_duration:.2f}s")
    except DiarizationModelLoadError as exc:
        print(f"\n   [Warning] Could not load pyannote model ({exc}).", file=sys.stderr)
        print("   If you have not accepted user conditions on HuggingFace for this model,", file=sys.stderr)
        print(f"   please visit https://huggingface.co/{diarization_model} and accept terms.", file=sys.stderr)
        return

    # Step 3: Phase 4 Temporal Alignment
    print("\n[Step 3/3] Aligning Whisper Transcripts with Diarization Segments...")
    aligner = TranscriptAligner(diar_config)
    t_align = time.perf_counter()
    attributed_transcript = aligner.align(transcription, diarization)
    align_elapsed = time.perf_counter() - t_align
    total_elapsed = time.perf_counter() - t_start

    # Print Summary Results
    print("\n" + "=" * 70)
    print("  Conversational Speaker-Attributed Transcript")
    print("=" * 70)
    print(attributed_transcript.full_text)
    print("=" * 70)

    print("\nSpeaker Conversational Statistics:")
    for spk, stats in attributed_transcript.speaker_stats.items():
        print(
            f"   {spk}: {stats.segment_count} segments | "
            f"{stats.total_speaking_time:.2f}s speech | "
            f"{stats.speech_percentage:.1f}% conversation share"
        )

    print(f"\nPerformance Telemetry:")
    print(f"   Audio Duration:    {transcription.duration_seconds:.2f}s")
    print(f"   ASR Time:          {asr_elapsed:.2f}s")
    print(f"   Diarization Time:  {diar_elapsed:.2f}s")
    print(f"   Alignment Time:    {align_elapsed * 1000:.2f}ms")
    print(f"   Total Pipeline:    {total_elapsed:.2f}s")
    print(f"   Total RTF:         {total_elapsed / max(transcription.duration_seconds, 1e-4):.3f}x")

    if attributed_transcript.warnings:
        print(f"\nDiagnostics & Warnings:")
        for w in attributed_transcript.warnings:
            print(f"   - {w}")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(attributed_transcript.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\nWrote full structured transcript to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-End ASR + Speaker Diarization + Alignment.")
    parser.add_argument("--input", "-i", type=str, help="Path to input standardized WAV audio file")
    parser.add_argument("--output", "-o", type=str, help="Destination JSON file for structured output")
    parser.add_argument("--hf-token", type=str, help="Hugging Face access token")
    parser.add_argument("--whisper-model", type=str, default="tiny", help="Whisper model size")
    parser.add_argument("--diarization-model", type=str, default="pyannote/speaker-diarization-3.1", help="Pyannote model")
    parser.add_argument("--min-speakers", type=int, help="Minimum number of speakers")
    parser.add_argument("--max-speakers", type=int, help="Maximum number of speakers")
    parser.add_argument("--policy", choices=["dominant", "word_level"], default="dominant", help="Cross-speaker policy")
    parser.add_argument("--demo-minds14", action="store_true", help="Run demonstration using MInDS-14 demo recording")

    args = parser.parse_args()

    demo_flag = getattr(args, "demo_minds14", False)
    if demo_flag:
        audio_path = PROJECT_ROOT / "data" / "processed" / "demo" / "demo_minds14_sample_0" / "audio.wav"
        if not audio_path.exists():
            print(f"Demo file not found at {audio_path}. Run 'python scripts/preprocess_audio.py --demo-minds14' first.")
            sys.exit(1)
    elif args.input:
        audio_path = Path(args.input)
        if not audio_path.exists():
            print(f"Input file not found: {audio_path}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    out_file = Path(args.output) if args.output else None

    run_pipeline(
        audio_path=audio_path,
        output_path=out_file,
        hf_token=args.hf_token,
        whisper_model=args.whisper_model,
        diarization_model=args.diarization_model,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
        policy=args.policy,
    )


if __name__ == "__main__":
    main()
