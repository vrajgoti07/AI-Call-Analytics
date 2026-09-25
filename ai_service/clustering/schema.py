"""
AI Call Analytics — Theme Discovery Schemas.

Defines strongly typed dataclasses representing representative dialogue chunks,
extracted themes, point memberships, and the overall discovery run result.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RepresentativeChunk:
    """A highly representative transcript chunk characterizing a theme (Step 17)."""

    chunk_id: int
    call_id: str
    speaker: str
    start: float
    end: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize representative chunk to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "call_id": self.call_id,
            "speaker": self.speaker,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
        }


@dataclass
class ThemeRecord:
    """
    Complete structured representation of a discovered conversational theme (Step 3, 45).
    """

    theme_id: str
    cluster_id: int
    label: str
    keywords: list[str]
    size: int
    percentage: float
    call_count: int
    speaker_count: int
    representative_chunks: list[RepresentativeChunk] = field(default_factory=list)
    intent_distribution: dict[str, float] = field(default_factory=dict)
    sentiment_distribution: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize theme record to JSON-compatible dictionary."""
        return {
            "theme_id": self.theme_id,
            "cluster_id": self.cluster_id,
            "label": self.label,
            "keywords": list(self.keywords),
            "size": self.size,
            "percentage": round(self.percentage, 2),
            "call_count": self.call_count,
            "speaker_count": self.speaker_count,
            "representative_chunks": [c.to_dict() for c in self.representative_chunks],
            "intent_distribution": {k: round(v, 3) for k, v in self.intent_distribution.items()},
            "sentiment_distribution": {k: round(v, 3) for k, v in self.sentiment_distribution.items()},
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ThemeMembershipRecord:
    """Cluster membership assignment for an individual chunk vector (Step 14, 15)."""

    chunk_id: int
    call_id: str
    cluster_id: int  # -1 represents HDBSCAN noise
    theme_id: str | None  # None for noise
    membership_probability: float
    outlier_score: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize membership record to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "call_id": self.call_id,
            "cluster_id": self.cluster_id,
            "theme_id": self.theme_id,
            "membership_probability": round(self.membership_probability, 4),
            "outlier_score": round(self.outlier_score, 4),
        }


@dataclass
class ThemeDiscoveryResult:
    """
    Standardized Phase 7 Output Contract (Step 3, 44).
    Encompasses the entire run execution, discovered themes, noise points, and metrics.
    """

    run_id: str
    config_hash: str
    embedding_count: int
    cluster_count: int
    noise_count: int
    noise_percentage: float
    silhouette_score: float | None
    themes: list[ThemeRecord] = field(default_factory=list)
    memberships: list[ThemeMembershipRecord] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    status: str = "SUCCESS"

    def to_dict(self) -> dict[str, Any]:
        """Serialize discovery result to dictionary."""
        return {
            "run_id": self.run_id,
            "config_hash": self.config_hash,
            "embedding_count": self.embedding_count,
            "cluster_count": self.cluster_count,
            "noise_count": self.noise_count,
            "noise_percentage": round(self.noise_percentage, 2),
            "silhouette_score": round(self.silhouette_score, 4) if self.silhouette_score is not None else None,
            "themes": [t.to_dict() for t in self.themes],
            "processing_time_seconds": round(self.processing_time_seconds, 4),
            "status": self.status,
        }
