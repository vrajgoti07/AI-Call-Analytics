"""
AI Call Analytics — Whisper & Diarization Temporal Alignment.

Fuses Phase 3 Whisper ASR transcription segments with Phase 4 acoustic
diarization segments using temporal overlap calculation, cross-speaker
splitting, and conversational speaker-turn aggregation.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import asdict
from typing import Any

from ai_service.asr.schema import TranscriptSegment, TranscriptionResult
from ai_service.diarization.config import DiarizationConfig, DEFAULT_DIARIZATION_CONFIG
from ai_service.diarization.exceptions import AlignmentError
from ai_service.diarization.schema import (
    DiarizationResult,
    DiarizationSegment,
    SpeakerAttributedTranscript,
    SpeakerStats,
    SpeakerTurn,
)

logger = logging.getLogger("ai_call_analytics.diarization.aligner")


class TranscriptAligner:
    """
    Temporal alignment service connecting Whisper ASR transcripts and pyannote diarization.

    Assigns speaker identities to ASR segments, resolves cross-speaker segments,
    consolidates sequential speaker turns, and generates the final conversational transcript.
    """

    def __init__(self, config: DiarizationConfig | None = None) -> None:
        """
        Initialize the aligner.

        Args:
            config: Optional DiarizationConfig. Defaults to DEFAULT_DIARIZATION_CONFIG.
        """
        self.config = config or DEFAULT_DIARIZATION_CONFIG

    def align(
        self,
        transcription: TranscriptionResult,
        diarization: DiarizationResult,
    ) -> SpeakerAttributedTranscript:
        """
        Align Whisper transcription segments with acoustic diarization segments.

        Args:
            transcription: Phase 3 Whisper transcription result.
            diarization: Phase 4 pyannote diarization result.

        Returns:
            SpeakerAttributedTranscript containing structured speaker turns and dialogue.

        Raises:
            AlignmentError: If alignment fails due to malformed input data.
        """
        start_time = time.perf_counter()
        logger.info(
            "Starting alignment: %d ASR segments, %d diarization segments",
            len(transcription.segments),
            len(diarization.speaker_segments),
        )

        warnings: list[str] = list(diarization.warnings)
        aligned_segments: list[TranscriptSegment] = []

        # Step 1: Align each Whisper segment with diarization segments (Steps 14, 15, 16)
        for seg in transcription.segments:
            assigned_parts, seg_warnings = self._align_single_whisper_segment(
                seg,
                diarization.speaker_segments,
            )
            aligned_segments.extend(assigned_parts)
            warnings.extend(seg_warnings)

        # Step 2: Consolidate aligned segments into conversational Speaker Turns (Steps 18, 19, 22)
        turns = self._aggregate_into_turns(aligned_segments)

        # Step 3: Generate human-readable multi-line dialogue (Step 20)
        formatted_dialogue = self._format_conversation_text(turns)

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Alignment completed in %.3fs: generated %d speaker turns from %d segments",
            elapsed,
            len(turns),
            len(aligned_segments),
        )

        return SpeakerAttributedTranscript(
            full_text=formatted_dialogue,
            turns=turns,
            speakers=diarization.speakers,
            speaker_stats=diarization.speaker_stats,
            total_turns=len(turns),
            audio_duration=transcription.duration_seconds,
            speech_duration=diarization.speech_duration,
            overlap_duration=diarization.overlap_duration,
            overlap_detected=diarization.overlap_detected,
            alignment_time_seconds=round(elapsed, 4),
            warnings=warnings,
            transcription_metadata=transcription.metadata.to_dict() if transcription.metadata else {},
            diarization_metadata=diarization.metadata.to_dict() if diarization.metadata else {},
        )

    def _align_single_whisper_segment(
        self,
        whisper_seg: TranscriptSegment,
        diar_segments: list[DiarizationSegment],
    ) -> tuple[list[TranscriptSegment], list[str]]:
        """
        Align a single Whisper segment against diarization boundaries.
        Supports word-level splitting or dominant-overlap assignment.
        """
        warnings: list[str] = []
        w_start = whisper_seg.start
        w_end = whisper_seg.end
        w_duration = max(1e-4, w_end - w_start)

        # Compute temporal overlap with all diarization segments
        speaker_overlap_durations: dict[str, float] = defaultdict(float)

        for d_seg in diar_segments:
            overlap_start = max(w_start, d_seg.start)
            overlap_end = min(w_end, d_seg.end)
            if overlap_end > overlap_start:
                speaker_overlap_durations[d_seg.speaker] += (overlap_end - overlap_start)

        # Case 1: No direct overlap -> search within collar tolerance
        if not speaker_overlap_durations:
            nearest_spk = self._find_nearest_speaker(whisper_seg, diar_segments, self.config.collar)
            if nearest_spk:
                whisper_seg.speaker = nearest_spk
                return [whisper_seg], []
            else:
                whisper_seg.speaker = "UNKNOWN"
                warnings.append(
                    f"ASR segment {whisper_seg.id} [{w_start:.2f}-{w_end:.2f}s] had no overlapping "
                    "speaker activity. Assigned to 'UNKNOWN'."
                )
                return [whisper_seg], warnings

        # Case 2: Direct overlap found
        # Check if multiple speakers overlap significantly (Cross-speaker segment - Step 16)
        sorted_overlaps = sorted(
            speaker_overlap_durations.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        dominant_speaker, dominant_dur = sorted_overlaps[0]
        dominant_ratio = dominant_dur / w_duration

        # If word-level policy enabled and multiple distinct speakers overlap
        if (
            self.config.cross_speaker_policy == "word_level"
            and len(sorted_overlaps) > 1
            and hasattr(whisper_seg, "words")
            and len(whisper_seg.words) >= 2
        ):
            split_segs, split_warns = self._split_segment_by_words(whisper_seg, diar_segments)
            if split_segs:
                return split_segs, split_warns

        # Dominant speaker policy (Step 16)
        whisper_seg.speaker = dominant_speaker

        if len(sorted_overlaps) > 1:
            secondary_speaker, secondary_dur = sorted_overlaps[1]
            sec_ratio = secondary_dur / w_duration
            if sec_ratio >= 0.20:
                warnings.append(
                    f"Cross-speaker segment: ASR segment {whisper_seg.id} [{w_start:.2f}-{w_end:.2f}s] "
                    f"crosses {dominant_speaker} ({dominant_ratio:.1%}) and {secondary_speaker} ({sec_ratio:.1%}). "
                    f"Assigned to dominant speaker '{dominant_speaker}'."
                )

        return [whisper_seg], warnings

    def _split_segment_by_words(
        self,
        whisper_seg: TranscriptSegment,
        diar_segments: list[DiarizationSegment],
    ) -> tuple[list[TranscriptSegment], list[str]]:
        """
        Split a cross-speaker Whisper segment across word boundaries based on word timestamps.
        Preserves original text with zero modification (Step 17).
        """
        if not whisper_seg.words:
            return [], []

        # Assign speaker to each word
        word_speaker_map: list[tuple[Any, str]] = []
        for word in whisper_seg.words:
            w_start, w_end = word.start, word.end
            best_spk = "UNKNOWN"
            best_overlap = 0.0

            for d_seg in diar_segments:
                ov_start = max(w_start, d_seg.start)
                ov_end = min(w_end, d_seg.end)
                if ov_end > ov_start:
                    ov = ov_end - ov_start
                    if ov > best_overlap:
                        best_overlap = ov
                        best_spk = d_seg.speaker

            if best_spk == "UNKNOWN":
                best_spk = self._find_nearest_speaker(word, diar_segments, self.config.collar) or "UNKNOWN"

            word_speaker_map.append((word, best_spk))

        # Group consecutive words by same speaker
        sub_segments: list[TranscriptSegment] = []
        current_words: list[Any] = []
        current_spk = word_speaker_map[0][1]

        for word, spk in word_speaker_map:
            if spk == current_spk:
                current_words.append(word)
            else:
                if current_words:
                    sub_text = " ".join(w.word for w in current_words)
                    sub_segments.append(
                        TranscriptSegment(
                            id=whisper_seg.id,
                            start=current_words[0].start,
                            end=current_words[-1].end,
                            text=sub_text,
                            words=list(current_words),
                            speaker=current_spk,
                        )
                    )
                current_words = [word]
                current_spk = spk

        if current_words:
            sub_text = " ".join(w.word for w in current_words)
            sub_segments.append(
                TranscriptSegment(
                    id=whisper_seg.id,
                    start=current_words[0].start,
                    end=current_words[-1].end,
                    text=sub_text,
                    words=list(current_words),
                    speaker=current_spk,
                )
            )

        warnings = [
            f"Split ASR segment {whisper_seg.id} into {len(sub_segments)} speaker-aligned portions using word timestamps."
        ]
        return sub_segments, warnings

    def _find_nearest_speaker(
        self,
        item: Any,
        diar_segments: list[DiarizationSegment],
        collar: float,
    ) -> str | None:
        """Find the nearest speaker within the temporal collar tolerance."""
        s = getattr(item, "start", 0.0)
        e = getattr(item, "end", 0.0)
        closest_spk = None
        min_dist = collar

        for d_seg in diar_segments:
            # Distance from item start/end to d_seg start/end
            if s >= d_seg.end:
                dist = s - d_seg.end
            elif e <= d_seg.start:
                dist = d_seg.start - e
            else:
                dist = 0.0

            if dist < min_dist:
                min_dist = dist
                closest_spk = d_seg.speaker

        return closest_spk

    def _aggregate_into_turns(
        self,
        segments: list[TranscriptSegment],
    ) -> list[SpeakerTurn]:
        """
        Consolidate sequential segments from the same speaker into coherent turns (Step 13 & 18).
        Ensures non-speech/silence is omitted (Step 22).
        """
        # Filter out empty or whitespace-only segments
        speech_segments = [s for s in segments if s.text and s.text.strip()]
        if not speech_segments:
            return []

        turns: list[SpeakerTurn] = []
        current_spk = speech_segments[0].speaker or "UNKNOWN"
        current_texts: list[str] = [speech_segments[0].text.strip()]
        current_ids: list[int] = [speech_segments[0].id]
        current_start: float = speech_segments[0].start
        current_end: float = speech_segments[0].end
        current_words: list[dict[str, Any]] = [
            w.to_dict() if hasattr(w, "to_dict") else asdict(w)
            for w in getattr(speech_segments[0], "words", [])
        ]

        turn_index = 1

        for seg in speech_segments[1:]:
            spk = seg.speaker or "UNKNOWN"
            if spk == current_spk:
                current_texts.append(seg.text.strip())
                current_ids.append(seg.id)
                current_end = max(current_end, seg.end)
                for w in getattr(seg, "words", []):
                    current_words.append(w.to_dict() if hasattr(w, "to_dict") else asdict(w))
            else:
                # Flush current turn
                turns.append(
                    SpeakerTurn(
                        turn_id=turn_index,
                        speaker=current_spk,
                        start=round(current_start, 3),
                        end=round(current_end, 3),
                        text=" ".join(current_texts),
                        source_segment_ids=list(current_ids),
                        words=current_words,
                    )
                )
                turn_index += 1

                # Start new turn
                current_spk = spk
                current_texts = [seg.text.strip()]
                current_ids = [seg.id]
                current_start = seg.start
                current_end = seg.end
                current_words = [
                    w.to_dict() if hasattr(w, "to_dict") else asdict(w)
                    for w in getattr(seg, "words", [])
                ]

        # Flush final turn
        if current_texts:
            turns.append(
                SpeakerTurn(
                    turn_id=turn_index,
                    speaker=current_spk,
                    start=round(current_start, 3),
                    end=round(current_end, 3),
                    text=" ".join(current_texts),
                    source_segment_ids=list(current_ids),
                    words=current_words,
                )
            )

        return turns

    def _format_conversation_text(self, turns: list[SpeakerTurn]) -> str:
        """Format speaker turns into human-readable dialogue representation (Step 20)."""
        lines: list[str] = []
        for turn in turns:
            lines.append(f"{turn.speaker}: {turn.text}")
        return "\n\n".join(lines)
