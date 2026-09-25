"""
AI Call Analytics — Speaker Diarization Configuration.

Defines parameters for pyannote.audio pipeline loading, Hugging Face authentication,
speaker count bounds, hardware device mapping, and Whisper alignment policies.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from ai_service.diarization.exceptions import DiarizationConfigurationError

logger = logging.getLogger("ai_call_analytics.diarization.config")


@dataclass
class DiarizationConfig:
    """Configuration settings for pyannote speaker diarization and alignment."""

    # Model and Hugging Face Authentication
    model_name: str = "pyannote/speaker-diarization-3.1"
    hf_token: str | None = None
    cache_dir: str | None = None

    # Hardware execution
    device: str = "auto"  # 'auto', 'cpu', 'cuda'

    # Speaker count constraints (Step 8: support auto or bounded, do NOT hardcode exactly 2)
    min_speakers: int | None = None
    max_speakers: int | None = None

    # Temporal collar tolerance in seconds (margin around boundaries)
    collar: float = 0.25

    # Cross-speaker Whisper segment policy (Step 16: 'dominant' or 'word_level')
    cross_speaker_policy: str = "dominant"

    @classmethod
    def from_env(cls) -> DiarizationConfig:
        """Construct DiarizationConfig from environment variables and .env file."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        model_name = os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization-3.1")
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        cache_dir = os.environ.get("HF_HOME") or "./models/huggingface"
        device = os.environ.get("DIARIZATION_DEVICE", os.environ.get("DEVICE", "auto")).lower()

        min_spk = os.environ.get("MIN_SPEAKERS")
        max_spk = os.environ.get("MAX_SPEAKERS")
        min_speakers = int(min_spk) if min_spk and min_spk.isdigit() else None
        max_speakers = int(max_spk) if max_spk and max_spk.isdigit() else None

        policy = os.environ.get("DIARIZATION_CROSS_SPEAKER_POLICY", "dominant").lower()

        return cls(
            model_name=model_name,
            hf_token=hf_token,
            cache_dir=cache_dir,
            device=device,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            cross_speaker_policy=policy,
        )

    def validate(self) -> None:
        """Validate configuration settings and speaker boundary logic."""
        if self.device not in ("auto", "cpu", "cuda"):
            raise DiarizationConfigurationError(
                f"Unsupported device: '{self.device}'. Supported options: 'auto', 'cpu', 'cuda'"
            )

        if self.min_speakers is not None and self.min_speakers < 1:
            raise DiarizationConfigurationError(
                f"min_speakers must be >= 1, got {self.min_speakers}"
            )

        if self.max_speakers is not None and self.max_speakers < 1:
            raise DiarizationConfigurationError(
                f"max_speakers must be >= 1, got {self.max_speakers}"
            )

        if (
            self.min_speakers is not None
            and self.max_speakers is not None
            and self.min_speakers > self.max_speakers
        ):
            raise DiarizationConfigurationError(
                f"min_speakers ({self.min_speakers}) cannot exceed max_speakers ({self.max_speakers})"
            )

        if self.cross_speaker_policy not in ("dominant", "word_level"):
            raise DiarizationConfigurationError(
                f"Unsupported cross_speaker_policy: '{self.cross_speaker_policy}'. "
                f"Supported: 'dominant', 'word_level'"
            )

    def resolve_device(self) -> str:
        """Resolve effective PyTorch compute device ('cpu' or 'cuda')."""
        self.validate()

        import torch

        eff_device = self.device.lower()
        cuda_available = torch.cuda.is_available()

        if eff_device == "auto":
            return "cuda" if cuda_available else "cpu"
        elif eff_device == "cuda":
            if not cuda_available:
                raise DiarizationConfigurationError(
                    "CUDA requested for pyannote diarization, but torch.cuda.is_available() is False."
                )
            return "cuda"
        return "cpu"


DEFAULT_DIARIZATION_CONFIG = DiarizationConfig()
