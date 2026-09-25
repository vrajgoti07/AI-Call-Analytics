"""
AI Call Analytics — Whisper & ASR Configuration.

Centralizes all parameters for model sizing, runtime device selection,
quantized compute types, beam search, VAD filtering, and hallucination thresholds.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ai_service.asr.exceptions import ModelConfigurationError, UnsupportedRuntimeError

logger = logging.getLogger("ai_call_analytics.asr.config")

SUPPORTED_MODEL_SIZES = {
    "tiny", "tiny.en",
    "base", "base.en",
    "small", "small.en",
    "medium", "medium.en",
    "large", "large-v1", "large-v2", "large-v3", "large-v3-turbo", "turbo",
}


def _is_cuda_usable() -> bool:
    """Test if CUDA GPU and runtime libraries (cuBLAS 12) are genuinely functional on host."""
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() == 0:
            return False
        if sys.platform == "win32":
            import ctypes.util
            # ctranslate2 (CUDA 12 build) strictly requires cublas64_12.dll
            has_cublas12 = (
                ctypes.util.find_library("cublas64_12.dll") is not None
                or ctypes.util.find_library("cublas64_12") is not None
            )
            if not has_cublas12:
                return False
        return True
    except Exception:
        return False


@dataclass
class WhisperConfig:
    """Configuration settings for faster-whisper speech recognition."""

    # Model specification
    model_size: str = "base"  # 'tiny', 'base', 'small', 'medium', 'large-v3'
    device: str = "auto"      # 'cpu', 'cuda', 'auto'
    device_index: int = 0
    compute_type: str = "auto"  # 'int8', 'float16', 'float32', 'auto', 'default'
    cpu_threads: int = 4
    num_workers: int = 1
    download_root: str | None = None  # Cache directory (defaults to HF_HOME / models)

    # Transcription parameters
    language: str = "auto"    # 'auto' for dynamic detection, or ISO code (e.g. 'en')
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0  # Greedy decoding for deterministic results
    word_timestamps: bool = True

    # Voice Activity Detection (Preserved by default for call analysis)
    vad_filter: bool = False
    min_vad_silence_ms: int = 500

    # Hallucination / Quality detection thresholds
    repetition_threshold: int = 3  # Warn if exact same phrase repeated 3+ times
    no_speech_threshold: float = 0.6  # Warn if segment no_speech_prob exceeds 0.6

    @classmethod
    def from_env(cls) -> WhisperConfig:
        """Create WhisperConfig from environment variable overrides."""
        model_size = os.environ.get("WHISPER_MODEL_SIZE", "base")
        device = os.environ.get("WHISPER_DEVICE", os.environ.get("DEVICE", "auto")).lower()
        compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "auto")
        language = os.environ.get("WHISPER_LANGUAGE", "auto")
        beam_size = int(os.environ.get("WHISPER_BEAM_SIZE", "5"))
        vad_filter = os.environ.get("WHISPER_VAD_FILTER", "false").lower() in ("true", "1", "yes")
        download_root = os.environ.get("HF_HOME") or "./models/huggingface"

        return cls(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            download_root=download_root,
        )

    def resolve_runtime(self) -> tuple[str, str]:
        """
        Validate and resolve effective device and compute type against host capabilities.

        Returns:
            Tuple of (effective_device, effective_compute_type).
        """
        # Validate model size
        if self.model_size not in SUPPORTED_MODEL_SIZES:
            raise ModelConfigurationError(
                f"Unsupported Whisper model size: '{self.model_size}'. "
                f"Supported sizes: {sorted(SUPPORTED_MODEL_SIZES)}"
            )

        eff_device = self.device.lower()
        if eff_device not in ("auto", "cpu", "cuda"):
            raise ModelConfigurationError(
                f"Unsupported device: '{self.device}'. Supported devices: 'auto', 'cpu', 'cuda'"
            )

        try:
            import ctranslate2
        except ImportError:
            return self.device, self.compute_type

        # 1. Resolve Device
        cuda_usable = _is_cuda_usable()

        if eff_device == "auto":
            eff_device = "cuda" if cuda_usable else "cpu"
        elif eff_device == "cuda" and not cuda_usable:
            raise UnsupportedRuntimeError(
                "CUDA requested for Whisper ASR, but no compatible CUDA GPU or runtime libraries "
                "(e.g. cuBLAS / cublas64_12.dll) were found on this system."
            )

        # 2. Resolve Compute Type
        eff_compute = self.compute_type.lower()
        supported_types = ctranslate2.get_supported_compute_types(eff_device)

        if eff_compute in ("auto", "default"):
            if eff_device == "cuda":
                eff_compute = "float16" if "float16" in supported_types else "float32"
            else:
                eff_compute = "int8" if "int8" in supported_types else "float32"
        elif eff_compute not in supported_types:
            fallback = "int8" if "int8" in supported_types else "float32"
            logger.warning(
                "Compute type '%s' is not supported on device '%s' (supported: %s). Falling back to '%s'.",
                eff_compute,
                eff_device,
                supported_types,
                fallback,
            )
            eff_compute = fallback

        return eff_device, eff_compute


DEFAULT_WHISPER_CONFIG = WhisperConfig()
