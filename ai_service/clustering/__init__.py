"""AI Call Analytics — Clustering & Theme Discovery Layer (Phase 7)."""

from ai_service.clustering.clusterer import HDBSCANClusterer
from ai_service.clustering.config import ThemeDiscoveryConfig
from ai_service.clustering.exceptions import (
    ClusteringExecutionError,
    DimensionalityReductionError,
    InsufficientEmbeddingsError,
    InvalidEmbeddingDataError,
    KeywordExtractionError,
    ThemeDiscoveryError,
    ThemePersistenceError,
)
from ai_service.clustering.keywords import ThemeKeywordExtractor
from ai_service.clustering.labeling import ThemeLabeler
from ai_service.clustering.loader import EmbeddingLoader
from ai_service.clustering.pipeline import ThemeDiscoveryService
from ai_service.clustering.reducer import UMAPReducer
from ai_service.clustering.schema import (
    RepresentativeChunk,
    ThemeDiscoveryResult,
    ThemeMembershipRecord,
    ThemeRecord,
)

__all__ = [
    "ThemeDiscoveryConfig",
    "ThemeDiscoveryError",
    "InsufficientEmbeddingsError",
    "InvalidEmbeddingDataError",
    "DimensionalityReductionError",
    "ClusteringExecutionError",
    "KeywordExtractionError",
    "ThemePersistenceError",
    "RepresentativeChunk",
    "ThemeRecord",
    "ThemeMembershipRecord",
    "ThemeDiscoveryResult",
    "EmbeddingLoader",
    "UMAPReducer",
    "HDBSCANClusterer",
    "ThemeKeywordExtractor",
    "ThemeLabeler",
    "ThemeDiscoveryService",
]
