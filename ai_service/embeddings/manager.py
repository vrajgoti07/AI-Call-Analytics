"""
AI Call Analytics — Embedding Model Manager.

Provides thread-safe singleton lifecycle management and batch inference for
Sentence Transformers models (Step 3, 4, 5, 11, 12).
Validates vector dimensions and checks for numerical integrity (no NaN/Inf).
"""

from __future__ import annotations

import logging
import math
import threading
from typing import Any

import numpy as np

from ai_service.embeddings.config import EmbeddingConfig
from ai_service.embeddings.exceptions import (
    EmbeddingGenerationError,
    EmbeddingModelLoadError,
    InvalidEmbeddingDimension,
)

logger = logging.getLogger("ai_call_analytics.embeddings.manager")


class EmbeddingModelManager:
    """
    Singleton manager for SentenceTransformer text embedding models.
    Loads model weights once in memory and provides high-throughput batched encoding.
    """

    _cached_model: Any | None = None
    _cached_model_name: str | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        model: Any | None = None,
    ) -> None:
        """
        Initialize the embedding model manager.

        Args:
            config: Optional EmbeddingConfig. If omitted, uses default/env configuration.
            model: Optional pre-loaded model instance (for dependency injection/testing).
        """
        self.config = config or EmbeddingConfig.from_env()
        self._model = model

    def _get_model(self) -> Any:
        """Retrieve cached model or load from disk/HuggingFace with thread safety."""
        if self._model is not None:
            return self._model

        with self._lock:
            if (
                EmbeddingModelManager._cached_model is not None
                and EmbeddingModelManager._cached_model_name == self.config.model_name
            ):
                return EmbeddingModelManager._cached_model

            logger.info(
                "Loading SentenceTransformer model '%s' on device '%s'...",
                self.config.model_name,
                self.config.device,
            )
            try:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(
                    self.config.model_name,
                    device=self.config.device,
                )
                EmbeddingModelManager._cached_model = model
                EmbeddingModelManager._cached_model_name = self.config.model_name
                return model
            except Exception as err:
                logger.error("Failed to load embedding model '%s': %s", self.config.model_name, err)
                raise EmbeddingModelLoadError(
                    f"Failed to load embedding model '{self.config.model_name}': {err}"
                ) from err

    def _validate_vector(self, vec: list[float] | np.ndarray) -> list[float]:
        """Validate vector dimensionality, numerical integrity, and absence of NaN/Inf."""
        arr = np.asarray(vec, dtype=np.float32)
        if arr.shape[0] != self.config.dimension:
            raise InvalidEmbeddingDimension(
                f"Embedding dimension mismatch: expected {self.config.dimension}, got {arr.shape[0]}"
            )
        if np.isnan(arr).any():
            raise EmbeddingGenerationError("Embedding vector contains NaN values")
        if np.isinf(arr).any():
            raise EmbeddingGenerationError("Embedding vector contains Infinite values")
        return [float(x) for x in arr]

    def embed(self, text: str) -> list[float]:
        """
        Generate a normalized embedding vector for a single text utterance (Step 11).

        Args:
            text: Input conversational text or search query.

        Returns:
            Normalized float vector of length `config.dimension`.
        """
        clean_text = text.strip()
        if not clean_text:
            # Return zero vector for empty text
            return [0.0] * self.config.dimension

        model = self._get_model()
        try:
            vec = model.encode(
                clean_text,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )
            return self._validate_vector(vec)
        except (InvalidEmbeddingDimension, EmbeddingGenerationError):
            raise
        except Exception as err:
            logger.error("Embedding generation failed for text: %s", err)
            raise EmbeddingGenerationError(f"Embedding generation failed: {err}") from err

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts using efficient mini-batching (Step 11).

        Args:
            texts: List of text chunks or sentences.

        Returns:
            List of float embedding vectors matching input order.
        """
        if not texts:
            return []

        # Replace pure empty strings with placeholder spaces to maintain batch alignment
        clean_texts = [t.strip() if t.strip() else " " for t in texts]

        model = self._get_model()
        try:
            vectors = model.encode(
                clean_texts,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )
            return [self._validate_vector(v) for v in vectors]
        except (InvalidEmbeddingDimension, EmbeddingGenerationError):
            raise
        except Exception as err:
            logger.error("Batched embedding generation failed: %s", err)
            raise EmbeddingGenerationError(f"Batch embedding generation failed: {err}") from err
