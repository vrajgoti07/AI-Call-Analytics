"""
AI Call Analytics — Embedding & Retrieval Evaluator.

Evaluates Sentence Transformer dense embeddings and semantic retrieval
across diverse e-banking queries, measuring Recall@1, Recall@5, Recall@10, and MRR.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ai_service.embeddings.manager import EmbeddingModelManager
from ai_service.evaluation.config import EvaluationConfig
from ai_service.evaluation.metrics import calculate_retrieval_metrics
from ai_service.evaluation.reports import ComponentEvaluationResult

logger = logging.getLogger(__name__)


def create_retrieval_benchmark() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Construct a verified e-banking domain retrieval benchmark set.
    Returns:
        (queries, corpus_chunks)
    """
    corpus = [
        {"id": "c1", "text": "My debit card was blocked at an ATM and online access is frozen."},
        {"id": "c2", "text": "Can you unblock my card after it was frozen yesterday?"},
        {"id": "c3", "text": "What is the interest rate for a small business commercial loan?"},
        {"id": "c4", "text": "I want to apply for a business mortgage loan for commercial property."},
        {"id": "c5", "text": "How do I send an international wire transfer to another bank?"},
        {"id": "c6", "text": "The international wire transfer failed to send abroad."},
        {"id": "c7", "text": "What is my current available balance in my checking account?"},
        {"id": "c8", "text": "Can you check my checking account balance online?"},
        {"id": "c9", "text": "What is the daily cash withdrawal limit at the ATM machine?"},
        {"id": "c10", "text": "Can I increase my daily ATM withdrawal limit for today?"},
    ]

    queries = [
        {"query": "unfreeze my debit card", "relevant_ids": {"c1", "c2"}},
        {"query": "commercial business loan application", "relevant_ids": {"c3", "c4"}},
        {"query": "send money via international wire", "relevant_ids": {"c5", "c6"}},
        {"query": "view available checking balance", "relevant_ids": {"c7", "c8"}},
        {"query": "raise ATM daily cash limit", "relevant_ids": {"c9", "c10"}},
    ]

    return queries, corpus


class RetrievalEvaluator:
    """
    Evaluates semantic vector retrieval using cosine similarity over normalized embeddings.
    """

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def evaluate(self) -> ComponentEvaluationResult:
        """
        Execute information retrieval evaluation on benchmark queries and chunks.
        """
        logger.info("Executing Semantic Retrieval evaluation...")
        try:
            manager = EmbeddingModelManager()
            queries, corpus = create_retrieval_benchmark()

            # Encode corpus and queries
            corpus_texts = [item["text"] for item in corpus]
            corpus_ids = [item["id"] for item in corpus]

            corpus_embeddings = np.array(manager.embed_batch(corpus_texts), dtype=np.float32)
            query_texts = [q["query"] for q in queries]
            query_embeddings = np.array(manager.embed_batch(query_texts), dtype=np.float32)

            relevant_sets = [q["relevant_ids"] for q in queries]
            retrieved_lists: list[list[str]] = []

            # Cosine similarity matrix: Q x C
            sim_matrix = np.dot(query_embeddings, corpus_embeddings.T)

            for q_idx in range(len(queries)):
                scores = sim_matrix[q_idx]
                ranked_indices = np.argsort(scores)[::-1]
                ranked_ids = [corpus_ids[i] for i in ranked_indices]
                retrieved_lists.append(ranked_ids)

            metrics = calculate_retrieval_metrics(
                relevant_ids_per_query=relevant_sets,
                retrieved_ids_per_query=retrieved_lists,
                k_values=(1, 3, 5),
            )

            metrics.update({
                "embedding_model": manager.config.model_name,
                "embedding_dimension": manager.config.dimension,
                "distance_metric": "cosine",
                "normalization": "L2",
                "corpus_size": len(corpus),
            })

            status = "PASSED" if metrics.get("recall@5", 0.0) >= 0.80 else "WARNING"
            summary = (
                f"Evaluated {len(queries)} queries against {len(corpus)} domain chunks. "
                f"MRR={metrics['mrr']:.4f}, Recall@1={metrics['recall@1']:.2%}, "
                f"Recall@3={metrics['recall@3']:.2%}, Recall@5={metrics['recall@5']:.2%}."
            )

            return ComponentEvaluationResult(
                component="embeddings",
                evaluation_type="retrieval",
                status=status,
                metrics=metrics,
                sample_count=len(queries),
                model_name=manager.config.model_name,
                model_version="1.0.0",
                summary=summary,
                details={"queries_evaluated": [q["query"] for q in queries]},
            )

        except Exception as exc:
            logger.error("Retrieval evaluation failed: %s", exc)
            return ComponentEvaluationResult(
                component="embeddings",
                evaluation_type="retrieval",
                status="FAILED",
                metrics={},
                sample_count=0,
                model_name="all-MiniLM-L6-v2",
                summary=f"Evaluation failed: {exc}",
                details={"error": str(exc)},
            )
