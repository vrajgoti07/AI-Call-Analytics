"""
AI Call Analytics — Theme Discovery Configuration.

Defines parameterized settings for UMAP dimensionality reduction, HDBSCAN clustering,
cluster statistics, and keyword extraction with environment variable overrides and
deterministic configuration hashing.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ThemeDiscoveryConfig:
    """Configurable hyperparameters for Phase 7 theme discovery."""

    # Dataset threshold (Step 8)
    min_embeddings: int = 15  # Minimum required chunks to form clusters

    # UMAP Dimensionality Reduction (Step 5, 11, 12)
    umap_n_neighbors: int = 15
    umap_n_components: int = 5  # Reduced dimensions for density clustering
    umap_min_dist: float = 0.0
    umap_metric: str = "cosine"
    umap_random_state: int = 42

    # HDBSCAN Density Clustering (Step 5, 14)
    hdbscan_min_cluster_size: int = 4
    hdbscan_min_samples: int | None = None  # Defaults to min_cluster_size if None
    hdbscan_metric: str = "euclidean"
    hdbscan_cluster_selection_method: str = "eom"  # 'eom' (Excess of Mass) or 'leaf'

    # Keyword extraction & labeling (Step 18, 20)
    top_keywords: int = 5
    representative_chunks: int = 3
    min_cluster_percentage: float = 1.0

    # Expected embedding specification (Step 10, 38)
    expected_model_name: str = "all-MiniLM-L6-v2"
    expected_dimension: int = 384

    @classmethod
    def from_env(cls) -> ThemeDiscoveryConfig:
        """Construct ThemeDiscoveryConfig from environment variables with sensible defaults."""
        return cls(
            min_embeddings=int(os.getenv("THEME_MIN_EMBEDDINGS", "15")),
            umap_n_neighbors=int(os.getenv("THEME_UMAP_N_NEIGHBORS", "15")),
            umap_n_components=int(os.getenv("THEME_UMAP_N_COMPONENTS", "5")),
            umap_min_dist=float(os.getenv("THEME_UMAP_MIN_DIST", "0.0")),
            umap_metric=os.getenv("THEME_UMAP_METRIC", "cosine").strip().lower(),
            umap_random_state=int(os.getenv("THEME_UMAP_RANDOM_STATE", "42")),
            hdbscan_min_cluster_size=int(os.getenv("THEME_HDBSCAN_MIN_CLUSTER_SIZE", "4")),
            hdbscan_min_samples=(
                int(os.getenv("THEME_HDBSCAN_MIN_SAMPLES"))
                if os.getenv("THEME_HDBSCAN_MIN_SAMPLES")
                else None
            ),
            hdbscan_metric=os.getenv("THEME_HDBSCAN_METRIC", "euclidean").strip().lower(),
            hdbscan_cluster_selection_method=os.getenv(
                "THEME_HDBSCAN_CLUSTER_SELECTION_METHOD", "eom"
            ).strip().lower(),
            top_keywords=int(os.getenv("THEME_TOP_KEYWORDS", "5")),
            representative_chunks=int(os.getenv("THEME_REPRESENTATIVE_CHUNKS", "3")),
            expected_model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip(),
            expected_dimension=int(os.getenv("EMBEDDING_DIMENSION", "384")),
        )

    def config_hash(self) -> str:
        """Compute deterministic SHA-256 hash of configuration parameters for run versioning (Step 27)."""
        d = asdict(self)
        canonical = json.dumps(d, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
