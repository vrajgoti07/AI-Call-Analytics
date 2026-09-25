"""
AI Call Analytics — Theme Discovery Service & Pipeline Orchestrator.

Coordinates:
1. Embedding loading and validation (Step 6, 7, 8)
2. UMAP dimensionality reduction (Step 11, 12, 13)
3. HDBSCAN density clustering and noise isolation (Step 14, 15)
4. Cluster statistics and representative chunk extraction (Step 16, 17, 22, 23, 24)
5. c-TF-IDF keyword extraction and title labeling (Step 18, 19, 20)
6. Run persistence and idempotency tracking in PostgreSQL (Step 25, 26, 27, 28)
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_service.clustering.clusterer import HDBSCANClusterer
from ai_service.clustering.config import ThemeDiscoveryConfig
from ai_service.clustering.exceptions import (
    ClusteringExecutionError,
    InsufficientEmbeddingsError,
    ThemePersistenceError,
)
from ai_service.clustering.keywords import ThemeKeywordExtractor
from ai_service.clustering.labeling import ThemeLabeler
from ai_service.clustering.loader import EmbeddingLoader
from ai_service.clustering.reducer import UMAPReducer
from ai_service.clustering.schema import (
    ThemeDiscoveryResult,
    ThemeMembershipRecord,
    ThemeRecord,
)
from ai_service.clustering.statistics import compute_cluster_stats
from backend.app.models.theme import Theme, ThemeDiscoveryRun, ThemeMembership

logger = logging.getLogger("ai_call_analytics.clustering.pipeline")


class ThemeDiscoveryService:
    """
    Unified Phase 7 Theme Discovery Orchestrator.
    """

    def __init__(
        self,
        config: ThemeDiscoveryConfig | None = None,
        loader: EmbeddingLoader | None = None,
        reducer: UMAPReducer | None = None,
        clusterer: HDBSCANClusterer | None = None,
        keyword_extractor: ThemeKeywordExtractor | None = None,
        labeler: ThemeLabeler | None = None,
    ) -> None:
        """
        Initialize the Theme Discovery Service.
        """
        self.config = config or ThemeDiscoveryConfig.from_env()
        self.loader = loader or EmbeddingLoader(config=self.config)
        self.reducer = reducer or UMAPReducer(config=self.config)
        self.clusterer = clusterer or HDBSCANClusterer(config=self.config)
        self.keyword_extractor = keyword_extractor or ThemeKeywordExtractor(top_k=self.config.top_keywords)
        self.labeler = labeler or ThemeLabeler()

    def discover_themes(
        self,
        embeddings: list[list[float]] | np.ndarray | None = None,
        metadata: list[dict[str, Any]] | None = None,
        session: Session | None = None,
        run_name: str = "theme_run",
        call_ids: list[str] | None = None,
    ) -> ThemeDiscoveryResult:
        """
        Execute end-to-end theme discovery pipeline.

        Args:
            embeddings: Optional in-memory embeddings array or list.
            metadata: Aligned metadata dictionary list.
            session: Optional active SQLAlchemy session to load from / persist to PostgreSQL.
            run_name: Name label for this discovery run.
            call_ids: Optional list of call IDs to restrict search to.

        Returns:
            Structured ThemeDiscoveryResult.
        """
        start_time = time.perf_counter()
        config_hash = self.config.config_hash()

        # Step 1: Load and validate embeddings (Step 6, 7, 8, 9)
        if embeddings is None:
            if session is None:
                raise InsufficientEmbeddingsError("Either 'embeddings' array or a database 'session' must be provided.")
            X, clean_metadata = self.loader.load_from_db(session=session, call_ids=call_ids)
        else:
            if metadata is None:
                raise InsufficientEmbeddingsError("Metadata must accompany in-memory embeddings.")
            X, clean_metadata = self.loader.validate_and_prepare(embeddings, metadata)

        n_samples = len(X)
        logger.info(
            "Starting Phase 7 Theme Discovery on %d chunks (run='%s', hash=%s)",
            n_samples,
            run_name,
            config_hash,
        )

        # Step 2: UMAP Dimensionality Reduction (Step 11, 12, 13)
        X_reduced = self.reducer.reduce(X)

        # Step 3: HDBSCAN Clustering (Step 14, 15, 29)
        labels, probabilities, outlier_scores, silhouette = self.clusterer.cluster(X_reduced)

        # Step 4: Group chunks by cluster (ignoring noise -1)
        clusters_indices: dict[int, list[int]] = defaultdict(list)
        cluster_texts: dict[int, list[str]] = defaultdict(list)

        for idx, label in enumerate(labels):
            if label != -1:
                clusters_indices[int(label)].append(idx)
                cluster_texts[int(label)].append(str(clean_metadata[idx].get("text", "")))

        # Step 5: Extract keywords using c-TF-IDF (Step 18, 19)
        cluster_keywords = self.keyword_extractor.extract_cluster_keywords(cluster_texts)

        # Step 6: Compute cluster statistics & synthesize labels (Step 16, 17, 20, 22, 23, 24)
        themes: list[ThemeRecord] = []
        cluster_to_theme_id: dict[int, str] = {}

        for theme_num, cid in enumerate(sorted(clusters_indices.keys()), 1):
            indices = clusters_indices[cid]
            c_embeddings = X[indices]
            c_metadata = [clean_metadata[i] for i in indices]

            stats = compute_cluster_stats(
                cluster_id=cid,
                cluster_embeddings=c_embeddings,
                cluster_metadata=c_metadata,
                total_dataset_size=n_samples,
                top_representative=self.config.representative_chunks,
            )

            kws = cluster_keywords.get(cid, [f"theme_{cid}"])
            label_text = self.labeler.generate_label(cluster_id=cid, keywords=kws)
            theme_id = f"theme-{theme_num:03d}"
            cluster_to_theme_id[cid] = theme_id

            themes.append(
                ThemeRecord(
                    theme_id=theme_id,
                    cluster_id=cid,
                    label=label_text,
                    keywords=kws,
                    size=stats["size"],
                    percentage=stats["percentage"],
                    call_count=stats["call_count"],
                    speaker_count=stats["speaker_count"],
                    representative_chunks=stats["representative_chunks"],
                    intent_distribution=stats["intent_distribution"],
                    sentiment_distribution=stats["sentiment_distribution"],
                )
            )

        # Step 7: Create membership records (Step 14, 15)
        memberships: list[ThemeMembershipRecord] = []
        for idx in range(n_samples):
            meta = clean_metadata[idx]
            cid = int(labels[idx])
            t_id = cluster_to_theme_id.get(cid) if cid != -1 else None

            memberships.append(
                ThemeMembershipRecord(
                    chunk_id=int(meta.get("chunk_id", idx)),
                    call_id=str(meta.get("call_id", "call_unknown")),
                    cluster_id=cid,
                    theme_id=t_id,
                    membership_probability=float(probabilities[idx]),
                    outlier_score=float(outlier_scores[idx]),
                )
            )

        n_noise = int(np.sum(labels == -1))
        noise_pct = (n_noise / n_samples * 100.0) if n_samples > 0 else 0.0
        total_time = time.perf_counter() - start_time
        run_id = f"run-{uuid.uuid4().hex[:8]}"

        result = ThemeDiscoveryResult(
            run_id=run_id,
            config_hash=config_hash,
            embedding_count=n_samples,
            cluster_count=len(themes),
            noise_count=n_noise,
            noise_percentage=noise_pct,
            silhouette_score=silhouette,
            themes=themes,
            memberships=memberships,
            processing_time_seconds=total_time,
            status="SUCCESS",
        )

        # Step 8: Persistence in PostgreSQL (Step 25, 26, 27, 28)
        if session is not None:
            self._persist_run(result=result, session=session, run_name=run_name)

        logger.info(
            "Theme discovery finished in %.3fs: %d themes discovered, %d noise chunks (%.1f%%)",
            total_time,
            len(themes),
            n_noise,
            noise_pct,
        )
        return result

    def _persist_run(
        self,
        result: ThemeDiscoveryResult,
        session: Session,
        run_name: str,
    ) -> None:
        """
        Persist execution run, themes, and chunk memberships to PostgreSQL (Step 25, 28).
        """
        try:
            # Check idempotency: remove previous run with identical config_hash and run_name if re-running
            existing_run = session.execute(
                select(ThemeDiscoveryRun).where(
                    ThemeDiscoveryRun.config_hash == result.config_hash,
                    ThemeDiscoveryRun.run_name == run_name,
                )
            ).scalar_one_or_none()

            if existing_run:
                logger.info("Found existing run for config_hash '%s'. Replacing old run...", result.config_hash)
                session.delete(existing_run)
                session.flush()

            # Create ThemeDiscoveryRun
            db_run = ThemeDiscoveryRun(
                run_name=run_name,
                embedding_model=self.config.expected_model_name,
                embedding_dimension=self.config.expected_dimension,
                umap_config={
                    "n_neighbors": self.config.umap_n_neighbors,
                    "n_components": self.config.umap_n_components,
                    "min_dist": self.config.umap_min_dist,
                    "metric": self.config.umap_metric,
                    "random_state": self.config.umap_random_state,
                },
                hdbscan_config={
                    "min_cluster_size": self.config.hdbscan_min_cluster_size,
                    "min_samples": self.config.hdbscan_min_samples,
                    "metric": self.config.hdbscan_metric,
                    "cluster_selection_method": self.config.hdbscan_cluster_selection_method,
                },
                config_hash=result.config_hash,
                dataset_size=result.embedding_count,
                num_clusters=result.cluster_count,
                noise_count=result.noise_count,
                noise_percentage=result.noise_percentage,
                silhouette_score=result.silhouette_score,
                status="SUCCESS",
            )
            session.add(db_run)
            session.flush()

            # Create Themes
            cluster_theme_id_map: dict[int, uuid.UUID] = {}
            for t in result.themes:
                db_theme = Theme(
                    run_id=db_run.id,
                    cluster_id=t.cluster_id,
                    label=t.label,
                    keywords=t.keywords,
                    size=t.size,
                    percentage=t.percentage,
                    call_count=t.call_count,
                    speaker_count=t.speaker_count,
                    intent_distribution=t.intent_distribution,
                    sentiment_distribution=t.sentiment_distribution,
                    representative_chunks=[c.to_dict() for c in t.representative_chunks],
                    extra_metadata=t.metadata,
                )
                session.add(db_theme)
                session.flush()
                cluster_theme_id_map[t.cluster_id] = db_theme.id

            # Create Memberships
            for m in result.memberships:
                theme_uuid = cluster_theme_id_map.get(m.cluster_id) if m.cluster_id != -1 else None
                db_membership = ThemeMembership(
                    run_id=db_run.id,
                    theme_id=theme_uuid,
                    call_id=m.call_id,
                    chunk_id=m.chunk_id,
                    cluster_id=m.cluster_id,
                    membership_probability=m.membership_probability,
                    outlier_score=m.outlier_score,
                )
                session.add(db_membership)

            session.commit()
            logger.info("Successfully persisted ThemeDiscoveryRun '%s' (%s) to database.", run_name, db_run.id)

        except Exception as err:
            session.rollback()
            logger.error("Failed to persist theme discovery results: %s", err)
            raise ThemePersistenceError(f"Theme persistence failed: {err}") from err
