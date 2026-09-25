"""
AI Call Analytics — UMAP Dimensionality Reducer.

Projects high-dimensional text embeddings into a compact manifold representation (Step 11, 12, 13)
optimized for density-based clustering with HDBSCAN.
"""

from __future__ import annotations

import logging
import numpy as np

from ai_service.clustering.config import ThemeDiscoveryConfig
from ai_service.clustering.exceptions import DimensionalityReductionError

logger = logging.getLogger("ai_call_analytics.clustering.reducer")


class UMAPReducer:
    """
    Dimensionality reduction service using UMAP.
    """

    def __init__(self, config: ThemeDiscoveryConfig | None = None) -> None:
        """Initialize the UMAP reducer with configuration."""
        self.config = config or ThemeDiscoveryConfig.from_env()

    def reduce(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Reduce high-dimensional vector embeddings to lower-dimensional space (Step 11).

        Args:
            embeddings: Float32 array of shape (N, original_dimension).

        Returns:
            Float32 array of shape (N, n_components).
        """
        n_samples, n_features = embeddings.shape
        if n_samples < 3:
            raise DimensionalityReductionError(
                f"UMAP reduction requires at least 3 samples, got {n_samples}"
            )

        # Adaptively adjust n_neighbors if dataset is smaller than configured default
        effective_neighbors = min(self.config.umap_n_neighbors, max(2, n_samples - 1))
        # Adaptively adjust n_components if dataset is smaller
        effective_components = min(self.config.umap_n_components, max(2, n_samples - 1))

        logger.info(
            "Running UMAP reduction: samples=%d, original_dim=%d -> target_dim=%d (n_neighbors=%d, metric='%s', seed=%d)",
            n_samples,
            n_features,
            effective_components,
            effective_neighbors,
            self.config.umap_metric,
            self.config.umap_random_state,
        )

        try:
            import umap

            reducer = umap.UMAP(
                n_neighbors=effective_neighbors,
                n_components=effective_components,
                min_dist=self.config.umap_min_dist,
                metric=self.config.umap_metric,
                random_state=self.config.umap_random_state,
            )
            reduced = reducer.fit_transform(embeddings)
            return np.asarray(reduced, dtype=np.float32)

        except Exception as err:
            logger.error("UMAP dimensionality reduction failed: %s", err)
            raise DimensionalityReductionError(f"UMAP reduction failed: {err}") from err
