"""
AI Call Analytics — Theme Discovery & Clustering Exceptions.

Defines a clean, domain-specific exception hierarchy for embedding loading,
UMAP dimensionality reduction, HDBSCAN clustering, keyword extraction, and persistence.
"""

from __future__ import annotations


class ThemeDiscoveryError(Exception):
    """Base exception for all clustering and theme discovery errors."""


class InsufficientEmbeddingsError(ThemeDiscoveryError):
    """Raised when the number of valid embeddings is below the minimum clustering threshold."""


class InvalidEmbeddingDataError(ThemeDiscoveryError):
    """Raised when embeddings contain NaN, Inf, dimension mismatches, or missing identifiers."""


class DimensionalityReductionError(ThemeDiscoveryError):
    """Raised when UMAP transformation fails."""


class ClusteringExecutionError(ThemeDiscoveryError):
    """Raised when HDBSCAN density clustering fails."""


class KeywordExtractionError(ThemeDiscoveryError):
    """Raised when cluster-specific TF-IDF keyword extraction fails."""


class ThemePersistenceError(ThemeDiscoveryError):
    """Raised when saving theme runs, themes, or memberships to the database fails."""
