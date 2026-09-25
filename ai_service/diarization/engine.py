"""
AI Call Analytics — Pyannote Diarization Engine.

Executes acoustic speaker diarization using pyannote.audio pipelines,
extracts and orders speaker activity segments, calculates speaking stats,
and measures multi-speaker cross-talk overlap duration.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from ai_service.diarization.config import DiarizationConfig, DEFAULT_DIARIZATION_CONFIG
from ai_service.diarization.exceptions import (
    DiarizationInferenceError,
    DiarizationModelLoadError,
    NoSpeakersDetectedError,
)
from ai_service.diarization.model_manager import DiarizationModelManager
from ai_service.diarization.schema import (
    DiarizationMetadata,
    DiarizationResult,
    DiarizationSegment,
)
from ai_service.diarization.validator import (
    calculate_speaker_stats,
    compute_overlap_duration,
    validate_diarization_audio,
    validate_diarization_segments,
)

logger = logging.getLogger("ai_call_analytics.diarization.engine")


class PyannoteDiarizer:
    """
    Speaker diarization engine wrapping pyannote.audio pipelines.

    Processes standardized 16kHz mono PCM16 audio, identifies distinct speaker
    turns, and produces structured DiarizationResult objects.
    """

    def __init__(
        self,
        config: DiarizationConfig | None = None,
        pipeline: Any | None = None,
    ) -> None:
        """
        Initialize the diarizer.

        Args:
            config: Optional DiarizationConfig. Defaults to DEFAULT_DIARIZATION_CONFIG.
            pipeline: Optional pre-loaded pyannote Pipeline instance for testing/DI.
        """
        self.config = config or DEFAULT_DIARIZATION_CONFIG
        self._pipeline = pipeline

    def _get_pipeline(self) -> Any:
        """Retrieve pyannote pipeline from singleton manager or injected mock."""
        if self._pipeline is not None:
            return self._pipeline
        return DiarizationModelManager.get_instance().get_pipeline(self.config)

    def diarize(
        self,
        audio_path: str | Path,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> DiarizationResult:
        """
        Perform speaker diarization on standardized call audio.

        Args:
            audio_path: Path to standardized 16kHz mono PCM16 WAV.
            min_speakers: Optional lower bound on detected speakers.
            max_speakers: Optional upper bound on detected speakers.

        Returns:
            Structured DiarizationResult.

        Raises:
            FileNotFoundError: If audio file does not exist.
            InvalidPreprocessedAudioError: If audio fails the Phase 2 contract.
            DiarizationInferenceError: If pyannote fails during inference.
            NoSpeakersDetectedError: If no speech/speakers are found in audio.
        """
        path = Path(audio_path).resolve()

        # Step 1: Validate input audio adheres to Phase 2 contract (Step 5)
        audio_duration = validate_diarization_audio(path)

        eff_min = min_speakers if min_speakers is not None else self.config.min_speakers
        eff_max = max_speakers if max_speakers is not None else self.config.max_speakers
        eff_device = self.config.resolve_device()

        logger.info(
            "Starting diarization for '%s' (duration=%.2fs, min_spk=%s, max_spk=%s, device=%s)",
            path.name,
            audio_duration,
            eff_min,
            eff_max,
            eff_device,
        )

        start_time = time.perf_counter()

        try:
            pipeline = self._get_pipeline()

            # Prepare optional pyannote kwargs
            diarize_kwargs: dict[str, Any] = {}
            if eff_min is not None:
                diarize_kwargs["min_speakers"] = eff_min
            if eff_max is not None:
                diarize_kwargs["max_speakers"] = eff_max

            # Step 2: Execute pyannote pipeline
            annotation = pipeline(str(path), **diarize_kwargs)

        except (DiarizationModelLoadError, FileNotFoundError):
            raise
        except Exception as err:
            logger.error("Diarization inference failed for '%s': %s", path.name, err)
            raise DiarizationInferenceError(f"Diarization inference failed for '{path.name}': {err}") from err

        elapsed = time.perf_counter() - start_time
        rtf = round(elapsed / max(audio_duration, 1e-4), 3)

        # Step 3: Extract and sort diarization segments (Steps 9 & 10)
        raw_segments: list[DiarizationSegment] = []

        if hasattr(annotation, "itertracks"):
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                raw_segments.append(
                    DiarizationSegment(
                        speaker=str(speaker),
                        start=round(float(turn.start), 3),
                        end=round(float(turn.end), 3),
                    )
                )

        raw_segments.sort(key=lambda s: (s.start, s.end))

        # Check for empty detection
        if not raw_segments:
            logger.warning("No speakers detected in audio '%s'", path.name)

        # Step 4: Validate diarization timestamps and consistency (Step 11)
        val_warnings = validate_diarization_segments(raw_segments, audio_duration)

        # Step 5: Calculate multi-speaker overlap & conversational statistics (Steps 12 & 21)
        overlap_dur = compute_overlap_duration(raw_segments)
        overlap_detected = overlap_dur > 0.0

        speakers, speaker_stats, total_speech_time = calculate_speaker_stats(
            raw_segments, audio_duration
        )

        metadata = DiarizationMetadata(
            model_name=self.config.model_name,
            device=eff_device,
            min_speakers=eff_min,
            max_speakers=eff_max,
            audio_path=str(path),
        )

        logger.info(
            "Diarization completed for '%s' in %.2fs (RTF=%.3f, speakers=%d, segments=%d, overlap=%.2fs)",
            path.name,
            elapsed,
            rtf,
            len(speakers),
            len(raw_segments),
            overlap_dur,
        )

        return DiarizationResult(
            audio_path=str(path),
            audio_duration=audio_duration,
            speaker_segments=raw_segments,
            speakers=speakers,
            speaker_stats=speaker_stats,
            speech_duration=total_speech_time,
            overlap_duration=overlap_dur,
            overlap_detected=overlap_detected,
            processing_time_seconds=round(elapsed, 3),
            real_time_factor=rtf,
            metadata=metadata,
            warnings=val_warnings,
        )
