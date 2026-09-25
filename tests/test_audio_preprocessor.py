"""
Unit and Integration tests for the Audio Preprocessing Pipeline.

Tests all ingestion, validation, resampling, mono-mixing, normalization,
quality diagnostics, idempotency, and output verification mechanisms.
Uses deterministic synthetic fixtures and offline in-memory generation.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf

from ai_service.audio.config import AudioConfig
from ai_service.audio.diagnostics import analyze_audio_quality
from ai_service.audio.engine import (
    convert_with_ffmpeg,
    is_ffmpeg_available,
    normalize_audio,
    process_audio_file,
    resample_audio,
    to_mono,
)
from ai_service.audio.exceptions import (
    AudioFileNotFoundError,
    AudioProcessingError,
    FFmpegConversionError,
    FFmpegNotInstalledError,
    InvalidDurationError,
    OutputValidationError,
    UnreadableAudioError,
    UnsupportedAudioFormatError,
)
from ai_service.audio.preprocessor import AudioPreprocessor
from ai_service.audio.schema import AudioProcessingResult
from ai_service.audio.validator import (
    extract_audio_metadata,
    validate_audio_file,
    verify_standardized_audio,
)


class TestAudioPreprocessingPipeline(unittest.TestCase):
    """Test suite for Audio Preprocessor, Engine, and Validators."""

    def setUp(self) -> None:
        """Create temporary test directory and synthetic audio fixtures."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="audio_test_"))
        self.output_dir = self.test_dir / "processed"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.config = AudioConfig(
            output_dir=str(self.output_dir),
            min_duration_seconds=0.2,
            max_duration_seconds=30.0,
            normalization_enabled=True,
            target_peak_dbfs=-1.0,
        )
        self.preprocessor = AudioPreprocessor(self.config)

    def tearDown(self) -> None:
        """Clean up temporary test artifacts."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_synthetic_wav(
        self,
        filename: str,
        duration_s: float = 1.0,
        sample_rate: int = 44100,
        channels: int = 2,
        freq: float = 440.0,
        amplitude: float = 0.5,
    ) -> Path:
        """Helper to generate deterministic multi-channel synthetic audio."""
        path = self.test_dir / filename
        t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)

        if channels == 1:
            samples = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        else:
            ch1 = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)
            ch2 = (amplitude * 0.7 * np.sin(2 * np.pi * (freq * 1.5) * t)).astype(np.float32)
            samples = np.column_stack([ch1, ch2])

        sf.write(str(path), samples, sample_rate, subtype="PCM_16", format="WAV")
        return path

    # ------------------------------------------------------------------------
    # 1. Validation Tests (Step 4 & Step 19)
    # ------------------------------------------------------------------------
    def test_validate_valid_wav(self) -> None:
        """Verify validation passes on a well-formed WAV file."""
        wav_path = self._create_synthetic_wav("valid.wav", duration_s=1.0, sample_rate=16000, channels=1)
        res = validate_audio_file(wav_path, self.config)

        self.assertTrue(res.valid)
        self.assertEqual(len(res.errors), 0)
        self.assertEqual(res.channels, 1)
        self.assertEqual(res.sample_rate, 16000)
        self.assertAlmostEqual(res.duration_seconds, 1.0, places=2)

    def test_validate_missing_file(self) -> None:
        """Verify validation fails when file does not exist."""
        res = validate_audio_file(self.test_dir / "non_existent.wav", self.config)
        self.assertFalse(res.valid)
        self.assertTrue(any("not found" in err.lower() for err in res.errors))

    def test_validate_empty_file(self) -> None:
        """Verify validation fails on an empty 0-byte file."""
        empty_path = self.test_dir / "empty.wav"
        empty_path.write_bytes(b"")

        res = validate_audio_file(empty_path, self.config)
        self.assertFalse(res.valid)
        self.assertTrue(any("empty" in err.lower() for err in res.errors))

    def test_validate_unsupported_format(self) -> None:
        """Verify validation fails when audio container extension is unsupported."""
        txt_path = self.test_dir / "notes.txt"
        txt_path.write_text("not an audio file")

        res = validate_audio_file(txt_path, self.config)
        self.assertFalse(res.valid)
        self.assertTrue(any("unsupported" in err.lower() for err in res.errors))

    def test_validate_duration_too_short(self) -> None:
        """Verify validation fails when duration is below min_duration_seconds."""
        short_wav = self._create_synthetic_wav("too_short.wav", duration_s=0.05, sample_rate=16000, channels=1)
        res = validate_audio_file(short_wav, self.config)

        self.assertFalse(res.valid)
        self.assertTrue(any("shorter than minimum" in err.lower() for err in res.errors))

    def test_validate_duration_too_long(self) -> None:
        """Verify validation fails when duration exceeds max_duration_seconds."""
        cfg = AudioConfig(output_dir=str(self.output_dir), max_duration_seconds=0.5, min_duration_seconds=0.1)
        long_wav = self._create_synthetic_wav("too_long.wav", duration_s=1.0, sample_rate=16000, channels=1)
        res = validate_audio_file(long_wav, cfg)

        self.assertFalse(res.valid)
        self.assertTrue(any("exceeds maximum" in err.lower() for err in res.errors))

    def test_validate_corrupted_audio(self) -> None:
        """Verify validation fails when file has WAV extension but invalid binary content."""
        corrupt_path = self.test_dir / "corrupt.wav"
        corrupt_path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEbad_corrupt_data_here")

        res = validate_audio_file(corrupt_path, self.config)
        self.assertFalse(res.valid)
        self.assertTrue(any("unreadable" in err.lower() for err in res.errors))

    # ------------------------------------------------------------------------
    # 2. Conversion & Standardization Tests (Steps 5, 6, 7, 8, 18)
    # ------------------------------------------------------------------------
    def test_convert_stereo_44k_to_mono_16k_wav(self) -> None:
        """Verify stereo 44.1 kHz WAV is converted to mono 16 kHz PCM_16 WAV."""
        in_path = self._create_synthetic_wav("stereo_44k.wav", duration_s=1.2, sample_rate=44100, channels=2)
        out_path = self.output_dir / "converted_16k.wav"

        result = self.preprocessor.preprocess(in_path, output_path=out_path)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.sample_rate, 16000)
        self.assertEqual(result.channels, 1)
        self.assertEqual(result.output_format, "wav")
        self.assertTrue(out_path.exists())

        # Inspect resulting file directly
        info = sf.info(str(out_path))
        self.assertEqual(info.samplerate, 16000)
        self.assertEqual(info.channels, 1)
        self.assertEqual(info.format, "WAV")
        self.assertEqual(info.subtype, "PCM_16")
        self.assertAlmostEqual(info.duration, 1.2, places=2)

    def test_convert_48k_to_16k(self) -> None:
        """Verify 48 kHz studio recording is resampled accurately to 16 kHz."""
        in_path = self._create_synthetic_wav("audio_48k.wav", duration_s=0.8, sample_rate=48000, channels=1)
        result = self.preprocessor.preprocess(in_path)

        self.assertEqual(result.sample_rate, 16000)
        self.assertEqual(result.channels, 1)
        self.assertAlmostEqual(result.duration_seconds, 0.8, places=2)

    def test_convert_8k_minds14_to_16k(self) -> None:
        """Verify 8 kHz telephony recording (MInDS-14 standard) is upsampled to 16 kHz."""
        in_path = self._create_synthetic_wav("telephony_8k.wav", duration_s=1.5, sample_rate=8000, channels=1)
        result = self.preprocessor.preprocess(in_path)

        self.assertEqual(result.sample_rate, 16000)
        self.assertEqual(result.channels, 1)
        self.assertAlmostEqual(result.duration_seconds, 1.5, places=2)

    def test_convert_flac_and_ogg_formats(self) -> None:
        """Verify FLAC and OGG audio formats are standardized to 16kHz mono WAV."""
        t = np.linspace(0, 1.0, 22050, endpoint=False)
        data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        # FLAC test
        flac_path = self.test_dir / "sample.flac"
        sf.write(str(flac_path), data, 22050, format="FLAC")
        flac_result = self.preprocessor.preprocess(flac_path)
        self.assertEqual(flac_result.sample_rate, 16000)
        self.assertEqual(flac_result.channels, 1)

        # OGG test
        ogg_path = self.test_dir / "sample.ogg"
        sf.write(str(ogg_path), data, 22050, format="OGG")
        ogg_result = self.preprocessor.preprocess(ogg_path)
        self.assertEqual(ogg_result.sample_rate, 16000)
        self.assertEqual(ogg_result.channels, 1)

    # ------------------------------------------------------------------------
    # 3. Normalization Tests (Step 8)
    # ------------------------------------------------------------------------
    def test_normalization_reaches_target_headroom(self) -> None:
        """Verify peak amplitude normalization scales speech to -1.0 dBFS (peak ~0.891)."""
        # Low amplitude audio (peak = 0.1)
        in_path = self._create_synthetic_wav("quiet.wav", duration_s=1.0, sample_rate=16000, channels=1, amplitude=0.1)
        result = self.preprocessor.preprocess(in_path)

        data, sr = sf.read(result.output_path)
        actual_peak = np.max(np.abs(data))
        target_linear_peak = 10.0 ** (-1.0 / 20.0)  # ~0.89125

        # Check peak is normalized to -1.0 dBFS within tolerance
        self.assertAlmostEqual(actual_peak, target_linear_peak, places=2)
        self.assertIsNotNone(result.quality_diagnostics)
        self.assertAlmostEqual(result.quality_diagnostics.peak_dbfs, -1.0, places=1)

    def test_normalization_skips_near_silent_audio(self) -> None:
        """Verify normalization does not amplify pure silence or near-zero background noise."""
        silent_data = np.zeros(16000, dtype=np.float32)
        norm, gain_db = normalize_audio(silent_data, target_peak_dbfs=-1.0)
        self.assertEqual(gain_db, 0.0)
        self.assertEqual(np.max(np.abs(norm)), 0.0)

    # ------------------------------------------------------------------------
    # 4. Audio Quality Diagnostics Tests (Step 10)
    # ------------------------------------------------------------------------
    def test_excessive_silence_warning(self) -> None:
        """Verify warning is emitted when audio contains > 90% silence."""
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        # 95% silence, 5% active tone
        audio = np.zeros(16000, dtype=np.float32)
        audio[:800] = 0.5 * np.sin(2 * np.pi * 440 * t[:800])

        diagnostics = analyze_audio_quality(audio, sample_rate=16000, config=self.config)
        self.assertTrue(diagnostics.is_silent)
        self.assertGreater(diagnostics.silence_percentage, 90.0)
        self.assertTrue(any("excessive silence" in w.lower() for w in diagnostics.warnings))

    def test_clipping_detection_warning(self) -> None:
        """Verify clipping warning is emitted when samples saturate at full scale."""
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        # Artificially clamp to ceiling 1.0 to simulate digital clipping
        audio = np.clip(audio * 1.5, -1.0, 1.0)

        diagnostics = analyze_audio_quality(audio, sample_rate=16000, config=self.config)
        self.assertTrue(diagnostics.is_clipped)
        self.assertTrue(any("clipping" in w.lower() for w in diagnostics.warnings))

    def test_low_amplitude_warning(self) -> None:
        """Verify warning is emitted on unusually faint/inaudible call audio."""
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        # Very faint tone: amplitude = 0.001 (approx -60 dBFS)
        audio = (0.001 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        cfg = AudioConfig(silence_threshold_db=-70.0)  # Lower silence threshold so it flags as low amplitude
        diagnostics = analyze_audio_quality(audio, sample_rate=16000, config=cfg)
        self.assertTrue(any("low audio amplitude" in w.lower() for w in diagnostics.warnings))

    # ------------------------------------------------------------------------
    # 5. Idempotency & Output Verification Tests (Steps 13, 14, 18)
    # ------------------------------------------------------------------------
    def test_idempotent_reuse_existing(self) -> None:
        """Verify pipeline reuses valid pre-existing standardized audio without re-computation."""
        in_path = self._create_synthetic_wav("idempotent.wav", duration_s=1.0, sample_rate=16000, channels=1)

        # First run: should be 'success'
        res1 = self.preprocessor.preprocess(in_path)
        self.assertEqual(res1.status, "success")

        # Second run: should be 'reused'
        res2 = self.preprocessor.preprocess(in_path)
        self.assertEqual(res2.status, "reused")
        self.assertEqual(res1.output_path, res2.output_path)

    def test_overwrite_policy(self) -> None:
        """Verify overwrite policy re-processes and updates file when configured."""
        in_path = self._create_synthetic_wav("overwrite_test.wav", duration_s=1.0, sample_rate=16000, channels=1)
        cfg = AudioConfig(output_dir=str(self.output_dir), overwrite_policy="overwrite")
        pre = AudioPreprocessor(cfg)

        res1 = pre.preprocess(in_path)
        self.assertEqual(res1.status, "success")

        res2 = pre.preprocess(in_path)
        self.assertEqual(res2.status, "success")

    def test_verify_standardized_audio_validates_correctly(self) -> None:
        """Verify verify_standardized_audio passes on valid output and fails on corrupt."""
        valid_wav = self._create_synthetic_wav("valid_std.wav", duration_s=1.0, sample_rate=16000, channels=1)
        meta = verify_standardized_audio(valid_wav, self.config)
        self.assertEqual(meta.sample_rate, 16000)
        self.assertEqual(meta.channels, 1)
        self.assertEqual(meta.format, "WAV")

        # Non-standard sample rate should raise OutputValidationError
        invalid_sr_wav = self._create_synthetic_wav("invalid_sr.wav", duration_s=1.0, sample_rate=44100, channels=1)
        with self.assertRaises(OutputValidationError):
            verify_standardized_audio(invalid_sr_wav, self.config)

    # ------------------------------------------------------------------------
    # 6. Temporary File Cleanup & Safety Tests (Steps 12 & 26)
    # ------------------------------------------------------------------------
    def test_temporary_files_cleaned_up_on_failure(self) -> None:
        """Verify temporary files are completely deleted even when conversion fails."""
        in_path = self._create_synthetic_wav("fail_test.wav", duration_s=1.0, sample_rate=16000, channels=1)

        # Mock process_audio_file to simulate an abrupt failure during processing
        with patch("ai_service.audio.preprocessor.process_audio_file") as mock_proc:
            mock_proc.side_effect = RuntimeError("Disk write failed unexpectedly")
            with self.assertRaises(RuntimeError):
                self.preprocessor.preprocess(in_path)

        # Confirm no orphaned .tmp.wav files remain in output directory
        tmp_files = list(self.output_dir.glob("proc_*"))
        self.assertEqual(len(tmp_files), 0)

    # ------------------------------------------------------------------------
    # 7. Error Handling Tests (Step 16)
    # ------------------------------------------------------------------------
    def test_ffmpeg_not_installed_error_on_m4a(self) -> None:
        """Verify FFmpegNotInstalledError is raised when M4A is passed and FFmpeg is absent."""
        m4a_path = self.test_dir / "sample.m4a"
        m4a_path.write_bytes(b"dummy m4a content")

        with patch("ai_service.audio.engine.is_ffmpeg_available", return_value=False):
            with self.assertRaises(AudioProcessingError) as ctx:
                process_audio_file(m4a_path, self.output_dir / "out.wav", self.config)
            self.assertIn("requires FFmpeg", str(ctx.exception))

    def test_ffmpeg_conversion_failure_handling(self) -> None:
        """Verify FFmpegConversionError is raised when FFmpeg subprocess returns non-zero."""
        in_path = self._create_synthetic_wav("test.wav")
        out_path = self.output_dir / "out.wav"

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "Invalid data found when processing input"

        with patch("ai_service.audio.engine.is_ffmpeg_available", return_value=True):
            with patch("subprocess.run", return_value=mock_proc):
                with self.assertRaises(FFmpegConversionError) as ctx:
                    convert_with_ffmpeg(in_path, out_path, self.config)
                self.assertIn("Invalid data found", str(ctx.exception))

    # ------------------------------------------------------------------------
    # 8. MInDS-14 Dataset Bridging Test
    # ------------------------------------------------------------------------
    def test_preprocess_minds14_synthetic_example(self) -> None:
        """Verify bridging MInDS-14 dataset row (8kHz mono WAV bytes) into 16kHz mono WAV."""
        buf = io.BytesIO()
        t = np.linspace(0, 1.0, 8000, endpoint=False)
        tone = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        sf.write(buf, tone, 8000, subtype="PCM_16", format="WAV")
        wav_bytes = buf.getvalue()

        example = {
            "path": "minds14_sample_0.wav",
            "audio": {"bytes": wav_bytes, "path": "minds14_sample_0.wav"},
            "transcription": "I want to check my account balance",
            "intent_class": 4,
        }

        result = self.preprocessor.preprocess_minds14_example(example, call_id="call_12345")
        self.assertEqual(result.sample_rate, 16000)
        self.assertEqual(result.channels, 1)
        self.assertEqual(result.output_format, "wav")
        self.assertAlmostEqual(result.duration_seconds, 1.0, places=2)
        self.assertIn("call_12345", result.output_path)


if __name__ == "__main__":
    unittest.main()
