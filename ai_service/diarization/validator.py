"""
AI Call Analytics — Diarization Validator & Statistics.

Validates that audio adheres to the Phase 2 standardization contract,
verifies temporal consistency of speaker segments, computes multi-speaker
overlaps, and generates conversational statistics.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

import soundfile as sf

from ai_service.diarization.exceptions import (
    InvalidDiarizationOutputError,
    InvalidPreprocessedAudioError,
)
from ai_service.diarization.schema import DiarizationSegment, SpeakerStats

logger = logging.getLogger("ai_call_analytics.diarization.validator")


def validate_diarization_audio(audio_path: str | Path) -> float:
    """
    Validate that an input audio file adheres strictly to the Phase 2 contract (Step 5).

    Expected contract:
    - Container: WAV
    - Sample rate: 16,000 Hz
    - Channels: 1 (Mono)
    - Duration > 0s

    Args:
        audio_path: Path to the preprocessed audio file.

    Returns:
        Duration in seconds.

    Raises:
        FileNotFoundError: If the file does not exist.
        InvalidPreprocessedAudioError: If any Phase 2 contract requirement is violated.
    """
    path = Path(audio_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    if not path.is_file():
        raise InvalidPreprocessedAudioError(f"Audio path is not a regular file: {path}")

    size = path.stat().st_size
    if size < 44:
        raise InvalidPreprocessedAudioError(
            f"Audio file is corrupted or too small to contain a WAV header ({size} bytes): {path}"
        )

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


def validate_diarization_segments(
    segments: list[DiarizationSegment],
    audio_duration: float,
    tolerance: float = 0.25,
) -> list[str]:
    """
    Audit diarization segments for temporal consistency (Step 11).

    Verifies:
    - segment.start >= 0
    - segment.end > segment.start
    - duration > 0
    - speaker identifier is non-empty
    - start / end do not drastically overshoot audio_duration

    Returns:
        List of warning messages describing detected inconsistencies.
    """
    warnings: list[str] = []

    for i, seg in enumerate(segments):
        if not seg.speaker or not seg.speaker.strip():
            warnings.append(f"Segment {i} [{seg.start:.2f}-{seg.end:.2f}s] has empty speaker label.")

        if seg.start < 0:
            warnings.append(f"Segment {i} ({seg.speaker}) has negative start time: {seg.start}s.")

        if seg.end <= seg.start:
            warnings.append(
                f"Segment {i} ({seg.speaker}) has invalid duration (end {seg.end}s <= start {seg.start}s)."
            )

        if seg.start > audio_duration + tolerance:
            warnings.append(
                f"Segment {i} ({seg.speaker}) start ({seg.start:.2f}s) exceeds audio duration ({audio_duration:.2f}s)."
            )

        if seg.end > audio_duration + tolerance:
            warnings.append(
                f"Segment {i} ({seg.speaker}) end ({seg.end:.2f}s) exceeds audio duration ({audio_duration:.2f}s)."
            )

    return warnings


def compute_overlap_duration(segments: list[DiarizationSegment]) -> float:
    """
    Calculate the total non-double-counted duration where multiple distinct speakers talk simultaneously (Step 21).

    Returns:
        Total overlap duration in seconds.
    """
    if len(segments) < 2:
        return 0.0

    raw_overlaps: list[tuple[float, float]] = []

    # Find all intersections between distinct speakers
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            seg_a = segments[i]
            seg_b = segments[j]

            if seg_a.speaker == seg_b.speaker:
                continue

            start_overlap = max(seg_a.start, seg_b.start)
            end_overlap = min(seg_a.end, seg_b.end)

            if end_overlap > start_overlap:
                raw_overlaps.append((start_overlap, end_overlap))

    if not raw_overlaps:
        return 0.0

    # Merge overlapping intervals to prevent double-counting multi-speaker cross-talk
    raw_overlaps.sort(key=lambda iv: iv[0])
    merged: list[tuple[float, float]] = [raw_overlaps[0]]

    for current in raw_overlaps[1:]:
        prev_s, prev_e = merged[-1]
        cur_s, cur_e = current
        if cur_s <= prev_e:
            merged[-1] = (prev_s, max(prev_e, cur_e))
        else:
            merged.append(current)

    total_overlap = sum(e - s for s, e in merged)
    return round(total_overlap, 3)


def calculate_speaker_stats(
    segments: list[DiarizationSegment],
    audio_duration: float,
) -> tuple[list[str], dict[str, SpeakerStats], float]:
    """
    Calculate per-speaker conversational statistics (Step 12).

    Aggregates:
    - total speaking duration per speaker
    - segment count per speaker
    - percentage of total conversational speech

    Returns:
        Tuple of (sorted_speaker_list, speaker_stats_dict, total_speech_time).
    """
    if not segments:
        return [], {}, 0.0

    speaker_times: dict[str, float] = defaultdict(float)
    speaker_counts: dict[str, int] = defaultdict(int)

    for seg in segments:
        speaker_times[seg.speaker] += seg.duration
        speaker_counts[seg.speaker] += 1

    total_speech_time = sum(speaker_times.values())
    sorted_speakers = sorted(speaker_times.keys())

    stats: dict[str, SpeakerStats] = {}
    for spk in sorted_speakers:
        spk_time = speaker_times[spk]
        spk_count = speaker_counts[spk]
        percentage = (spk_time / total_speech_time * 100.0) if total_speech_time > 0 else 0.0

        stats[spk] = SpeakerStats(
            speaker=spk,
            total_speaking_time=round(spk_time, 3),
            segment_count=spk_count,
            speech_percentage=round(percentage, 2),
        )

    return sorted_speakers, stats, round(total_speech_time, 3)
