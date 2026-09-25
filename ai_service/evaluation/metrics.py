"""
AI Call Analytics — Evaluation Metrics.

Provides mathematically verified implementations for ASR error rates (WER, CER),
classification metrics (Accuracy, Macro-F1, Weighted-F1, Confusion Matrix),
information retrieval quality (Recall@K, MRR), and clustering validation (Silhouette, Noise Ratio).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    silhouette_score,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 1. ASR Metrics: Word Error Rate (WER) & Character Error Rate (CER)
# ============================================================================
def calculate_wer(
    reference: str,
    hypothesis: str,
) -> tuple[float, int, int, int, int]:
    """
    Compute Word Error Rate (WER) using dynamic programming Levenshtein distance.

    Formula:
        WER = (S + D + I) / N
    Where:
        S = Number of word substitutions
        D = Number of word deletions
        I = Number of word insertions
        N = Number of words in reference text

    Returns:
        (wer, substitutions, deletions, insertions, reference_word_count)
    """
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()

    n = len(ref_words)
    m = len(hyp_words)

    if n == 0:
        if m == 0:
            return 0.0, 0, 0, 0, 0
        return 1.0, 0, 0, m, 0

    # DP Matrix: (n + 1) x (m + 1)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    ops = [[""] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
        ops[i][0] = "D"
    for j in range(m + 1):
        dp[0][j] = j
        ops[0][j] = "I"
    ops[0][0] = " "

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                ops[i][j] = "M"  # Match
            else:
                sub = dp[i - 1][j - 1] + 1
                ins = dp[i][j - 1] + 1
                dele = dp[i - 1][j] + 1

                min_val = min(sub, ins, dele)
                dp[i][j] = min_val
                if min_val == sub:
                    ops[i][j] = "S"
                elif min_val == ins:
                    ops[i][j] = "I"
                else:
                    ops[i][j] = "D"

    # Backtrace to count exact S, D, I operations
    i, j = n, m
    subs, dels, inss = 0, 0, 0
    while i > 0 or j > 0:
        op = ops[i][j]
        if op == "M":
            i -= 1
            j -= 1
        elif op == "S":
            subs += 1
            i -= 1
            j -= 1
        elif op == "I":
            inss += 1
            j -= 1
        elif op == "D":
            dels += 1
            i -= 1
        else:
            break

    wer = float((subs + dels + inss) / n)
    return wer, subs, dels, inss, n


def calculate_cer(reference: str, hypothesis: str) -> float:
    """
    Compute Character Error Rate (CER) using character-level Levenshtein distance.
    """
    ref_chars = list(reference.strip())
    hyp_chars = list(hypothesis.strip())

    n = len(ref_chars)
    m = len(hyp_chars)

    if n == 0:
        return 0.0 if m == 0 else 1.0

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j - 1], dp[i][j - 1], dp[i - 1][j])

    return float(dp[n][m] / n)


# ============================================================================
# 2. Classification Metrics (Intent, Sentiment, Supervised Escalation)
# ============================================================================
def calculate_classification_metrics(
    y_true: list[Any] | np.ndarray,
    y_pred: list[Any] | np.ndarray,
    labels: list[Any] | None = None,
) -> dict[str, Any]:
    """
    Calculate comprehensive multiclass/binary classification metrics.
    """
    if len(y_true) == 0 or len(y_pred) == 0:
        return {
            "sample_count": 0,
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "weighted_f1": 0.0,
            "confusion_matrix": [],
            "per_class": {},
        }

    acc = float(accuracy_score(y_true, y_pred))
    macro_prec = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    macro_rec = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    all_labels = labels if labels is not None else sorted(list(set(y_true) | set(y_pred)))
    cm = confusion_matrix(y_true, y_pred, labels=all_labels).tolist()

    # Per-class metrics
    per_class: dict[str, dict[str, float]] = {}
    for label in all_labels:
        # Binary mask for current class
        y_t_bin = [1 if y == label else 0 for y in y_true]
        y_p_bin = [1 if y == label else 0 for y in y_pred]
        p = float(precision_score(y_t_bin, y_p_bin, zero_division=0))
        r = float(recall_score(y_t_bin, y_p_bin, zero_division=0))
        f = float(f1_score(y_t_bin, y_p_bin, zero_division=0))
        support = int(sum(y_t_bin))
        per_class[str(label)] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f, 4),
            "support": support,
        }

    return {
        "sample_count": len(y_true),
        "accuracy": round(acc, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "labels": [str(l) for l in all_labels],
        "confusion_matrix": cm,
        "per_class": per_class,
    }


# ============================================================================
# 3. Information Retrieval Metrics (Semantic Search)
# ============================================================================
def calculate_retrieval_metrics(
    relevant_ids_per_query: list[set[str]],
    retrieved_ids_per_query: list[list[str]],
    k_values: tuple[int, ...] = (1, 5, 10),
) -> dict[str, Any]:
    """
    Calculate Recall@K, Precision@K, and Mean Reciprocal Rank (MRR).

    Args:
        relevant_ids_per_query: Ground truth sets of relevant chunk IDs.
        retrieved_ids_per_query: Ranked lists of retrieved chunk IDs.
        k_values: Cutoff thresholds (e.g. 1, 5, 10).
    """
    n_queries = len(relevant_ids_per_query)
    if n_queries == 0:
        return {"query_count": 0, "mrr": 0.0, **{f"recall@{k}": 0.0 for k in k_values}}

    recall_at_k: dict[int, list[float]] = {k: [] for k in k_values}
    precision_at_k: dict[int, list[float]] = {k: [] for k in k_values}
    reciprocal_ranks: list[float] = []

    for rel_set, ret_list in zip(relevant_ids_per_query, retrieved_ids_per_query):
        if not rel_set:
            continue

        # Reciprocal Rank (MRR)
        rr = 0.0
        for rank, item_id in enumerate(ret_list, start=1):
            if item_id in rel_set:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        # Recall@K and Precision@K
        for k in k_values:
            top_k = ret_list[:k]
            hits = sum(1 for item_id in top_k if item_id in rel_set)
            rec = hits / len(rel_set)
            prec = hits / k if k > 0 else 0.0
            recall_at_k[k].append(rec)
            precision_at_k[k].append(prec)

    results: dict[str, Any] = {
        "query_count": n_queries,
        "mrr": round(float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0, 4),
    }
    for k in k_values:
        results[f"recall@{k}"] = round(
            float(np.mean(recall_at_k[k])) if recall_at_k[k] else 0.0, 4
        )
        results[f"precision@{k}"] = round(
            float(np.mean(precision_at_k[k])) if precision_at_k[k] else 0.0, 4
        )

    return results


# ============================================================================
# 4. Clustering & Theme Metrics
# ============================================================================
def calculate_clustering_metrics(
    embeddings: np.ndarray,
    labels: np.ndarray,
) -> dict[str, Any]:
    """
    Calculate unsupervised clustering validation metrics.
    Computes silhouette score strictly on non-noise points.
    """
    n_samples = len(labels)
    if n_samples == 0:
        return {"n_samples": 0, "n_clusters": 0, "noise_percentage": 0.0, "silhouette_score": None}

    unique_labels = set(labels)
    non_noise_mask = labels != -1
    n_noise = int(np.sum(~non_noise_mask))
    noise_pct = round(float(n_noise / n_samples) * 100.0, 2)

    valid_clusters = [l for l in unique_labels if l != -1]
    n_clusters = len(valid_clusters)

    sil_score: float | None = None
    if n_clusters >= 2 and np.sum(non_noise_mask) > n_clusters:
        try:
            sil_score = round(
                float(silhouette_score(embeddings[non_noise_mask], labels[non_noise_mask], metric="cosine")),
                4,
            )
        except Exception as exc:
            logger.debug("Silhouette computation skipped: %s", exc)

    return {
        "n_samples": n_samples,
        "n_clusters": n_clusters,
        "noise_count": n_noise,
        "noise_percentage": noise_pct,
        "silhouette_score": sil_score,
    }
