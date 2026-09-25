#!/usr/bin/env python3
"""
AI Call Analytics — Speech-to-Text (ASR) CLI Tool.

Transcribes preprocessed standardized call audio (16 kHz, mono, PCM_16 WAV)
using faster-whisper and produces structured transcripts with segments, timestamps,
and processing metrics.

Usage:
    python scripts/transcribe_audio.py --input data/processed/demo/demo_minds14_sample_0/audio.wav
    python scripts/transcribe_audio.py --demo-minds14 --model tiny
    python scripts/transcribe_audio.py --input path/to/call.wav --model base --language en
"""

from __future__ import annotations

import argparse
import json
import logging
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

from ai_service.asr import (
    WhisperConfig,
    WhisperModelManager,
    WhisperTranscriber,
    ASRError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.transcribe")


def run_demo_minds14(
    model_size: str = "tiny",
    device: str = "auto",
    compute_type: str = "auto",
) -> None:
    """Preprocess and transcribe a sample MInDS-14 call to demonstrate Phase 1 -> Phase 2 -> Phase 3."""
    print("=" * 70)
    print("  MInDS-14 -> Audio Preprocessing -> Whisper ASR Pipeline Demo")
    print("=" * 70)

    demo_wav_path = PROJECT_ROOT / "data" / "processed" / "demo" / "demo_minds14_sample_0" / "audio.wav"

    if not demo_wav_path.exists():
        print("\n1. Standardized sample audio not found. Generating via Phase 2 Preprocessor...")
        from ai_service.audio import AudioConfig, AudioPreprocessor
        from ai_service.datasets import load_minds14

        dataset = load_minds14(subset="en-US", split="train", decode_audio=False)
        sample_record = dataset[0]
        print(f"   Ground Truth Text: '{sample_record.get('transcription', '')}'")

        config = AudioConfig(output_dir="data/processed/demo")
        preprocessor = AudioPreprocessor(config)
        prep_res = preprocessor.preprocess_minds14_example(sample_record, call_id="demo_minds14_sample_0")
        print(f"   Standardized WAV: {prep_res.output_path} ({prep_res.duration_seconds:.2f}s, 16kHz mono)")
    else:
        print(f"\n1. Using existing Phase 2 standardized audio: {demo_wav_path}")

    print(f"\n2. Initializing WhisperTranscriber (model={model_size}, device={device}, compute_type={compute_type})...")
    asr_config = WhisperConfig(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        word_timestamps=True,
    )
    transcriber = WhisperTranscriber(asr_config)

    print("\n3. Executing ASR Transcription...")
    t0 = time.perf_counter()
    result = transcriber.transcribe(demo_wav_path)
    total_time = time.perf_counter() - t0

    print("\n4. Structured Transcription Result:")
    print(f"   Language:            {result.language.upper()} (p={result.language_probability:.2%})")
    print(f"   Audio Duration:      {result.audio_duration:.2f} s")
    print(f"   Processing Time:     {result.processing_time_seconds:.2f} s (Wall clock: {total_time:.2f} s)")
    print(f"   Real-Time Factor:    {result.real_time_factor:.3f}x")
    print(f"   Model Used:          {result.metadata.model_name} on {result.metadata.device} ({result.metadata.compute_type})")
    print(f"   Segment Count:       {len(result.segments)}")
    if result.warnings:
        print(f"   Warnings:            {result.warnings}")

    print("\n5. Transcript Text:")
    print(f"   \"{result.text}\"")

    print("\n6. Segments:")
    for seg in result.segments:
        conf_str = f" (avg_p={seg.avg_logprob:.2f})" if seg.avg_logprob is not None else ""
        print(f"   [{seg.start:05.2f}s -> {seg.end:05.2f}s] {seg.text}{conf_str}")
        if seg.words:
            word_str = " ".join(f"{w.word}[{w.start:.2f}-{w.end:.2f}]" for w in seg.words[:6])
            if len(seg.words) > 6:
                word_str += " ..."
            print(f"       words: {word_str}")

    print("\n" + "=" * 70)
    print("  Phase 3 Complete: Structured ASR Output Ready for Phase 4 Diarization!")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe standardized audio using faster-whisper.")
    parser.add_argument("--input", "-i", type=str, help="Path to input standardized WAV audio file")
    parser.add_argument("--output", "-o", type=str, help="Destination JSON file for structured output")
    parser.add_argument("--model", "-m", type=str, default="base", help="Whisper model size (tiny, base, small, medium, large)")
    parser.add_argument("--device", "-d", type=str, default="auto", help="Compute device (auto, cpu, cuda)")
    parser.add_argument("--compute-type", "-c", type=str, default="auto", help="Quantization / compute type (int8, float16, float32, auto)")
    parser.add_argument("--language", "-l", type=str, default="auto", help="Language code ('auto' or BCP-47 / ISO like 'en')")
    parser.add_argument("--vad", action="store_true", help="Enable VAD filtering")
    parser.add_argument("--word-timestamps", action="store_true", default=True, help="Extract word-level timestamps")
    parser.add_argument("--demo-minds14", action="store_true", help="Run demonstration on MInDS-14 sample")

    args = parser.parse_args()

    if args.demo-minds14 if hasattr(args, "demo-minds14") else args.demo_minds14:
        run_demo_minds14(
            model_size=args.model,
            device=args.device,
            compute_type=args.compute_type,
        )
        return

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input audio file does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    config = WhisperConfig(
        model_size=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        vad_filter=args.vad,
        word_timestamps=args.word_timestamps,
    )

    print(f"Loading Whisper transcriber (model={config.model_size}, device={config.device})...")
    transcriber = WhisperTranscriber(config)

    try:
        print(f"Transcribing {input_path}...")
        result = transcriber.transcribe(input_path)

        if args.output:
            out_file = Path(args.output)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"Wrote structured transcript to {out_file}")
        else:
            print("\n" + "=" * 50)
            print(f"Transcript: {result.text}")
            print(f"Language: {result.language} ({result.language_probability:.1%})")
            print(f"Duration: {result.audio_duration:.2f}s | Processing: {result.processing_time_seconds:.2f}s | RTF: {result.real_time_factor:.3f}")
            print("=" * 50)
            for seg in result.segments:
                print(f"[{seg.start:.2f}s - {seg.end:.2f}s] {seg.text}")

    except ASRError as exc:
        print(f"ASR Error: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
