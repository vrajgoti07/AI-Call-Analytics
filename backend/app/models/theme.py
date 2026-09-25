"""
AI Call Analytics — Theme Discovery ORM Models (Step 25, 26).

Persists theme discovery execution runs, discovered themes, cluster statistics,
and individual transcript chunk memberships in PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base


class ThemeDiscoveryRun(Base):
    """
    Represents an individual execution of the Phase 7 theme discovery pipeline.
    Tracks hyperparameters, model provenance, and cluster validation metrics.
    """

    __tablename__ = "theme_discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_name: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=384)

    # Serialized UMAP and HDBSCAN hyperparameters
    umap_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    hdbscan_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    config_hash: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Telemetry
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False)
    num_clusters: Mapped[int] = mapped_column(Integer, nullable=False)
    noise_count: Mapped[int] = mapped_column(Integer, nullable=False)
    noise_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    silhouette_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SUCCESS")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    themes: Mapped[list[Theme]] = relationship("Theme", back_populates="run", cascade="all, delete-orphan")
    memberships: Mapped[list[ThemeMembership]] = relationship("ThemeMembership", back_populates="run", cascade="all, delete-orphan")


class Theme(Base):
    """
    A single discovered recurring conversational theme/cluster.
    """

    __tablename__ = "themes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("theme_discovery_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # Cluster metrics
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Categorical distributions
    intent_distribution: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    sentiment_distribution: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    representative_chunks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped[ThemeDiscoveryRun] = relationship("ThemeDiscoveryRun", back_populates="themes")
    memberships: Mapped[list[ThemeMembership]] = relationship("ThemeMembership", back_populates="theme", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("run_id", "cluster_id", name="uq_run_cluster"),
        Index("ix_themes_label", "label"),
    )


class ThemeMembership(Base):
    """
    Mapping assigning a specific transcript chunk to a discovered theme or noise (-1).
    """

    __tablename__ = "theme_memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("theme_discovery_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    theme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    call_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    chunk_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)  # -1 for noise
    membership_probability: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    outlier_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped[ThemeDiscoveryRun] = relationship("ThemeDiscoveryRun", back_populates="memberships")
    theme: Mapped[Theme | None] = relationship("Theme", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("run_id", "call_id", "chunk_id", name="uq_run_call_chunk"),
        Index("ix_theme_memberships_cluster_id", "cluster_id"),
    )
