"""
AI Call Analytics — Diarization Model Manager.

Provides a thread-safe singleton cache for pyannote.audio pipelines to ensure
neural networks and clustering models are loaded into memory once and reused
across audio recordings.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from ai_service.diarization.config import DiarizationConfig, DEFAULT_DIARIZATION_CONFIG
from ai_service.diarization.exceptions import DiarizationModelLoadError

logger = logging.getLogger("ai_call_analytics.diarization.model_manager")


class DiarizationModelManager:
    """
    Thread-safe registry and cache for pyannote.audio diarization pipelines.

    Prevents reloading large acoustic embeddings and segmentation models
    on every call processing request.
    """

    _instance: DiarizationModelManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._pipelines: dict[tuple[str, str], Any] = {}
        self._init_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> DiarizationModelManager:
        """Retrieve the singleton model manager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_pipeline(self, config: DiarizationConfig | None = None) -> Any:
        """
        Retrieve or load a pyannote diarization pipeline matching the configuration.

        Args:
            config: DiarizationConfig instance. Defaults to DEFAULT_DIARIZATION_CONFIG.

        Returns:
            pyannote.audio.Pipeline instance ready for inference.

        Raises:
            DiarizationModelLoadError: If loading fails due to missing auth token,
            unaccepted gated repository agreements, or network/device issues.
        """
        cfg = config or DEFAULT_DIARIZATION_CONFIG
        device = cfg.resolve_device()

        cache_key = (cfg.model_name, device)

        with self._init_lock:
            if cache_key in self._pipelines:
                logger.debug("Reusing cached Diarization pipeline: %s on %s", cfg.model_name, device)
                return self._pipelines[cache_key]

            logger.info("Loading pyannote diarization pipeline '%s' on device '%s'...", cfg.model_name, device)

            try:
                import torch
                from pyannote.audio import Pipeline
            except ImportError as err:
                raise DiarizationModelLoadError(
                    "pyannote.audio or torch is not installed. Please install via 'pip install pyannote.audio'."
                ) from err

            token = cfg.hf_token
            if not token:
                raise DiarizationModelLoadError(
                    f"A Hugging Face access token is required to load pyannote pipeline '{cfg.model_name}'. "
                    "Please set the HF_TOKEN or HUGGINGFACE_TOKEN environment variable."
                )

            try:
                pipeline = Pipeline.from_pretrained(
                    cfg.model_name,
                    token=token,
                    cache_dir=cfg.cache_dir,
                )
            except Exception as err:
                logger.error("Failed to load pyannote pipeline '%s': %s", cfg.model_name, err)
                raise DiarizationModelLoadError(
                    f"Failed to load pyannote diarization pipeline '{cfg.model_name}': {err}. "
                    "Please verify that: 1) Your HF_TOKEN is valid, 2) You have visited "
                    f"https://huggingface.co/{cfg.model_name} and accepted the user terms, "
                    "and 3) You have accepted user terms for 'pyannote/segmentation-3.0'."
                ) from err

            if pipeline is None:
                raise DiarizationModelLoadError(
                    f"Pipeline.from_pretrained('{cfg.model_name}') returned None. "
                    "Please verify your Hugging Face token permissions."
                )

            # Assign to target compute device
            try:
                pipeline.to(torch.device(device))
            except Exception as err:
                logger.warning("Could not move pipeline to %s, using default device: %s", device, err)

            self._pipelines[cache_key] = pipeline
            logger.info("Successfully loaded and cached pyannote pipeline '%s' on %s", cfg.model_name, device)
            return pipeline

    @property
    def loaded_model_count(self) -> int:
        """Number of active diarization pipelines cached in memory."""
        with self._init_lock:
            return len(self._pipelines)

    def is_pipeline_loaded(self, config: DiarizationConfig) -> bool:
        """Check if pipeline matching config is currently cached in memory."""
        device = config.resolve_device()
        cache_key = (config.model_name, device)
        with self._init_lock:
            return cache_key in self._pipelines

    def clear_cache(self) -> None:
        """Evict all cached pipelines from memory."""
        with self._init_lock:
            self._pipelines.clear()
            logger.info("Diarization model cache cleared.")
