"""
AI Call Analytics — ASR Evaluator.

Evaluates Whisper/faster-whisper ASR against reference transcripts.
Computes Word Error Rate (WER), Character Error Rate (CER), error taxonomy
(substitutions, deletions, insertions), processing latency, and Real-Time Factor (RTF).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from ai_service.asr.config import WhisperConfig
from ai_service.asr.transcriber import WhisperTranscriber
from ai_service.evaluation.config import EvaluationConfig
from ai_service.evaluation.metrics import calculate_cer, calculate_wer
from ai_service.evaluation.normalizer import TextNormalizer
from ai_service.evaluation.reports import ComponentEvaluationResult

logger = logging.getLogger(__name__)


class ASREvaluator:
    """
    Evaluates Speech-to-Text accuracy and operational performance against reference transcripts.
    """

    def __init__(
        self,
        config: EvaluationConfig | None = None,
        asr_config: WhisperConfig | None = None,
    ) -> None:
        self.config = config or EvaluationConfig()
        self.asr_config = asr_config or WhisperConfig(model_size="base")

    def evaluate_samples(
        self,
        samples: list[dict[str, Any]],
    ) -> ComponentEvaluationResult:
        """
        Evaluate ASR performance on a provided list of audio/reference transcript samples.

        Each sample must contain:
            - 'audio_path' or 'audio_array'
            - 'reference_text': Ground truth transcription
            - 'duration': Optional audio duration in seconds
        """
        if not samples:
            return ComponentEvaluationResult(
                component="asr",
                evaluation_type="quantitative",
                status="WARNING",
                metrics={"wer": None, "cer": None, "rtf": None},
                sample_count=0,
                model_name=f"faster-whisper-{self.asr_config.model_size}",
                summary="No audio samples provided for ASR evaluation.",
            )

        logger.info(
            "Evaluating ASR on %d samples using model size '%s'",
            len(samples),
            self.asr_config.model_size,
        )

        wers: list[float] = []
        cers: list[float] = []
        total_subs = 0
        total_dels = 0
        total_inss = 0
        total_ref_words = 0

        total_audio_duration = 0.0
        total_processing_time = 0.0

        transcriber = WhisperTranscriber(self.asr_config)

        for s in samples:
            ref_raw = s.get("reference_text", "")
            audio = s.get("audio_path") or s.get("audio_array")
            expected_dur = float(s.get("duration", 0.0) or 0.0)

            t_start = time.perf_counter()
            try:
                result = transcriber.transcribe(audio)
                proc_time = time.perf_counter() - t_start
                hyp_raw = result.text
                aud_dur = result.audio_duration or expected_dur
            except Exception as exc:
                logger.warning("Transcription error on sample: %s", exc)
                continue

            total_audio_duration += aud_dur
            total_processing_time += proc_time

            # Standardized Normalization
            ref_norm = TextNormalizer.normalize(ref_raw)
            hyp_norm = TextNormalizer.normalize(hyp_raw)

            wer, subs, dels, inss, n_words = calculate_wer(ref_norm, hyp_norm)
            cer = calculate_cer(ref_norm, hyp_norm)

            wers.append(wer)
            cers.append(cer)
            total_subs += subs
            total_dels += dels
            total_inss += inss
            total_ref_words += n_words

        if not wers:
            return ComponentEvaluationResult(
                component="asr",
                evaluation_type="quantitative",
                status="FAILED",
                metrics={},
                sample_count=0,
                model_name=f"faster-whisper-{self.asr_config.model_size}",
                summary="Failed to transcribe any of the provided samples.",
            )

        overall_wer = round(
            float((total_subs + total_dels + total_inss) / total_ref_words)
            if total_ref_words > 0
            else 0.0,
            4,
        )
        mean_cer = round(float(np.mean(cers)), 4)
        median_wer = round(float(np.median(wers)), 4)
        p90_wer = round(float(np.percentile(wers, 90)), 4)

        rtf = round(
            float(total_processing_time / total_audio_duration)
            if total_audio_duration > 0
            else 0.0,
            4,
        )

        metrics = {
            "wer": overall_wer,
            "cer": mean_cer,
            "median_wer": median_wer,
            "p90_wer": p90_wer,
            "substitutions": total_subs,
            "deletions": total_dels,
            "insertions": total_inss,
            "total_ref_words": total_ref_words,
            "total_audio_duration_seconds": round(total_audio_duration, 2),
            "total_processing_time_seconds": round(total_processing_time, 2),
            "real_time_factor": rtf,
            "normalization_policy": TextNormalizer.POLICY_DESCRIPTION,
        }

        status = "PASSED" if overall_wer < 0.35 else "WARNING"
        summary = (
            f"Evaluated {len(wers)} samples. WER={overall_wer:.2%}, CER={mean_cer:.2%}, "
            f"Median WER={median_wer:.2%}, RTF={rtf:.3f}x on CPU."
        )

        return ComponentEvaluationResult(
            component="asr",
            evaluation_type="quantitative",
            status=status,
            metrics=metrics,
            sample_count=len(wers),
            model_name=f"faster-whisper-{self.asr_config.model_size}",
            model_version=self.asr_config.compute_type,
            summary=summary,
            details={
                "error_breakdown": {
                    "substitutions": total_subs,
                    "deletions": total_dels,
                    "insertions": total_inss,
                }
            },
        )
