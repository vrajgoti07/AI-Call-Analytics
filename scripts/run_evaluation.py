#!/usr/bin/env python3
"""
AI Call Analytics — System Evaluation CLI Tool (Phase 9).

Executes quantitative, retrieval, and structural evaluations across all 8 pipeline phases,
prints a quality audit matrix, and exports results to JSON and Markdown.

Usage:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --component intent
    python scripts/run_evaluation.py --output-dir reports/evaluation
"""

from __future__ import annotations

import argparse
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

from ai_service.evaluation import EvaluationConfig, EvaluationRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Call Analytics Evaluation Suite")
    parser.add_argument(
        "--component",
        type=str,
        default="all",
        choices=["all", "dataset", "asr", "diarization", "sentiment", "intent", "ner", "embeddings", "themes", "escalation"],
        help="Target AI component to evaluate or 'all'",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/evaluation",
        help="Directory to save JSON and Markdown reports",
    )
    args = parser.parse_args()

    cfg = EvaluationConfig(output_dir=Path(args.output_dir))
    if args.component != "all":
        cfg.components = [args.component]

    runner = EvaluationRunner(cfg)
    report = runner.run_all()
    report.print_summary()


if __name__ == "__main__":
    main()
