#!/usr/bin/env python3
"""
AI Call Analytics — Audio Preprocessing CLI Tool.

Converts input call audio (or MInDS-14 sample recordings) into the standardized
target specification (16 kHz, mono, PCM_16 WAV, peak-normalized).

Usage:
    python scripts/preprocess_audio.py --input path/to/call.wav --output data/processed/call_std.wav
    python scripts/preprocess_audio.py --demo-minds14
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

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_service.audio import AudioConfig, AudioPreprocessor
from ai_service.datasets import load_minds14

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.preprocess")


def run_demo_minds14() -> None:
    """Preprocess a sample MInDS-14 dataset example to demonstrate Phase 1 -> Phase 2 integration."""
    print("=" * 60)
    print("  MInDS-14 -> Audio Preprocessing Pipeline Demo")
    print("=" * 60)

    print("\n1. Loading sample MInDS-14 record (8 kHz mono WAV)...")
    dataset = load_minds14(subset="en-US", split="train", decode_audio=False)
    sample_record = dataset[0]

    transcription = sample_record.get("transcription", "")
    intent_class = sample_record.get("intent_class", 0)
    print(f"   Utterance:    '{transcription}'")
    print(f"   Intent class: {intent_class}")

    print("\n2. Initializing AudioPreprocessor...")
    config = AudioConfig(output_dir="data/processed/demo")
    preprocessor = AudioPreprocessor(config)

    print("\n3. Processing sample through 16kHz mono PCM16 normalization pipeline...")
    start_time = time.perf_counter()
    result = preprocessor.preprocess_minds14_example(sample_record, call_id="demo_minds14_sample_0")
    elapsed = (time.perf_counter() - start_time) * 1000.0

    print("\n4. Preprocessing Result:")
    print(f"   Output Path:     {result.output_path}")
    print(f"   Format:          {result.output_format.upper()} (PCM_16)")
    print(f"   Sample Rate:     {result.sample_rate} Hz (converted from 8000 Hz)")
    print(f"   Channels:        {result.channels} (mono)")
    print(f"   Duration:        {result.duration_seconds:.2f}s")
    print(f"   File Size:       {result.file_size_bytes} bytes")
    print(f"   Status:          {result.status}")
    print(f"   Processing Time: {elapsed:.2f} ms")

    if result.quality_diagnostics:
        qd = result.quality_diagnostics
        print("\n5. Audio Quality Telemetry:")
        print(f"   Peak Level:      {qd.peak_dbfs} dBFS")
        print(f"   RMS Power:       {qd.rms_dbfs} dBFS")
        print(f"   Silence Ratio:   {qd.silence_percentage}%")
        print(f"   Clipping Ratio:  {qd.clipping_percentage}%")
        if qd.warnings:
            print(f"   Warnings:        {qd.warnings}")

    print("\n" + "=" * 60)
    print("  Demo Complete: Standardized audio ready for Whisper ASR!")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Standardize call audio to 16kHz mono PCM16 WAV.")
    parser.add_argument("--input", "-i", type=str, help="Path to input audio file")
    parser.add_argument("--output", "-o", type=str, help="Destination path for standardized WAV")
    parser.add_argument("--call-id", type=str, help="Call identifier for directory routing")
    parser.add_argument("--demo-minds14", action="store_true", help="Run demonstration using MInDS-14 dataset")

    args = parser.parse_args()

    if args.demo_minds14:
        run_demo_minds14()
        return

    if not args.input:
        parser.print_help()
        sys.exit(1)

    preprocessor = AudioPreprocessor()
    result = preprocessor.preprocess(args.input, output_path=args.output, call_id=args.call_id)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
