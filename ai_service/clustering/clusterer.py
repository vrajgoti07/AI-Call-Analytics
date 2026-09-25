"""
AI Call Analytics — HDBSCAN Density Clusterer.

Executes density-based hierarchical clustering on reduced embedding spaces (Step 14, 15),
isolates noise points (-1), and evaluates cluster validation metrics.
"""

from __future__ import annotations

import logging
import numpy as np
from sklearn.metrics import silhouette_score

from ai_service.clustering.config import ThemeDiscoveryConfig
from ai_service.clustering.exceptions import ClusteringExecutionError

logger = logging.getLogger("ai_call_analytics.clustering.clusterer")


class HDBSCANClusterer:
    """
    Density-based clustering using HDBSCAN.
    """

    def __init__(self, config: ThemeDiscoveryConfig | None = None) -> None:
        """Initialize the HDBSCAN clusterer."""
        self.config = config or ThemeDiscoveryConfig.from_env()

    def cluster(
        self,
        reduced_embeddings: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float | None]:
        """
        Execute HDBSCAN density clustering on reduced vectors.

        Args:
            reduced_embeddings: Float32 array of shape (N, n_components).

        Returns:
            Tuple of:
            - labels: Cluster IDs (with -1 indicating noise)
            - probabilities: Cluster membership confidence in [0.0, 1.0]
            - outlier_scores: Outlier likelihood in [0.0, 1.0]
            - silhouette: Non-noise silhouette score (or None if unavailable)
        """
        n_samples = len(reduced_embeddings)
        effective_min_cluster_size = min(
            self.config.hdbscan_min_cluster_size,
            max(2, n_samples // 3),
        )
        effective_min_samples = (
            self.config.hdbscan_min_samples
            if self.config.hdbscan_min_samples is not None
            else effective_min_cluster_size
        )

        logger.info(
            "Running HDBSCAN clustering: samples=%d, min_cluster_size=%d, min_samples=%d, metric='%s'",
            n_samples,
            effective_min_cluster_size,
            effective_min_samples,
            self.config.hdbscan_metric,
        )

        try:
            from sklearn.cluster import HDBSCAN

            clusterer = HDBSCAN(
                min_cluster_size=effective_min_cluster_size,
                min_samples=effective_min_samples,
                metric=self.config.hdbscan_metric,
                cluster_selection_method=self.config.hdbscan_cluster_selection_method,
            )
            labels = clusterer.fit_predict(reduced_embeddings)
            probabilities = getattr(clusterer, "probabilities_", np.ones(n_samples, dtype=np.float32))

            # Outlier scores (GLOSH or 1.0 - probabilities)
            if hasattr(clusterer, "outlier_scores_") and clusterer.outlier_scores_ is not None:
                outlier_scores = clusterer.outlier_scores_
            else:
                outlier_scores = 1.0 - probabilities

            # Calculate silhouette score strictly on non-noise points (Step 29)
            non_noise_mask = labels != -1
            unique_clusters = set(labels[non_noise_mask])
            silhouette: float | None = None

            if len(unique_clusters) >= 2 and np.sum(non_noise_mask) > len(unique_clusters):
                try:
                    silhouette = float(
                        silhouette_score(
                            reduced_embeddings[non_noise_mask],
                            labels[non_noise_mask],
                            metric=self.config.hdbscan_metric,
                        )
                    )
                except Exception as s_err:
                    logger.debug("Silhouette computation skipped: %s", s_err)
                    silhouette = None

            n_noise = int(np.sum(labels == -1))
            n_clusters = len(unique_clusters)
            logger.info(
                "HDBSCAN completed: %d clusters discovered, %d noise points (%.1f%%)",
                n_clusters,
                n_noise,
                (n_noise / n_samples) * 100.0 if n_samples > 0 else 0.0,
            )

            return labels, probabilities, outlier_scores, silhouette

        except Exception as err:
            logger.error("HDBSCAN clustering execution failed: %s", err)
            raise ClusteringExecutionError(f"HDBSCAN clustering failed: {err}") from err
