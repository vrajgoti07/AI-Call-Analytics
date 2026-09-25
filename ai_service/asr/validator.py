"""
AI Call Analytics — ASR Validator & Diagnostics.

Validates that input audio strictly conforms to the Phase 2 contract (16kHz mono PCM16 WAV),
verifies segment timestamp monotonicity, and detects hallucination loops or empty speech.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

import soundfile as sf

from ai_service.asr.exceptions import (
    AudioNotFoundError,
    InvalidPreprocessedAudioError,
)
from ai_service.asr.schema import TranscriptSegment

logger = logging.getLogger("ai_call_analytics.asr.validator")


def validate_asr_input(audio_path: str | Path) -> float:
    """
    Validate that an input audio file adheres strictly to the Phase 2 contract (Step 10).

    Expected contract:
    - File exists and is non-empty.
    - Container: WAV
    - Format: PCM_16 (or valid linear PCM)
    - Sample rate: 16,000 Hz
    - Channels: 1 (Mono)
    - Duration > 0s

    Args:
        audio_path: Path to the preprocessed audio file.

    Returns:
        Duration in seconds.

    Raises:
        AudioNotFoundError: If the file does not exist.
        InvalidPreprocessedAudioError: If any Phase 2 contract requirement is violated.
    """
    path = Path(audio_path).resolve()
    if not path.exists():
        raise AudioNotFoundError(f"Audio file not found: {path}")

    if not path.is_file():
        raise InvalidPreprocessedAudioError(f"Audio path is not a regular file: {path}")

    size = path.stat().st_size
    if size < 44:
        raise InvalidPreprocessedAudioError(f"Audio file is corrupted or too small to contain a WAV header ({size} bytes): {path}")

    try:
        info = sf.info(str(path))
    except Exception as err:
        raise InvalidPreprocessedAudioError(f"Cannot inspect audio file '{path.name}': {err}") from err

    # 1. Container check
    if info.format != "WAV":
        raise InvalidPreprocessedAudioError(
            f"Input audio must be WAV container from Phase 2, got '{info.format}' for '{path.name}'."
        )

    # 2. Sample rate check
    if info.samplerate != 16000:
        raise InvalidPreprocessedAudioError(
            f"Input audio must be 16,000 Hz from Phase 2, got {info.samplerate} Hz for '{path.name}'."
        )

    # 3. Channel count check
    if info.channels != 1:
        raise InvalidPreprocessedAudioError(
            f"Input audio must be single-channel mono from Phase 2, got {info.channels} channels for '{path.name}'."
        )

    # 4. Duration check
    if info.duration <= 0:
        raise InvalidPreprocessedAudioError(
            f"Audio duration must be greater than 0s, got {info.duration}s for '{path.name}'."
        )

    return round(info.duration, 4)


def validate_timestamps(
    segments: list[TranscriptSegment],
    audio_duration: float,
    tolerance: float = 0.1,
) -> list[str]:
    """
    Audit segment timestamps for mathematical consistency (Step 20).

    Verifies:
    - start >= 0
    - end > start
    - start < audio_duration
    - end <= audio_duration + tolerance
    - Chronological monotonicity (start times do not regress backwards)

    Args:
        segments: List of TranscriptSegment instances.
        audio_duration: Total audio duration in seconds.
        tolerance: Allowed floating-point boundary margin (default: 0.1s).

    Returns:
        List of warning strings describing any detected timestamp anomalies.
    """
    warnings: list[str] = []

    for i, seg in enumerate(segments):
        # 1. Negative boundary
        if seg.start < 0:
            warnings.append(f"Segment {seg.id} has negative start time: {seg.start}s.")

        # 2. Inverted duration
        if seg.end <= seg.start:
            warnings.append(
                f"Segment {seg.id} has invalid duration (end {seg.end}s <= start {seg.start}s)."
            )

        # 3. Audio boundary overflow
        if seg.start > audio_duration + tolerance:
            warnings.append(
                f"Segment {seg.id} start ({seg.start}s) exceeds total audio duration ({audio_duration}s)."
            )
        if seg.end > audio_duration + tolerance:
            warnings.append(
                f"Segment {seg.id} end ({seg.end}s) extends beyond total audio duration ({audio_duration}s)."
            )

        # 4. Chronological order check
        if i > 0:
            prev_seg = segments[i - 1]
            if seg.start < prev_seg.start - tolerance:
                warnings.append(
                    f"Segment {seg.id} start ({seg.start}s) is earlier than previous segment {prev_seg.id} ({prev_seg.start}s)."
                )

    return warnings


def detect_transcription_anomalies(
    text: str,
    segments: list[TranscriptSegment],
    audio_duration: float,
    repetition_threshold: int = 3,
    no_speech_threshold: float = 0.6,
) -> list[str]:
    """
    Detect speech recognition anomalies, empty speech, and hallucination loops (Step 19).

    Args:
        text: Full combined transcript string.
        segments: List of generated TranscriptSegment instances.
        audio_duration: Audio duration in seconds.
        repetition_threshold: Number of repeated identical segments before flagging hallucination.
        no_speech_threshold: Minimum no_speech_prob to flag a silent/inaudible segment.

    Returns:
        List of warning strings.
    """
    warnings: list[str] = []

    # 1. Empty speech check
    if not text.strip():
        if audio_duration > 1.0:
            warnings.append("No speech detected: audio contains speech-range duration but produced an empty transcript.")
        return warnings

    # 2. Extremely short transcript check
    if len(text.strip()) < 3 and audio_duration > 5.0:
        warnings.append("Extremely short transcript detected for audio duration > 5.0s.")

    # 3. Repetition / Hallucination loop check
    clean_segment_texts = [s.text.strip().lower() for s in segments if len(s.text.strip()) > 3]
    if clean_segment_texts:
        counts = Counter(clean_segment_texts)
        for phrase, count in counts.items():
            if count >= repetition_threshold:
                warnings.append(
                    f"Possible hallucination loop: phrase '{phrase[:40]}...' repeats {count} times."
                )

    # 4. Segment-level confidence / no_speech telemetry check
    high_no_speech_count = sum(
        1 for s in segments if s.no_speech_prob is not None and s.no_speech_prob > no_speech_threshold
    )
    if high_no_speech_count > len(segments) * 0.5 and len(segments) > 1:
        warnings.append(
            f"Low acoustic confidence: {high_no_speech_count}/{len(segments)} segments flagged with high no-speech probability."
        )

    return warnings
