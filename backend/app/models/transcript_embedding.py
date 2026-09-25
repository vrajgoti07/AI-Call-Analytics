"""
AI Call Analytics — Transcript Chunk Embedding ORM Model (Step 13, 14, 16, 17, 19, 20).

Stores vectorized conversational transcript chunks with their speaker attribution,
temporal boundaries, model versioning metadata, and HNSW vector index in pgvector.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base

DEFAULT_EMBEDDING_DIM = 384


class TranscriptEmbedding(Base):
    """
    PostgreSQL + pgvector model storing text chunks with high-dimensional vector embeddings.
    """

    __tablename__ = "transcript_embeddings"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Call and chunk identifiers
    call_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    chunk_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Conversational text and speech timing
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)

    # Speaker and turn provenance
    speaker_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    turn_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)

    # Vector embedding column with exact dimension
    embedding: Mapped[list[float]] = mapped_column(
        Vector(DEFAULT_EMBEDDING_DIM),
        nullable=False,
    )

    # Model provenance (Step 20: prevents mixing vectors from different spaces)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="1.0.0")
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_EMBEDDING_DIM)

    # Additional contextual metadata (sentiment, intent, tags)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        # Idempotency constraint (Step 19)
        UniqueConstraint(
            "call_id",
            "chunk_id",
            "model_name",
            name="uq_transcript_embeddings_call_chunk_model",
        ),
        # HNSW Cosine Similarity Vector Index (Step 16, 17)
        Index(
            "ix_transcript_embeddings_vector_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize embedding record to dictionary."""
        return {
            "id": str(self.id),
            "call_id": self.call_id,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "speaker_ids": list(self.speaker_ids),
            "turn_ids": list(self.turn_ids),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "embedding_dimension": self.embedding_dimension,
            "extra_metadata": dict(self.extra_metadata),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
