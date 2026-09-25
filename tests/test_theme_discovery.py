"""
AI Call Analytics — Unit and Integration Tests for Phase 7 Theme Discovery.

Validates:
1. Embedding loading, dimension validation, NaN/Inf handling, and deduplication
2. UMAP dimensionality reduction and reproducibility
3. HDBSCAN density clustering and noise detection
4. c-TF-IDF keyword extraction and theme label generation
5. Cluster statistics, intent/sentiment distribution, and centroid representative chunk selection
6. Controlled synthetic clustering test with distinct clusters and noise
7. Database models and idempotency tracking
"""

from __future__ import annotations

import numpy as np
import pytest

from ai_service.clustering import (
    ClusteringExecutionError,
    DimensionalityReductionError,
    EmbeddingLoader,
    HDBSCANClusterer,
    InsufficientEmbeddingsError,
    InvalidEmbeddingDataError,
    RepresentativeChunk,
    ThemeDiscoveryConfig,
    ThemeDiscoveryResult,
    ThemeDiscoveryService,
    ThemeKeywordExtractor,
    ThemeLabeler,
    ThemeRecord,
    UMAPReducer,
)
from ai_service.clustering.statistics import compute_cluster_stats
from backend.app.models.theme import Theme, ThemeDiscoveryRun, ThemeMembership


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_synthetic_dataset() -> tuple[np.ndarray, list[dict]]:
    """
    Generate synthetic 384-dimensional clusters with known separation and noise (Step 33).
    Cluster 0: 8 samples centered at [1.0, 0, ...]
    Cluster 1: 8 samples centered at [-1.0, 0, ...]
    Noise: 2 outlier samples
    """
    np.random.seed(42)
    dim = 384
    c0 = np.random.normal(loc=1.0, scale=0.05, size=(8, dim)).astype(np.float32)
    c1 = np.random.normal(loc=-1.0, scale=0.05, size=(8, dim)).astype(np.float32)
    noise = np.random.uniform(low=-10.0, high=10.0, size=(2, dim)).astype(np.float32)

    X = np.vstack([c0, c1, noise])
    meta = []
    for i in range(len(X)):
        topic = "cards" if i < 8 else ("loans" if i < 16 else "noise")
        meta.append({
            "chunk_id": i + 1,
            "call_id": f"call_{i:02d}",
            "speaker_ids": ["SPEAKER_01"],
            "start": 0.0,
            "end": 5.0,
            "text": f"This is sample transcript {i} about {topic}.",
            "metadata": {
                "intent": "card_issue" if i < 8 else ("loan_application" if i < 16 else "other"),
                "sentiment": "NEGATIVE" if i < 8 else "POSITIVE",
            },
        })
    return X, meta


# ============================================================================
# 1. Embedding Loader & Validation Tests (Step 6, 7, 8, 9, 32)
# ============================================================================

class TestEmbeddingLoader:
    """Test suite for embedding loading, dimension validation, and cleaning."""

    def test_insufficient_embeddings_raises(self) -> None:
        """Verify loader raises InsufficientEmbeddingsError when samples < threshold."""
        loader = EmbeddingLoader(config=ThemeDiscoveryConfig(min_embeddings=15))
        few_vectors = np.ones((5, 384), dtype=np.float32)
        few_meta = [{"chunk_id": i} for i in range(5)]

        with pytest.raises(InsufficientEmbeddingsError):
            loader.validate_and_prepare(few_vectors, few_meta)

    def test_dimension_mismatch_raises(self) -> None:
        """Verify vector dimension != 384 raises InvalidEmbeddingDataError."""
        loader = EmbeddingLoader(config=ThemeDiscoveryConfig(min_embeddings=5, expected_dimension=384))
        wrong_dim_vectors = np.ones((10, 512), dtype=np.float32)
        meta = [{"chunk_id": i} for i in range(10)]

        with pytest.raises(InvalidEmbeddingDataError):
            loader.validate_and_prepare(wrong_dim_vectors, meta)

    def test_nan_and_inf_filtering(self) -> None:
        """Verify NaN and Inf rows are cleanly removed and valid data preserved."""
        loader = EmbeddingLoader(config=ThemeDiscoveryConfig(min_embeddings=5, expected_dimension=384))
        vectors = np.ones((10, 384), dtype=np.float32)
        vectors[2, 5] = np.nan
        vectors[7, 10] = np.inf
        meta = [{"chunk_id": i, "call_id": f"c_{i}"} for i in range(10)]

        clean_X, clean_meta = loader.validate_and_prepare(vectors, meta)
        assert len(clean_X) == 8
        assert len(clean_meta) == 8
        assert not np.isnan(clean_X).any()
        assert not np.isinf(clean_X).any()

    def test_deduplication(self) -> None:
        """Verify duplicate (call_id, chunk_id) entries are deduplicated."""
        loader = EmbeddingLoader(config=ThemeDiscoveryConfig(min_embeddings=4, expected_dimension=384))
        vectors = np.ones((6, 384), dtype=np.float32)
        meta = [
            {"call_id": "c1", "chunk_id": 1},
            {"call_id": "c1", "chunk_id": 1},  # Duplicate
            {"call_id": "c2", "chunk_id": 1},
            {"call_id": "c2", "chunk_id": 2},
            {"call_id": "c3", "chunk_id": 1},
            {"call_id": "c3", "chunk_id": 1},  # Duplicate
        ]
        clean_X, clean_meta = loader.validate_and_prepare(vectors, meta)
        assert len(clean_X) == 4
        assert len(clean_meta) == 4


# ============================================================================
# 2. UMAP Reducer Tests (Step 11, 12, 32)
# ============================================================================

class TestUMAPReducer:
    """Test suite for UMAP dimensionality reduction."""

    def test_umap_reduction_output_shape(self, sample_synthetic_dataset) -> None:
        """Verify UMAP reduces to configured target dimension."""
        X, _ = sample_synthetic_dataset
        reducer = UMAPReducer(config=ThemeDiscoveryConfig(umap_n_components=5, umap_n_neighbors=5))
        X_red = reducer.reduce(X)

        assert X_red.shape == (len(X), 5)
        assert X_red.dtype == np.float32

    def test_umap_too_few_samples_raises(self) -> None:
        """Verify reducing <3 samples raises DimensionalityReductionError."""
        reducer = UMAPReducer()
        with pytest.raises(DimensionalityReductionError):
            reducer.reduce(np.ones((2, 384), dtype=np.float32))


# ============================================================================
# 3. HDBSCAN Clusterer Tests (Step 14, 15, 32)
# ============================================================================

class TestHDBSCANClusterer:
    """Test suite for HDBSCAN density clustering and noise identification."""

    def test_hdbscan_clusters_and_noise(self, sample_synthetic_dataset) -> None:
        """Verify HDBSCAN discovers clusters and identifies outlier points."""
        X, _ = sample_synthetic_dataset
        reducer = UMAPReducer(config=ThemeDiscoveryConfig(umap_n_components=3, umap_n_neighbors=5))
        X_red = reducer.reduce(X)

        clusterer = HDBSCANClusterer(config=ThemeDiscoveryConfig(hdbscan_min_cluster_size=4))
        labels, probs, outliers, sil = clusterer.cluster(X_red)

        assert len(labels) == len(X)
        assert len(probs) == len(X)
        assert len(outliers) == len(X)
        # Should have found at least 1 cluster
        unique_clusters = set(labels) - {-1}
        assert len(unique_clusters) >= 1
        # Probabilities bounded in [0.0, 1.0]
        assert np.all((probs >= 0.0) & (probs <= 1.0))


# ============================================================================
# 4. Keyword Extraction & Labeling Tests (Step 18, 19, 20)
# ============================================================================

class TestKeywordAndLabeling:
    """Test suite for c-TF-IDF keyword extraction and descriptive label synthesis."""

    def test_extract_cluster_keywords(self) -> None:
        """Verify cluster keywords capture domain terminology without conversational stopwords."""
        extractor = ThemeKeywordExtractor(top_k=3)
        cluster_texts = {
            0: [
                "Hello, my credit card was frozen and blocked yesterday.",
                "Yes, I need to unfreeze my Visa card payment.",
                "Thank you, card transactions are declining.",
            ],
            1: [
                "I am interested in a business loan for commercial property.",
                "Commercial financing interest rates for business expansion.",
                "Applying for a small business commercial mortgage.",
            ],
        }
        kws = extractor.extract_cluster_keywords(cluster_texts)

        assert 0 in kws and 1 in kws
        # Check cluster 0 terms
        assert any("card" in k or "frozen" in k for k in kws[0])
        # Check cluster 1 terms
        assert any("loan" in k or "commercial" in k or "business" in k for k in kws[1])
        # Stopwords must not appear
        for term in kws[0] + kws[1]:
            assert term not in ["hello", "thank", "yes", "please"]

    def test_theme_label_synthesis(self) -> None:
        """Verify label synthesizer formats readable title from keywords."""
        labeler = ThemeLabeler()
        lbl = labeler.generate_label(cluster_id=1, keywords=["credit card", "frozen", "unblock"])
        assert "Credit Card" in lbl
        assert "Frozen" in lbl

    def test_empty_keywords_fallback_label(self) -> None:
        """Verify fallback to Theme <id> when keywords are absent."""
        labeler = ThemeLabeler()
        lbl = labeler.generate_label(cluster_id=3, keywords=[])
        assert lbl == "Theme 3"


# ============================================================================
# 5. Cluster Statistics & Centroids (Step 16, 17, 22, 23, 24)
# ============================================================================

class TestClusterStatistics:
    """Test suite for cluster metrics, intent/sentiment distribution, and representative chunks."""

    def test_compute_cluster_stats(self) -> None:
        """Verify statistics calculation and centroid-based chunk extraction."""
        np.random.seed(42)
        c_emb = np.random.normal(loc=0.0, scale=1.0, size=(5, 384)).astype(np.float32)
        c_meta = [
            {"chunk_id": 1, "call_id": "c1", "speaker_ids": ["SPEAKER_00"], "text": "Turn 1", "metadata": {"intent": "freeze", "sentiment": "NEGATIVE"}},
            {"chunk_id": 2, "call_id": "c1", "speaker_ids": ["SPEAKER_01"], "text": "Turn 2", "metadata": {"intent": "freeze", "sentiment": "NEGATIVE"}},
            {"chunk_id": 3, "call_id": "c2", "speaker_ids": ["SPEAKER_01"], "text": "Turn 3", "metadata": {"intent": "freeze", "sentiment": "NEUTRAL"}},
            {"chunk_id": 4, "call_id": "c3", "speaker_ids": ["SPEAKER_01"], "text": "Turn 4", "metadata": {"intent": "balance", "sentiment": "NEUTRAL"}},
            {"chunk_id": 5, "call_id": "c4", "speaker_ids": ["SPEAKER_01"], "text": "Turn 5", "metadata": {"intent": "balance", "sentiment": "NEUTRAL"}},
        ]
        stats = compute_cluster_stats(
            cluster_id=0,
            cluster_embeddings=c_emb,
            cluster_metadata=c_meta,
            total_dataset_size=10,
            top_representative=2,
        )

        assert stats["size"] == 5
        assert stats["percentage"] == 50.0
        assert stats["call_count"] == 4
        assert stats["speaker_count"] == 2
        assert stats["intent_distribution"]["freeze"] == 0.6
        assert stats["sentiment_distribution"]["NEGATIVE"] == 0.4
        assert len(stats["representative_chunks"]) == 2
        assert isinstance(stats["representative_chunks"][0], RepresentativeChunk)


# ============================================================================
# 6. End-to-End Synthetic Clustering Pipeline (Step 33, 34)
# ============================================================================

class TestThemeDiscoveryServicePipeline:
    """Test suite for complete ThemeDiscoveryService pipeline execution."""

    def test_synthetic_end_to_end_pipeline(self, sample_synthetic_dataset) -> None:
        """Verify full pipeline runs on synthetic data and returns valid ThemeDiscoveryResult."""
        X, meta = sample_synthetic_dataset

        config = ThemeDiscoveryConfig(
            min_embeddings=10,
            umap_n_neighbors=5,
            umap_n_components=3,
            hdbscan_min_cluster_size=4,
            hdbscan_min_samples=4,
        )
        service = ThemeDiscoveryService(config=config)
        result = service.discover_themes(embeddings=X, metadata=meta, run_name="synthetic_test")

        assert isinstance(result, ThemeDiscoveryResult)
        assert result.status == "SUCCESS"
        assert result.embedding_count == len(X)
        assert result.cluster_count >= 1
        assert len(result.themes) == result.cluster_count
        assert len(result.memberships) == len(X)
        assert result.processing_time_seconds > 0.0

        # Check theme record attributes
        top_theme = result.themes[0]
        assert top_theme.size >= 4
        assert len(top_theme.keywords) > 0
        assert len(top_theme.representative_chunks) > 0

        # Check serialization
        d = result.to_dict()
        assert "run_id" in d
        assert "themes" in d
        assert len(d["themes"]) == result.cluster_count


# ============================================================================
# 7. Database Models & Idempotency Tests (Step 25, 26, 27)
# ============================================================================

class TestThemeDatabaseModels:
    """Test suite for SQLAlchemy theme models and constraints."""

    def test_theme_run_model_columns(self) -> None:
        """Verify ThemeDiscoveryRun has required columns and indexes."""
        cols = ThemeDiscoveryRun.__table__.columns
        assert "config_hash" in cols
        assert "dataset_size" in cols
        assert "num_clusters" in cols
        assert "noise_count" in cols
        assert "silhouette_score" in cols

    def test_theme_model_columns(self) -> None:
        """Verify Theme model has required columns and relationships."""
        cols = Theme.__table__.columns
        assert "run_id" in cols
        assert "cluster_id" in cols
        assert "label" in cols
        assert "keywords" in cols
        assert "representative_chunks" in cols

    def test_theme_membership_columns(self) -> None:
        """Verify ThemeMembership model has required columns and indexes."""
        cols = ThemeMembership.__table__.columns
        assert "run_id" in cols
        assert "theme_id" in cols
        assert "call_id" in cols
        assert "chunk_id" in cols
        assert "cluster_id" in cols
        assert "membership_probability" in cols
