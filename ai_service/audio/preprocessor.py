"""
AI Call Analytics — Audio Preprocessing Pipeline Orchestrator.

Provides the unified AudioPreprocessor class that validates, converts,
normalizes, and verifies call audio into standardized 16kHz mono PCM16 WAV
ready for downstream Whisper transcription and Speaker Diarization.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import soundfile as sf

from ai_service.audio.config import AudioConfig, DEFAULT_AUDIO_CONFIG
from ai_service.audio.engine import process_audio_file
from ai_service.audio.exceptions import (
    AudioFileNotFoundError,
    AudioProcessingError,
    OutputValidationError,
    UnreadableAudioError,
    UnsupportedAudioFormatError,
)
from ai_service.audio.schema import AudioMetadata, AudioProcessingResult
from ai_service.audio.validator import extract_audio_metadata, validate_audio_file, verify_standardized_audio

logger = logging.getLogger("ai_call_analytics.audio.preprocessor")


class AudioPreprocessor:
    """
    Standardized Audio Preprocessing Pipeline.

    Converts heterogeneous call recordings (variable sample rates, stereo, MP3/FLAC/OGG/WAV)
    into uniform, speech-analysis optimized audio artifacts:
    - Container: WAV
    - Format: Linear PCM 16-bit
    - Sampling Rate: 16,000 Hz
    - Channels: 1 (Mono)
    - Amplitude: Peak-normalized (-1.0 dBFS)
    """

    def __init__(self, config: AudioConfig | None = None) -> None:
        """
        Initialize preprocessor with pipeline configuration.

        Args:
            config: Optional AudioConfig instance. Defaults to DEFAULT_AUDIO_CONFIG.
        """
        self.config = config or DEFAULT_AUDIO_CONFIG

    def resolve_output_path(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        call_id: str | None = None,
    ) -> Path:
        """
        Resolve the destination path for standardized audio.

        Hierarchy:
        1. Explicit output_path if provided.
        2. <output_dir>/<call_id>/audio.wav if call_id is provided.
        3. <output_dir>/<input_stem>_standardized.wav otherwise.

        Args:
            input_path: Source audio path.
            output_path: Optional explicit output destination.
            call_id: Optional unique call identifier.

        Returns:
            Resolved Path instance.
        """
        if output_path is not None:
            return Path(output_path).resolve()

        base_dir = Path(self.config.output_dir).resolve()
        if call_id is not None:
            return base_dir / call_id / f"audio.{self.config.target_format}"

        stem = Path(input_path).stem
        return base_dir / f"{stem}_standardized.{self.config.target_format}"

    def preprocess(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        call_id: str | None = None,
    ) -> AudioProcessingResult:
        """
        Execute end-to-end preprocessing on an input audio file.

        Steps:
        1. Validate input file and stream properties.
        2. Resolve output path and evaluate idempotency policy.
        3. Convert, resample to 16kHz, mix to mono, and normalize via safe temporary file.
        4. Run audio quality diagnostics (silence, clipping, amplitude).
        5. Atomically move temporary output to destination.
        6. Execute mandatory output validation (re-inspecting generated WAV).
        7. Collect and return structured AudioProcessingResult.

        Args:
            input_path: Path to source audio file.
            output_path: Optional explicit destination path.
            call_id: Optional unique call ID (used for structured directory storage).

        Returns:
            AudioProcessingResult instance.

        Raises:
            AudioProcessingError: If validation, conversion, or output verification fails.
        """
        start_time = time.perf_counter()
        in_p = Path(input_path).resolve()

        logger.info("Starting audio preprocessing for '%s'", in_p.name)

        # Step 1: Pre-validation
        val_result = validate_audio_file(in_p, self.config)
        if not val_result.valid:
            error_summary = "; ".join(val_result.errors)
            logger.error("Audio validation failed for '%s': %s", in_p.name, error_summary)
            if any("not found" in err.lower() for err in val_result.errors):
                raise AudioFileNotFoundError(error_summary)
            if any("unsupported" in err.lower() for err in val_result.errors):
                raise UnsupportedAudioFormatError(error_summary)
            raise UnreadableAudioError(error_summary)

        orig_meta = extract_audio_metadata(in_p)
        dest_path = self.resolve_output_path(in_p, output_path=output_path, call_id=call_id)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 2: Idempotency check
        if dest_path.exists():
            if self.config.overwrite_policy == "reuse_existing":
                try:
                    verified_meta = verify_standardized_audio(dest_path, self.config)
                    logger.info("Valid standardized audio already exists at '%s'. Reusing.", dest_path)
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                    return AudioProcessingResult(
                        output_path=str(dest_path),
                        output_format=verified_meta.format.lower(),
                        sample_rate=verified_meta.sample_rate,
                        channels=verified_meta.channels,
                        duration_seconds=verified_meta.duration_seconds,
                        file_size_bytes=verified_meta.file_size_bytes,
                        status="reused",
                        processing_time_ms=elapsed_ms,
                        original_metadata=orig_meta,
                        warnings=val_result.warnings,
                        quality_diagnostics=None,
                    )
                except OutputValidationError:
                    logger.warning("Existing output at '%s' is invalid. Re-processing.", dest_path)
            elif self.config.overwrite_policy == "error":
                raise FileExistsError(f"Target audio file already exists: {dest_path}")

        # Step 3: Safe temporary file handling
        temp_fd, temp_path_str = tempfile.mkstemp(
            prefix=f"proc_{in_p.stem}_",
            suffix=f".{self.config.target_format}",
            dir=str(dest_path.parent),
        )
        os.close(temp_fd)
        temp_path = Path(temp_path_str)

        try:
            # Step 4: Convert, resample, mix to mono, normalize, and diagnose
            diagnostics = process_audio_file(in_p, temp_path, self.config)

            # Step 5: Atomic move to target output path
            if dest_path.exists():
                dest_path.unlink()
            shutil.move(str(temp_path), str(dest_path))

            # Step 6: Mandatory output verification
            verified_meta = verify_standardized_audio(dest_path, self.config)

            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            all_warnings = list(val_result.warnings)
            if diagnostics:
                all_warnings.extend(diagnostics.warnings)

            logger.info(
                "Preprocessing completed in %.2fms: %s -> %s (16kHz mono WAV)",
                elapsed_ms,
                in_p.name,
                dest_path.name,
            )

            return AudioProcessingResult(
                output_path=str(dest_path),
                output_format=verified_meta.format.lower(),
                sample_rate=verified_meta.sample_rate,
                channels=verified_meta.channels,
                duration_seconds=verified_meta.duration_seconds,
                file_size_bytes=verified_meta.file_size_bytes,
                status="success",
                processing_time_ms=elapsed_ms,
                original_metadata=orig_meta,
                warnings=all_warnings,
                quality_diagnostics=diagnostics,
            )

        except Exception as err:
            logger.error("Preprocessing failed for '%s': %s", in_p.name, err)
            raise
        finally:
            # Always ensure temporary file cleanup
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as cleanup_err:
                    logger.warning("Failed to remove temporary file '%s': %s", temp_path, cleanup_err)

    def preprocess_minds14_example(
        self,
        example: dict[str, Any],
        output_dir: str | Path | None = None,
        call_id: str | None = None,
    ) -> AudioProcessingResult:
        """
        Process a MInDS-14 dataset row into standardized 16kHz mono WAV.

        MInDS-14 audio is natively 8000 Hz mono WAV. This bridges Phase 1 dataset
        records directly into the Phase 2 standardized audio pipeline.

        Args:
            example: A dataset row dictionary containing an 'audio' field.
            output_dir: Optional custom output directory.
            call_id: Optional call ID identifier.

        Returns:
            AudioProcessingResult instance.
        """
        audio = example.get("audio")
        if not audio or not isinstance(audio, dict):
            raise UnreadableAudioError("Dataset example does not contain a valid 'audio' dictionary.")

        # If example contains existing file path, process directly
        path_val = audio.get("path")
        if path_val and os.path.exists(path_val):
            return self.preprocess(path_val, call_id=call_id)

        # If example contains in-memory bytes, write to temporary buffer
        audio_bytes = audio.get("bytes")
        if audio_bytes is not None:
            temp_in_fd, temp_in_path_str = tempfile.mkstemp(prefix="minds14_in_", suffix=".wav")
            try:
                with os.fdopen(temp_in_fd, "wb") as f:
                    f.write(audio_bytes)
                cid = call_id or (Path(path_val).stem if path_val else None)
                return self.preprocess(temp_in_path_str, call_id=cid)
            finally:
                if os.path.exists(temp_in_path_str):
                    os.unlink(temp_in_path_str)

        # If example contains pre-decoded array
        array_val = audio.get("array")
        if array_val is not None:
            sr = audio.get("sampling_rate", 8000)
            temp_in_fd, temp_in_path_str = tempfile.mkstemp(prefix="minds14_arr_", suffix=".wav")
            try:
                os.close(temp_in_fd)
                sf.write(temp_in_path_str, np.asarray(array_val, dtype=np.float32), sr, format="WAV")
                cid = call_id or (Path(path_val).stem if path_val else None)
                return self.preprocess(temp_in_path_str, call_id=cid)
            finally:
                if os.path.exists(temp_in_path_str):
                    os.unlink(temp_in_path_str)

        raise UnreadableAudioError("Cannot extract audio stream from dataset example.")
