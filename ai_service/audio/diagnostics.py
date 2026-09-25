"""
AI Call Analytics — Audio Quality Diagnostics.

Calculates signal diagnostics including peak dBFS, RMS power, clipping ratios,
and silence percentages to flag conversational audio anomalies without corrupting data.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ai_service.audio.config import AudioConfig, DEFAULT_AUDIO_CONFIG
from ai_service.audio.schema import AudioQualityDiagnostics

logger = logging.getLogger("ai_call_analytics.audio.diagnostics")


def analyze_audio_quality(
    audio_data: np.ndarray,
    sample_rate: int,
    config: AudioConfig | None = None,
) -> AudioQualityDiagnostics:
    """
    Perform speech-oriented quality checks on decoded floating-point audio data.

    Calculates:
    - Peak amplitude and peak dBFS (dB relative to full scale)
    - Root-Mean-Square (RMS) amplitude and RMS dBFS
    - Silence ratio (samples below silence threshold)
    - Clipping ratio (samples at or above digital ceiling)
    - Descriptive operational warnings

    Args:
        audio_data: 1D or 2D numpy array of audio samples (-1.0 to 1.0).
        sample_rate: Sampling frequency in Hz.
        config: Optional AudioConfig with threshold specifications.

    Returns:
        AudioQualityDiagnostics instance.
    """
    cfg = config or DEFAULT_AUDIO_CONFIG
    warnings: list[str] = []

    if audio_data.size == 0:
        return AudioQualityDiagnostics(
            is_silent=True,
            silence_percentage=100.0,
            is_clipped=False,
            clipping_percentage=0.0,
            peak_amplitude=0.0,
            peak_dbfs=-120.0,
            rms_amplitude=0.0,
            rms_dbfs=-120.0,
            warnings=["Audio buffer is empty."],
        )

    # Flatten multi-channel arrays for signal analysis
    samples = audio_data.flatten()
    abs_samples = np.abs(samples)

    # 1. Peak & RMS measurements
    peak = float(np.max(abs_samples))
    peak_dbfs = round(float(20.0 * np.log10(max(peak, 1e-9))), 2)

    rms = float(np.sqrt(np.mean(samples ** 2)))
    rms_dbfs = round(float(20.0 * np.log10(max(rms, 1e-9))), 2)

    # 2. Silence detection
    # Linear amplitude corresponding to silence threshold (e.g. -40 dBFS = 0.01)
    silence_amp_thresh = 10.0 ** (cfg.silence_threshold_db / 20.0)
    silent_count = int(np.sum(abs_samples < silence_amp_thresh))
    silence_ratio = silent_count / samples.size
    silence_pct = round(silence_ratio * 100.0, 2)
    is_silent = silence_ratio >= cfg.silence_warning_ratio

    if is_silent:
        warnings.append(
            f"Excessive silence detected: {silence_pct}% of audio is below {cfg.silence_threshold_db} dBFS."
        )

    # 3. Clipping detection
    clipped_count = int(np.sum(abs_samples >= cfg.clipping_threshold))
    clipping_ratio = clipped_count / samples.size
    clipping_pct = round(clipping_ratio * 100.0, 3)
    is_clipped = clipping_ratio >= cfg.clipping_warning_ratio

    if is_clipped:
        warnings.append(
            f"Potential audio clipping detected: {clipping_pct}% of samples exceed ceiling {cfg.clipping_threshold}."
        )

    # 4. Low amplitude / Inaudible signal check
    if peak_dbfs < -45.0 and not is_silent:
        warnings.append(
            f"Unusually low audio amplitude (peak: {peak_dbfs} dBFS, RMS: {rms_dbfs} dBFS). "
            f"Audio may be faint or inaudible."
        )

    return AudioQualityDiagnostics(
        is_silent=is_silent,
        silence_percentage=silence_pct,
        is_clipped=is_clipped,
        clipping_percentage=clipping_pct,
        peak_amplitude=round(peak, 5),
        peak_dbfs=peak_dbfs,
        rms_amplitude=round(rms, 5),
        rms_dbfs=rms_dbfs,
        warnings=warnings,
    )
