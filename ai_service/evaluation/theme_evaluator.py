"""
AI Call Analytics — Theme Discovery Evaluator.

Evaluates unsupervised topic discovery using density metrics, noise proportions,
silhouette validation, and topic coherence.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ai_service.clustering import ThemeDiscoveryConfig, ThemeDiscoveryService
from ai_service.embeddings.manager import EmbeddingModelManager
from ai_service.evaluation.config import EvaluationConfig
from ai_service.evaluation.reports import ComponentEvaluationResult

logger = logging.getLogger(__name__)


class ThemeEvaluator:
    """
    Evaluates unsupervised clustering stability, silhouette score, and noise levels.
    """

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def evaluate(self) -> ComponentEvaluationResult:
        """
        Execute theme clustering validation on realistic domain chunks.
        """
        logger.info("Executing Theme Discovery evaluation...")
        try:
            texts = [
                "My debit card was blocked at an ATM machine and my account is frozen.",
                "Can you unblock my debit card after the freeze yesterday?",
                "Online banking says my debit card has been frozen due to fraud suspicion.",
                "What is the interest rate for a small business commercial loan?",
                "I want to apply for a business mortgage loan for commercial property.",
                "How much collateral is required for a commercial business loan?",
                "How do I send an international wire transfer to another bank?",
                "The international wire transfer failed to send abroad to Europe.",
                "Can you check the status of my outgoing international wire transfer?",
                "What is my current available balance in my checking account?",
                "Can you check my checking account balance online?",
                "I need to know my available funds and checking balance.",
                "Can I withdraw five hundred dollars from the ATM cash machine?",
                "What is the daily cash limit on ATM withdrawals?",
                "The cash machine did not dispense my money.",
            ]

            manager = EmbeddingModelManager()
            embeddings = np.array(manager.embed_batch(texts), dtype=np.float32)

            cluster_config = ThemeDiscoveryConfig(
                min_embeddings=12,
                umap_n_neighbors=5,
                umap_n_components=3,
                hdbscan_min_cluster_size=3,
                hdbscan_min_samples=2,
                umap_random_state=42,
            )
            service = ThemeDiscoveryService(cluster_config)

            # Ingest and run
            metadata = [
                {
                    "embedding_id": f"emb_{i}",
                    "chunk_id": i,
                    "call_id": f"call_{i // 3}",
                    "text": t,
                }
                for i, t in enumerate(texts)
            ]

            result = service.discover_themes(embeddings=embeddings, metadata=metadata, run_name="theme_eval_run")

            metrics = {
                "dataset_size": result.embedding_count,
                "cluster_count": result.cluster_count,
                "noise_count": result.noise_count,
                "noise_percentage": result.noise_percentage,
                "silhouette_score": result.silhouette_score,
                "themes": [
                    {
                        "cluster_id": th.cluster_id,
                        "label": th.label,
                        "size": th.size,
                        "percentage": th.percentage,
                        "top_keywords": th.keywords[:3],
                    }
                    for th in result.themes
                ],
            }

            status = "PASSED" if result.cluster_count >= 2 and result.noise_percentage < 40.0 else "WARNING"
            summary = (
                f"Clustered {result.embedding_count} items into {result.cluster_count} themes. "
                f"Noise={result.noise_count} ({result.noise_percentage:.1f}%), "
                f"Silhouette Score={result.silhouette_score if result.silhouette_score is not None else 'N/A'}."
            )

            return ComponentEvaluationResult(
                component="themes",
                evaluation_type="cluster_based",
                status=status,
                metrics=metrics,
                sample_count=result.embedding_count,
                model_name="UMAP+HDBSCAN+c-TF-IDF",
                model_version="1.0.0",
                summary=summary,
                details={"clusters": metrics["themes"]},
            )


        except Exception as exc:
            logger.error("Theme evaluation failed: %s", exc)
            return ComponentEvaluationResult(
                component="themes",
                evaluation_type="cluster_based",
                status="FAILED",
                metrics={},
                sample_count=0,
                model_name="UMAP+HDBSCAN",
                summary=f"Evaluation failed: {exc}",
                details={"error": str(exc)},
            )
