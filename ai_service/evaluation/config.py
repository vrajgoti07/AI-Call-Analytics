"""
AI Call Analytics — Evaluation Configuration.

Centralizes configuration parameters, dataset splits, sample limits,
and output directory paths for Phase 9 model and pipeline validation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvaluationConfig:
    """
    Configuration parameters for AI system evaluation.
    """

    dataset_name: str = "PolyAI/minds14"
    subset: str = "en-US"
    split: str = field(default_factory=lambda: os.getenv("EVAL_SPLIT", "test"))
    max_samples: int | None = field(
        default_factory=lambda: int(os.getenv("EVAL_MAX_SAMPLES"))
        if os.getenv("EVAL_MAX_SAMPLES")
        else None
    )
    batch_size: int = field(default_factory=lambda: int(os.getenv("EVAL_BATCH_SIZE", "16")))
    output_dir: Path = field(
        default_factory=lambda: Path(os.getenv("EVAL_OUTPUT_DIR", "reports/evaluation"))
    )
    random_seed: int = field(default_factory=lambda: int(os.getenv("EVAL_RANDOM_SEED", "42")))

    # Specific components to evaluate
    components: list[str] = field(
        default_factory=lambda: [
            "dataset",
            "asr",
            "diarization",
            "sentiment",
            "intent",
            "ner",
            "embeddings",
            "themes",
            "escalation",
            "system",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration parameters."""
        return {
            "dataset_name": self.dataset_name,
            "subset": self.subset,
            "split": self.split,
            "max_samples": self.max_samples,
            "batch_size": self.batch_size,
            "output_dir": str(self.output_dir),
            "random_seed": self.random_seed,
            "components": list(self.components),
        }
