"""
AI Call Analytics — Cluster Statistics & Representative Chunk Calculator.

Calculates cluster size, percentage of total call corpus, distinct call and speaker distributions (Step 16, 23, 24),
identifies representative dialogue chunks via centroid proximity in embedding space (Step 17),
and aggregates Phase 5 intent and sentiment telemetry (Step 22).
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import numpy as np

from ai_service.clustering.schema import RepresentativeChunk

logger = logging.getLogger("ai_call_analytics.clustering.statistics")


def _find_representative_chunks(
    cluster_embeddings: np.ndarray,
    cluster_metadata: list[dict[str, Any]],
    top_n: int = 3,
) -> list[RepresentativeChunk]:
    """
    Select transcript chunks closest to the cluster centroid in embedding space (Option A/C, Step 17).
    """
    if len(cluster_embeddings) == 0:
        return []

    # Calculate cluster centroid vector
    centroid = np.mean(cluster_embeddings, axis=0)
    norm_centroid = np.linalg.norm(centroid)

    if norm_centroid == 0.0:
        # Fallback to first N
        candidates = cluster_metadata[:top_n]
    else:
        # Compute cosine similarity of each point to centroid
        norms = np.linalg.norm(cluster_embeddings, axis=1)
        norms[norms == 0.0] = 1e-9
        similarities = np.dot(cluster_embeddings, centroid) / (norms * norm_centroid)

        # Rank descending
        ranked_indices = similarities.argsort()[::-1][:top_n]
        candidates = [cluster_metadata[idx] for idx in ranked_indices]

    results: list[RepresentativeChunk] = []
    for m in candidates:
        spk_list = m.get("speaker_ids", [])
        spk = spk_list[0] if spk_list else "UNKNOWN"

        results.append(
            RepresentativeChunk(
                chunk_id=int(m.get("chunk_id", 0)),
                call_id=str(m.get("call_id", "")),
                speaker=spk,
                start=float(m.get("start", m.get("start_time", 0.0))),
                end=float(m.get("end", m.get("end_time", 0.0))),
                text=str(m.get("text", "")),
            )
        )
    return results


def compute_cluster_stats(
    cluster_id: int,
    cluster_embeddings: np.ndarray,
    cluster_metadata: list[dict[str, Any]],
    total_dataset_size: int,
    top_representative: int = 3,
) -> dict[str, Any]:
    """
    Compute comprehensive statistics and telemetry for a single cluster.

    Returns:
        Dictionary of computed statistics.
    """
    size = len(cluster_metadata)
    percentage = (size / total_dataset_size * 100.0) if total_dataset_size > 0 else 0.0

    # Calls and speakers distribution
    calls: set[str] = set()
    speakers: set[str] = set()
    intents: list[str] = []
    sentiments: list[str] = []

    for m in cluster_metadata:
        cid = str(m.get("call_id", ""))
        if cid:
            calls.add(cid)
        for s in m.get("speaker_ids", []):
            speakers.add(s)

        # Phase 5 intent metadata
        meta_dict = m.get("metadata", m.get("extra_metadata", {}))
        if isinstance(meta_dict, dict):
            if "intent" in meta_dict and meta_dict["intent"]:
                intents.append(str(meta_dict["intent"]))
            if "sentiment" in meta_dict and meta_dict["sentiment"]:
                sentiments.append(str(meta_dict["sentiment"]))

    # Normalize distributions to percentage
    intent_dist: dict[str, float] = {}
    if intents:
        i_counts = Counter(intents)
        intent_dist = {k: round(v / len(intents), 3) for k, v in i_counts.items()}

    sentiment_dist: dict[str, float] = {}
    if sentiments:
        s_counts = Counter(sentiments)
        sentiment_dist = {k: round(v / len(sentiments), 3) for k, v in s_counts.items()}

    rep_chunks = _find_representative_chunks(
        cluster_embeddings=cluster_embeddings,
        cluster_metadata=cluster_metadata,
        top_n=top_representative,
    )

    return {
        "cluster_id": cluster_id,
        "size": size,
        "percentage": percentage,
        "call_count": len(calls),
        "speaker_count": len(speakers),
        "intent_distribution": intent_dist,
        "sentiment_distribution": sentiment_dist,
        "representative_chunks": rep_chunks,
    }
