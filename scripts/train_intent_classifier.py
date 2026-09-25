#!/usr/bin/env python3
"""
AI Call Analytics — MInDS-14 Intent Model Training CLI.

Trains and evaluates the 14-class e-banking intent classifier on the MInDS-14
dataset with stratified sampling and outputs the performance metrics.

Usage:
    python scripts/train_intent_classifier.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_service.intent.trainer import train_minds14_intent_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.train_intent")


def main() -> None:
    print("=" * 65)
    print("  Training MInDS-14 Intent Classifier (14 Classes)")
    print("=" * 65)

    metrics = train_minds14_intent_model(output_dir="models/intent")

    print("\nTraining & Evaluation Complete!")
    print(f"Artifact Path:  {metrics['artifact_path']}")
    print(f"Metadata Path:  {metrics['metadata_path']}")
    print("\nHeld-Out Test Split Metrics:")
    for k, v in metrics["test_metrics"].items():
        print(f"   {k:18s}: {v}")
    print("=" * 65)


if __name__ == "__main__":
    main()
