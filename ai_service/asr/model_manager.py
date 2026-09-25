"""
AI Call Analytics — Whisper Model Manager.

Provides a thread-safe singleton cache for faster-whisper models to ensure
models are loaded into memory once and reused across batch calls.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from ai_service.asr.config import WhisperConfig, DEFAULT_WHISPER_CONFIG
from ai_service.asr.exceptions import ModelConfigurationError, ModelLoadError

logger = logging.getLogger("ai_call_analytics.asr.model_manager")


class WhisperModelManager:
    """
    Thread-safe registry and cache for faster-whisper model instances.

    Prevents reloading large neural network weights on every audio transcription,
    dramatically reducing latency and memory fragmentation.
    """

    _instance: WhisperModelManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._models: dict[tuple[str, str, str, str | None], Any] = {}
        self._init_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> WhisperModelManager:
        """Retrieve the singleton model manager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_model(self, config: WhisperConfig | None = None) -> Any:
        """
        Retrieve or initialize a faster-whisper model matching the configuration.

        Args:
            config: WhisperConfig instance. Defaults to DEFAULT_WHISPER_CONFIG.

        Returns:
            faster_whisper.WhisperModel instance.

        Raises:
            ModelLoadError: If faster-whisper fails to download or initialize weights.
            ModelConfigurationError: If requested model parameters are invalid.
        """
        cfg = config or DEFAULT_WHISPER_CONFIG
        device, compute_type = cfg.resolve_runtime()

        cache_key = (cfg.model_size, device, compute_type, cfg.download_root)

        with self._init_lock:
            if cache_key in self._models:
                logger.debug("Reusing cached Whisper model: %s (%s, %s)", cfg.model_size, device, compute_type)
                return self._models[cache_key]

            logger.info(
                "Loading faster-whisper model: size=%s, device=%s, compute_type=%s, cpu_threads=%d",
                cfg.model_size,
                device,
                compute_type,
                cfg.cpu_threads,
            )

            try:
                from faster_whisper import WhisperModel
            except ImportError as err:
                raise ModelLoadError(
                    "faster-whisper is not installed. Please install it via 'pip install faster-whisper'."
                ) from err

            try:
                model = WhisperModel(
                    cfg.model_size,
                    device=device,
                    device_index=cfg.device_index,
                    compute_type=compute_type,
                    cpu_threads=cfg.cpu_threads,
                    num_workers=cfg.num_workers,
                    download_root=cfg.download_root,
                )
                self._models[cache_key] = model
                logger.info("Successfully loaded and cached Whisper model '%s'", cfg.model_size)
                return model
            except Exception as err:
                logger.error("Failed to load faster-whisper model '%s': %s", cfg.model_size, err)
                raise ModelLoadError(
                    f"Failed to load Whisper model '{cfg.model_size}' on device '{device}': {err}"
                ) from err

    def is_model_loaded(self, config: WhisperConfig) -> bool:
        """Check if a model matching the config is currently cached in memory."""
        device, compute_type = config.resolve_runtime()
        cache_key = (config.model_size, device, compute_type, config.download_root)
        with self._init_lock:
            return cache_key in self._models

    @property
    def loaded_model_count(self) -> int:
        """Return the number of distinct models currently cached in memory."""
        with self._init_lock:
            return len(self._models)

    def clear_cache(self) -> None:
        """Evict all cached models from memory."""
        with self._init_lock:
            self._models.clear()
            logger.info("Whisper model cache cleared.")

