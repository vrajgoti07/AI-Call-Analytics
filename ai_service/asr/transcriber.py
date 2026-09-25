"""
AI Call Analytics — Whisper Transcriber.

Implements the production speech-to-text service wrapping faster-whisper:
validates Phase 2 standardized audio, executes batched or streaming inference,
extracts word and segment alignments, derives the full transcript, and calculates
real-time factor (RTF) performance metrics.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from ai_service.asr.config import WhisperConfig, DEFAULT_WHISPER_CONFIG
from ai_service.asr.exceptions import (
    AudioNotFoundError,
    InvalidPreprocessedAudioError,
    TranscriptionError,
)
from ai_service.asr.model_manager import WhisperModelManager
from ai_service.asr.schema import (
    TranscriptSegment,
    TranscriptionMetadata,
    TranscriptionResult,
    WordTiming,
)
from ai_service.asr.validator import (
    detect_transcription_anomalies,
    validate_asr_input,
    validate_timestamps,
)

logger = logging.getLogger("ai_call_analytics.asr.transcriber")


class WhisperTranscriber:
    """
    Automatic Speech Recognition (ASR) service powered by faster-whisper.

    Converts standardized 16kHz mono PCM16 WAV audio into structured transcripts
    with segment timestamps, word alignments, confidence telemetry, and language detection.
    """

    def __init__(
        self,
        config: WhisperConfig | None = None,
        model: Any | None = None,
    ) -> None:
        """
        Initialize the transcriber.

        Args:
            config: Optional WhisperConfig instance. Defaults to DEFAULT_WHISPER_CONFIG.
            model: Optional pre-loaded WhisperModel instance for testing or dependency injection.
        """
        self.config = config or DEFAULT_WHISPER_CONFIG
        self._model = model

    def _get_model(self) -> Any:
        """Retrieve model instance (injected or from singleton manager)."""
        if self._model is not None:
            return self._model
        return WhisperModelManager.get_instance().get_model(self.config)

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
        beam_size: int | None = None,
        vad_filter: bool | None = None,
    ) -> TranscriptionResult:
        """
        Transcribe a standardized call recording audio file.

        Steps:
        1. Validate that input audio meets Phase 2 contract (16kHz mono PCM16 WAV).
        2. Resolve language (dynamic auto-detection vs explicit language code).
        3. Execute faster-whisper inference.
        4. Extract segments, word timestamps, and confidence telemetry.
        5. Derive formatted full transcript.
        6. Validate timestamps and audit for hallucination loops.
        7. Calculate performance metrics (RTF) and log execution summary.

        Args:
            audio_path: Path to preprocessed WAV file.
            language: Optional language code override (e.g. 'en'). Defaults to config.
            beam_size: Optional beam size override. Defaults to config.
            vad_filter: Optional VAD filter override. Defaults to config.

        Returns:
            Structured TranscriptionResult.

        Raises:
            AudioNotFoundError: If audio file does not exist.
            InvalidPreprocessedAudioError: If audio fails the Phase 2 contract.
            TranscriptionError: If inference fails during execution.
        """
        path = Path(audio_path).resolve()

        # Step 1: Input contract validation (Step 10)
        audio_duration = validate_asr_input(path)

        # Step 2: Language resolution (Steps 15 & 16)
        target_lang = language or (None if self.config.language == "auto" else self.config.language)
        eff_beam = beam_size or self.config.beam_size
        eff_vad = vad_filter if vad_filter is not None else self.config.vad_filter

        device, compute_type = self.config.resolve_runtime()
        logger.info(
            "Starting ASR for '%s' (duration=%.2fs, lang=%s, model=%s, device=%s)",
            path.name,
            audio_duration,
            target_lang or "auto",
            self.config.model_size,
            device,
        )

        start_time = time.perf_counter()

        try:
            model = self._get_model()
            vad_params = dict(min_silence_duration_ms=self.config.min_vad_silence_ms) if eff_vad else None

            # Step 3: Execute faster-whisper inference
            segments_gen, info = model.transcribe(
                str(path),
                language=target_lang,
                beam_size=eff_beam,
                best_of=self.config.best_of,
                temperature=self.config.temperature,
                vad_filter=eff_vad,
                vad_parameters=vad_params,
                word_timestamps=self.config.word_timestamps,
            )

            # Step 4: Collect segments & word timings
            segments: list[TranscriptSegment] = []
            segment_texts: list[str] = []

            for i, seg in enumerate(segments_gen):
                clean_text = seg.text.strip()
                words: list[WordTiming] = []
                if hasattr(seg, "words") and seg.words:
                    for w in seg.words:
                        words.append(
                            WordTiming(
                                word=w.word.strip(),
                                start=round(w.start, 3),
                                end=round(w.end, 3),
                                probability=round(w.probability, 4),
                            )
                        )

                segment = TranscriptSegment(
                    id=i,
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=clean_text,
                    avg_logprob=getattr(seg, "avg_logprob", None),
                    no_speech_prob=getattr(seg, "no_speech_prob", None),
                    compression_ratio=getattr(seg, "compression_ratio", None),
                    words=words,
                    speaker=None,  # Placeholder for Phase 4 Diarization
                )
                segments.append(segment)
                if clean_text:
                    segment_texts.append(clean_text)

        except (AudioNotFoundError, InvalidPreprocessedAudioError):
            raise
        except Exception as err:
            logger.error("Transcription failed for '%s': %s", path.name, err)
            raise TranscriptionError(f"Whisper inference failed for '{path.name}': {err}") from err

        elapsed = time.perf_counter() - start_time
        rtf = round(elapsed / max(audio_duration, 1e-4), 3)

        # Step 5: Derive combined full transcript (Step 14)
        full_transcript = " ".join(segment_texts)

        # Step 6: Telemetry & diagnostics audits (Steps 19 & 20)
        ts_warnings = validate_timestamps(segments, audio_duration)
        anomaly_warnings = detect_transcription_anomalies(
            full_transcript,
            segments,
            audio_duration,
            repetition_threshold=self.config.repetition_threshold,
            no_speech_threshold=self.config.no_speech_threshold,
        )
        all_warnings = ts_warnings + anomaly_warnings

        detected_lang = getattr(info, "language", target_lang or "unknown")
        detected_lang_prob = getattr(info, "language_probability", 1.0)

        metadata = TranscriptionMetadata(
            model_name=self.config.model_size,
            device=device,
            compute_type=compute_type,
            beam_size=eff_beam,
            vad_filter=eff_vad,
            audio_path=str(path),
        )

        # Step 7: Log telemetry (Step 24 - no full customer transcripts in application logs)
        logger.info(
            "ASR finished for '%s' in %.2fs (RTF=%.3f, lang=%s [prob=%.2f], segments=%d, warnings=%d)",
            path.name,
            elapsed,
            rtf,
            detected_lang,
            detected_lang_prob,
            len(segments),
            len(all_warnings),
        )

        return TranscriptionResult(
            text=full_transcript,
            language=detected_lang,
            language_probability=round(detected_lang_prob, 4),
            duration_seconds=audio_duration,
            processing_time_seconds=round(elapsed, 3),
            real_time_factor=rtf,
            segments=segments,
            warnings=all_warnings,
            metadata=metadata,
        )
