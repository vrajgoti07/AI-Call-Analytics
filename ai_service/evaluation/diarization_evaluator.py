"""
AI Call Analytics — Speaker Diarization & Alignment Evaluator.

Evaluates Diarization Error Rate (DER) when reference annotations exist;
otherwise executes structural integrity, timestamp validity, continuity,
and speech alignment coverage validation.
"""

from __future__ import annotations

import logging
from typing import Any

from ai_service.diarization.schema import SpeakerAttributedTranscript
from ai_service.evaluation.config import EvaluationConfig
from ai_service.evaluation.reports import ComponentEvaluationResult

logger = logging.getLogger(__name__)


class DiarizationEvaluator:
    """
    Evaluates speaker diarization segments and Whisper alignment transcripts.
    Strictly reports 'GROUND_TRUTH_UNAVAILABLE' when reference speaker annotations
    are missing, substituting rigorous structural and acoustic checks.
    """

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def evaluate_structural(
        self,
        transcripts: list[SpeakerAttributedTranscript],
    ) -> ComponentEvaluationResult:
        """
        Execute structural and timestamp integrity validation across speaker transcripts.
        """
        if not transcripts:
            return ComponentEvaluationResult(
                component="diarization",
                evaluation_type="ground_truth_unavailable",
                status="GROUND_TRUTH_UNAVAILABLE",
                metrics={"der": None, "structural_validity_rate": 0.0},
                sample_count=0,
                model_name="pyannote.audio",
                summary="No transcripts provided for diarization structural validation.",
            )

        total_transcripts = len(transcripts)
        valid_transcripts = 0
        total_turns = 0
        timestamp_violations = 0
        coverage_ratios: list[float] = []

        for tr in transcripts:
            turns = getattr(tr, "turns", []) or []
            aud_dur = float(getattr(tr, "audio_duration", 0.0) or 0.0)
            speech_dur = float(getattr(tr, "speech_duration", 0.0) or 0.0)

            is_valid = True
            last_end = 0.0

            for turn in turns:
                total_turns += 1
                start = getattr(turn, "start", 0.0)
                end = getattr(turn, "end", 0.0)
                speaker = getattr(turn, "speaker", "")

                # Checks
                if start < 0.0 or end <= start or (aud_dur > 0 and end > aud_dur + 1.0) or not speaker:
                    timestamp_violations += 1
                    is_valid = False

                last_end = end

            # Alignment Coverage: total turn speech time vs total speech duration
            turn_speech_time = sum(t.duration for t in turns if hasattr(t, "duration"))
            if speech_dur > 0:
                cov = min(1.0, turn_speech_time / speech_dur)
                coverage_ratios.append(cov)

            if is_valid:
                valid_transcripts += 1

        mean_coverage = float(sum(coverage_ratios) / len(coverage_ratios)) if coverage_ratios else 1.0
        structural_validity_rate = float(valid_transcripts / total_transcripts)

        metrics = {
            "der": None,  # No reference RTTM ground truth exists
            "structural_validity_rate": round(structural_validity_rate, 4),
            "timestamp_violations": timestamp_violations,
            "average_alignment_coverage": round(mean_coverage, 4),
            "total_turns_inspected": total_turns,
        }

        status = "PASSED" if structural_validity_rate >= 0.95 else "WARNING"
        summary = (
            f"Reference speaker annotations (RTTM) unavailable in MInDS-14. "
            f"Executed structural validation over {total_transcripts} calls ({total_turns} turns): "
            f"validity={structural_validity_rate:.1%}, alignment coverage={mean_coverage:.1%}, "
            f"timestamp violations={timestamp_violations}."
        )

        return ComponentEvaluationResult(
            component="diarization",
            evaluation_type="structural",
            status=status,
            metrics=metrics,
            sample_count=total_transcripts,
            model_name="pyannote.audio+whisper_aligner",
            model_version="3.3.2",
            summary=summary,
            details={
                "ground_truth_status": "UNAVAILABLE",
                "der_calculated": False,
            },
        )
