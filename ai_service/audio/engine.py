"""
AI Call Analytics — Audio Conversion & Processing Engine.

Implements high-fidelity audio conversion to standardized 16kHz mono PCM16 WAV.
Supports dual processing pipelines:
1. Subprocess-based FFmpeg engine (for production / Docker with broad container support).
2. Pure Python native engine via soundfile + scipy.signal (resampling, mono-mixing, normalization).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import scipy.signal
import soundfile as sf

from ai_service.audio.config import AudioConfig, DEFAULT_AUDIO_CONFIG
from ai_service.audio.diagnostics import analyze_audio_quality
from ai_service.audio.exceptions import (
    FFmpegConversionError,
    FFmpegNotInstalledError,
    OutputWriteError,
    UnreadableAudioError,
    UnsupportedAudioFormatError,
)
from ai_service.audio.schema import AudioQualityDiagnostics

logger = logging.getLogger("ai_call_analytics.audio.engine")


def is_ffmpeg_available() -> bool:
    """Check if the ffmpeg executable is available on the system PATH."""
    return shutil.which("ffmpeg") is not None


def to_mono(audio_data: np.ndarray) -> np.ndarray:
    """
    Convert stereo or multi-channel audio data to single-channel mono.

    Averages all channels across the sample axis to preserve all speech content.

    Args:
        audio_data: 1D (mono) or 2D (samples, channels) numpy array.

    Returns:
        1D float32 numpy array.
    """
    if audio_data.ndim == 1:
        return audio_data.astype(np.float32)
    if audio_data.ndim == 2:
        return np.mean(audio_data, axis=1, dtype=np.float32)
    raise ValueError(f"Unsupported audio array dimension: {audio_data.ndim} (expected 1 or 2)")


def resample_audio(audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample 1D audio array to target sampling rate using polyphase filtering.

    Utilizes scipy.signal.resample_poly for linear phase, high anti-aliasing rejection,
    and minimal spectral distortion.

    Args:
        audio_data: 1D numpy array of audio samples.
        orig_sr: Original sampling rate in Hz.
        target_sr: Target sampling rate in Hz.

    Returns:
        1D float32 numpy array resampled to target_sr.
    """
    if orig_sr == target_sr:
        return audio_data.astype(np.float32)

    # Find rational fraction approximation or greatest common divisor
    gcd = np.gcd(orig_sr, target_sr)
    up = target_sr // gcd
    down = orig_sr // gcd

    resampled = scipy.signal.resample_poly(audio_data, up=up, down=down, axis=0)
    return resampled.astype(np.float32)


def normalize_audio(
    audio_data: np.ndarray,
    target_peak_dbfs: float = -1.0,
    min_threshold: float = 1e-4,
) -> tuple[np.ndarray, float]:
    """
    Apply speech-oriented peak amplitude normalization.

    Scales speech linearly to a target peak headroom (default: -1.0 dBFS, peak ~0.891).
    This ensures uniform volume across distinct call recordings while:
    - Avoiding dynamic range compression that alters phoneme structure
    - Leaving natural conversational dynamics and pauses intact
    - Preventing digital clipping during subsequent 16-bit PCM quantization
    - Skipping near-silent recordings to avoid amplifying the analog noise floor

    Args:
        audio_data: 1D float32 audio array (-1.0 to 1.0).
        target_peak_dbfs: Target peak level in dBFS (default: -1.0).
        min_threshold: Minimum absolute peak required to apply scaling.

    Returns:
        Tuple of (normalized_audio_array, gain_in_db).
    """
    current_peak = float(np.max(np.abs(audio_data))) if audio_data.size > 0 else 0.0

    if current_peak < min_threshold:
        # Audio is near-silent; skip amplification to preserve silent baseline
        return audio_data.astype(np.float32), 0.0

    target_linear_peak = 10.0 ** (target_peak_dbfs / 20.0)
    gain = target_linear_peak / current_peak
    gain_db = round(float(20.0 * np.log10(gain)), 2)

    normalized = audio_data * gain
    # Clip to absolute [-1.0, 1.0] boundary as safety guard
    normalized = np.clip(normalized, -1.0, 1.0)

    return normalized.astype(np.float32), gain_db


def convert_with_ffmpeg(
    input_path: Path,
    output_path: Path,
    config: AudioConfig,
) -> None:
    """
    Convert audio file using FFmpeg subprocess execution.

    Args:
        input_path: Path to input audio file.
        output_path: Destination path for standardized WAV output.
        config: AudioConfig instance.

    Raises:
        FFmpegNotInstalledError: If ffmpeg is not found on PATH.
        FFmpegConversionError: If FFmpeg returns a non-zero exit code.
    """
    if not is_ffmpeg_available():
        raise FFmpegNotInstalledError(
            "FFmpeg executable not found on system PATH. Please install FFmpeg "
            "(e.g., 'winget install Gyan.FFmpeg' on Windows or 'apt-get install -y ffmpeg' on Linux)."
        )

    # Secure argument list avoiding shell execution and injection
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-loglevel", "error",
        "-i", str(input_path),
        "-vn",  # Strip video streams if container has them
        "-ac", str(config.target_channels),
        "-ar", str(config.target_sample_rate),
        "-c:a", "pcm_s16le",
        str(output_path),
    ]

    logger.debug("Executing FFmpeg command: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as err:
        raise FFmpegConversionError(f"Failed to execute FFmpeg for '{input_path.name}': {err}") from err

    if proc.returncode != 0:
        err_msg = proc.stderr.strip() if proc.stderr else f"Exit code {proc.returncode}"
        raise FFmpegConversionError(f"FFmpeg conversion failed for '{input_path.name}': {err_msg}")


def convert_with_python(
    input_path: Path,
    output_path: Path,
    config: AudioConfig,
) -> tuple[np.ndarray, AudioQualityDiagnostics]:
    """
    Convert, resample, mono-mix, and normalize audio using soundfile and scipy.

    Args:
        input_path: Path to input audio file.
        output_path: Destination path for standardized WAV output.
        config: AudioConfig instance.

    Returns:
        Tuple of (processed_samples_array, quality_diagnostics).

    Raises:
        UnreadableAudioError: If soundfile fails to decode the file.
        OutputWriteError: If saving the standardized WAV fails.
    """
    try:
        data, sr = sf.read(str(input_path), dtype="float32")
    except Exception as err:
        raise UnreadableAudioError(f"Native audio reader failed on '{input_path.name}': {err}") from err

    # 1. Convert to mono
    mono_data = to_mono(data)

    # 2. Resample to target sample rate (16 kHz)
    resampled = resample_audio(mono_data, orig_sr=sr, target_sr=config.target_sample_rate)

    # 3. Apply peak amplitude normalization
    if config.normalization_enabled:
        normalized, gain_db = normalize_audio(
            resampled,
            target_peak_dbfs=config.target_peak_dbfs,
            min_threshold=config.min_norm_peak_threshold,
        )
        logger.debug("Applied normalization to '%s': gain=%.2f dB", input_path.name, gain_db)
    else:
        normalized = np.clip(resampled, -1.0, 1.0).astype(np.float32)

    # 4. Analyze quality diagnostics on final standardized buffer
    diagnostics = analyze_audio_quality(normalized, config.target_sample_rate, config)

    # 5. Write to output WAV PCM_16
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sf.write(
            str(output_path),
            normalized,
            config.target_sample_rate,
            subtype=config.target_subtype,
            format=config.target_format.upper(),
        )
    except Exception as err:
        raise OutputWriteError(f"Failed to write standardized WAV to '{output_path}': {err}") from err

    return normalized, diagnostics


def process_audio_file(
    input_path: str | Path,
    output_path: str | Path,
    config: AudioConfig | None = None,
) -> AudioQualityDiagnostics:
    """
    Execute end-to-end audio processing to standardized 16kHz mono PCM16 WAV.

    Chooses between FFmpeg engine and Python native engine based on format
    and environment availability.

    Args:
        input_path: Path to source audio file.
        output_path: Target destination path for standardized WAV.
        config: Optional AudioConfig instance.

    Returns:
        AudioQualityDiagnostics for the processed audio.
    """
    cfg = config or DEFAULT_AUDIO_CONFIG
    in_p = Path(input_path).resolve()
    out_p = Path(output_path).resolve()

    suffix = in_p.suffix.lower()

    # Formats that require external FFmpeg container decoding (e.g. M4A/AAC containers)
    ffmpeg_required_formats = {".m4a", ".aac", ".wma"}

    if suffix in ffmpeg_required_formats and not is_ffmpeg_available():
        raise FFmpegNotInstalledError(
            f"Input format '{suffix}' requires FFmpeg for decoding, but ffmpeg was not found on PATH. "
            f"Please install FFmpeg or convert to .wav / .mp3 / .flac / .ogg before processing."
        )

    # Decide processing backend
    use_ffmpeg = is_ffmpeg_available() and (cfg.prefer_ffmpeg or suffix in ffmpeg_required_formats)

    if use_ffmpeg:
        logger.info("Processing '%s' via FFmpeg engine", in_p.name)
        convert_with_ffmpeg(in_p, out_p, cfg)

        # Apply normalization and run diagnostics on FFmpeg output
        data, sr = sf.read(str(out_p), dtype="float32")
        if cfg.normalization_enabled:
            normalized, gain_db = normalize_audio(
                data,
                target_peak_dbfs=cfg.target_peak_dbfs,
                min_threshold=cfg.min_norm_peak_threshold,
            )
            sf.write(
                str(out_p),
                normalized,
                cfg.target_sample_rate,
                subtype=cfg.target_subtype,
                format=cfg.target_format.upper(),
            )
            data = normalized
        diagnostics = analyze_audio_quality(data, cfg.target_sample_rate, cfg)
        return diagnostics
    else:
        logger.info("Processing '%s' via Python native engine (soundfile + scipy)", in_p.name)
        _, diagnostics = convert_with_python(in_p, out_p, cfg)
        return diagnostics
