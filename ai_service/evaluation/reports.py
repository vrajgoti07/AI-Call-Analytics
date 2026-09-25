"""
AI Call Analytics — Evaluation Reporting & Serialization.

Formats, serializes, and exports multi-component validation results into
standardized JSON data contracts, Markdown summaries, and console audit displays.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ComponentEvaluationResult:
    """
    Standardized validation telemetry for an individual AI component.
    """

    component: str  # e.g., 'asr', 'intent', 'diarization'
    evaluation_type: str  # 'quantitative', 'qualitative', 'structural', 'ground_truth_unavailable'
    status: str  # 'PASSED', 'WARNING', 'FAILED', 'GROUND_TRUTH_UNAVAILABLE'
    metrics: dict[str, Any] = field(default_factory=dict)
    sample_count: int = 0
    dataset_name: str = "PolyAI/minds14"
    model_name: str = "unknown"
    model_version: str = "1.0.0"
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "component": self.component,
            "evaluation_type": self.evaluation_type,
            "status": self.status,
            "metrics": self.metrics,
            "sample_count": self.sample_count,
            "dataset_name": self.dataset_name,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass
class SystemEvaluationReport:
    """
    Comprehensive system-wide evaluation audit across all 8 pipeline phases.
    """

    evaluation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    git_commit: str | None = None
    components: dict[str, ComponentEvaluationResult] = field(default_factory=dict)
    latency_breakdown_seconds: dict[str, float] = field(default_factory=dict)
    total_pipeline_latency_seconds: float = 0.0

    def add_result(self, result: ComponentEvaluationResult) -> None:
        """Register a component evaluation result."""
        self.components[result.component] = result

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete system evaluation report to JSON-compatible dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "latency_breakdown_seconds": self.latency_breakdown_seconds,
            "total_pipeline_latency_seconds": round(self.total_pipeline_latency_seconds, 4),
        }

    def save_json(self, filepath: str | Path) -> None:
        """Save structured JSON results."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("Saved evaluation JSON report to %s", path)

    def save_markdown(self, filepath: str | Path) -> None:
        """Generate human-readable Markdown evaluation report."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# AI Call Analysis — System Evaluation Report",
            "",
            f"**Evaluation ID:** `{self.evaluation_id}`  ",
            f"**Execution Timestamp:** `{self.timestamp}`  ",
            f"**Git Commit:** `{self.git_commit or 'N/A'}`  ",
            "",
            "## 1. Quality Matrix Summary",
            "",
            "| Component | Evaluation Type | Status | Key Metric | Metric Value | Samples |",
            "|:---|:---:|:---:|:---|:---:|:---:|",
        ]

        for name, comp in self.components.items():
            key_metric_name = "N/A"
            key_metric_val = "N/A"
            if comp.metrics:
                # Pick the most prominent metric for the table
                for candidate in ["wer", "macro_f1", "accuracy", "recall@5", "silhouette_score", "f1"]:
                    if candidate in comp.metrics and comp.metrics[candidate] is not None:
                        key_metric_name = candidate.upper()
                        key_metric_val = str(comp.metrics[candidate])
                        break
                if key_metric_name == "N/A" and comp.metrics:
                    first_k = next(iter(comp.metrics))
                    key_metric_name = first_k.upper()
                    key_metric_val = str(comp.metrics[first_k])

            lines.append(
                f"| **{name.upper()}** | {comp.evaluation_type} | `{comp.status}` | {key_metric_name} | {key_metric_val} | {comp.sample_count} |"
            )

        lines.extend([
            "",
            "## 2. Detailed Component Analyses",
            "",
        ])

        for name, comp in self.components.items():
            lines.extend([
                f"### {name.upper()}",
                f"- **Model:** `{comp.model_name}` (v{comp.model_version})",
                f"- **Evaluation Type:** `{comp.evaluation_type}`",
                f"- **Status:** `{comp.status}`",
                f"- **Summary:** {comp.summary}",
            ])
            if comp.metrics:
                lines.append("- **Metrics:**")
                for k, v in comp.metrics.items():
                    if isinstance(v, (int, float, str)):
                        lines.append(f"  - `{k}`: {v}")
            lines.append("")

        if self.latency_breakdown_seconds:
            lines.extend([
                "## 3. End-to-End Latency Breakdown",
                "",
                "| Stage | Latency (seconds) |",
                "|:---|:---:|",
            ])
            for stage, lat in self.latency_breakdown_seconds.items():
                lines.append(f"| {stage} | {lat:.4f}s |")
            lines.extend([
                f"| **TOTAL PIPELINE** | **{self.total_pipeline_latency_seconds:.4f}s** |",
                "",
            ])

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Saved evaluation Markdown report to %s", path)

    def print_summary(self) -> None:
        """Print clean ASCII summary to console."""
        print("\n" + "=" * 90)
        print("                 AI CALL ANALYSIS — COMPONENT QUALITY AUDIT")
        print("=" * 90)
        print(f"Evaluation ID:  {self.evaluation_id}")
        print(f"Timestamp:      {self.timestamp}")
        print("-" * 90)
        print(f"{'Component':<18} | {'Type':<16} | {'Status':<24} | {'Metric':<14} | {'Value':<10}")
        print("-" * 90)

        for name, comp in self.components.items():
            key_m = "N/A"
            val_m = "N/A"
            if comp.metrics:
                for candidate in ["wer", "macro_f1", "accuracy", "recall@5", "silhouette_score", "f1"]:
                    if candidate in comp.metrics and comp.metrics[candidate] is not None:
                        key_m = candidate.upper()
                        val_m = str(comp.metrics[candidate])
                        break
            print(f"{name.upper():<18} | {comp.evaluation_type:<16} | {comp.status:<24} | {key_m:<14} | {val_m:<10}")

        print("=" * 90)
        if self.total_pipeline_latency_seconds > 0:
            print(f"Total Pipeline Latency: {self.total_pipeline_latency_seconds:.3f}s")
            print("=" * 90)
