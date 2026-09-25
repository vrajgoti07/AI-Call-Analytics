"""
Unit and integration test suite for Phase 3: Whisper / faster-whisper ASR.

Validates:
- Configuration handling, device/compute-type fallback, and environment loading
- Model Manager singleton lifecycle, caching, thread safety, and reuse
- Audio input contract validation (16kHz mono PCM16 WAV strict enforcement)
- Timestamp monotonicity, bounds checking, and anomaly diagnostics
- WhisperTranscriber speech-to-text inference with mocked faster-whisper engine
- Future-proof data contract (speaker field ready for Phase 4)
- Real-model integration test on preprocessed MInDS-14 sample
"""

from __future__ import annotations

import io
import os
import struct
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ai_service.asr.config import WhisperConfig, DEFAULT_WHISPER_CONFIG
from ai_service.asr.exceptions import (
    ASRError,
    AudioNotFoundError,
    EmptyTranscriptionError,
    InvalidAudioStreamError,
    InvalidDurationError,
    InvalidPreprocessedAudioError,
    ModelConfigurationError,
    ModelLoadError,
    TranscriptionError,
    UnsupportedRuntimeError,
)
from ai_service.asr.model_manager import WhisperModelManager
from ai_service.asr.schema import (
    TranscriptSegment,
    TranscriptionMetadata,
    TranscriptionResult,
    WordTiming,
)
from ai_service.asr.transcriber import WhisperTranscriber
from ai_service.asr.validator import (
    detect_transcription_anomalies,
    validate_asr_input,
    validate_timestamps,
)


# ============================================================================
# Helpers & Fixtures
# ============================================================================

def create_synthetic_wav(
    filepath: Path,
    sample_rate: int = 16000,
    channels: int = 1,
    duration_seconds: float = 1.0,
    sample_width: int = 2,  # 16-bit
) -> Path:
    """Create a synthetic uncompressed PCM WAV file for contract testing."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(sample_rate * duration_seconds)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        # Write small sine/silence bytes
        data = bytearray(num_samples * channels * sample_width)
        wf.writeframes(data)
    return filepath


@pytest.fixture
def temp_wav(tmp_path: Path) -> Path:
    """Standard 16kHz mono PCM16 WAV file conforming to Phase 2 contract."""
    return create_synthetic_wav(tmp_path / "standard.wav", sample_rate=16000, channels=1, duration_seconds=2.0)


# ============================================================================
# Test Section 1: Configuration & Runtime Fallback
# ============================================================================

class TestWhisperConfig:
    def test_default_configuration(self) -> None:
        cfg = WhisperConfig()
        assert cfg.model_size == "base"
        assert cfg.device == "auto"
        assert cfg.compute_type == "auto"
        assert cfg.language == "auto"
        assert cfg.vad_filter is False  # Pauses preserved for call analytics
        assert cfg.word_timestamps is True

    def test_invalid_model_size_raises(self) -> None:
        with pytest.raises(ModelConfigurationError, match="Unsupported Whisper model size"):
            WhisperConfig(model_size="gigantic").resolve_runtime()

    def test_invalid_device_raises(self) -> None:
        with pytest.raises(ModelConfigurationError, match="Unsupported device"):
            WhisperConfig(device="tpu").resolve_runtime()

    def test_cpu_float16_fallback(self) -> None:
        cfg = WhisperConfig(device="cpu", compute_type="float16")
        dev, comp = cfg.resolve_runtime()
        assert dev == "cpu"
        # CPU does not support float16 natively in CTranslate2 -> auto-corrected to int8/float32
        assert comp in ("int8", "float32")

    def test_cuda_fallback_when_unavailable(self) -> None:
        with patch("ai_service.asr.config._is_cuda_usable", return_value=False):
            # If explicitly requested, raises UnsupportedRuntimeError
            with pytest.raises(UnsupportedRuntimeError, match="CUDA requested for Whisper ASR"):
                WhisperConfig(device="cuda").resolve_runtime()

            # If 'auto' requested, gracefully falls back to CPU
            auto_cfg = WhisperConfig(device="auto")
            dev, comp = auto_cfg.resolve_runtime()
            assert dev == "cpu"
            assert comp in ("int8", "float32")

    def test_from_env_loading(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WHISPER_MODEL_SIZE", "tiny")
        monkeypatch.setenv("WHISPER_DEVICE", "cpu")
        monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "int8")
        monkeypatch.setenv("WHISPER_LANGUAGE", "es")
        monkeypatch.setenv("WHISPER_BEAM_SIZE", "3")
        monkeypatch.setenv("WHISPER_VAD_FILTER", "true")

        cfg = WhisperConfig.from_env()
        assert cfg.model_size == "tiny"
        assert cfg.device == "cpu"
        assert cfg.compute_type == "int8"
        assert cfg.language == "es"
        assert cfg.beam_size == 3
        assert cfg.vad_filter is True


# ============================================================================
# Test Section 2: Model Manager & Singleton Lifecycle
# ============================================================================

class TestWhisperModelManager:
    def test_singleton_instance(self) -> None:
        mgr1 = WhisperModelManager.get_instance()
        mgr2 = WhisperModelManager.get_instance()
        assert mgr1 is mgr2

    @patch("faster_whisper.WhisperModel")
    def test_model_cached_and_reused(self, mock_model_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_model_cls.return_value = mock_instance

        manager = WhisperModelManager.get_instance()
        manager.clear_cache()

        cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type="int8")

        model_a = manager.get_model(cfg)
        model_b = manager.get_model(cfg)

        assert model_a is model_b
        # Verify WhisperModel was initialized only once
        assert mock_model_cls.call_count == 1
        assert manager.loaded_model_count == 1

    @patch("faster_whisper.WhisperModel", side_effect=RuntimeError("Out of memory"))
    def test_model_load_failure_raises_model_load_error(self, mock_model_cls: MagicMock) -> None:
        manager = WhisperModelManager.get_instance()
        manager.clear_cache()

        cfg = WhisperConfig(model_size="large-v3", device="cpu", compute_type="int8")
        with pytest.raises(ModelLoadError, match="Failed to load Whisper model"):
            manager.get_model(cfg)


# ============================================================================
# Test Section 3: Audio Input Contract Validation (Phase 2 Compliance)
# ============================================================================

class TestAudioInputValidation:
    def test_valid_preprocessed_wav_passes(self, temp_wav: Path) -> None:
        duration = validate_asr_input(temp_wav)
        assert abs(duration - 2.0) < 0.05

    def test_missing_audio_file_raises_audio_not_found(self, tmp_path: Path) -> None:
        non_existent = tmp_path / "ghost_call.wav"
        with pytest.raises(AudioNotFoundError, match="Audio file not found"):
            validate_asr_input(non_existent)

    def test_non_wav_extension_rejected(self, tmp_path: Path) -> None:
        mp3_file = tmp_path / "call.mp3"
        mp3_file.write_bytes(b"ID3" + b"\x00" * 200)
        with pytest.raises(InvalidPreprocessedAudioError):
            validate_asr_input(mp3_file)

    def test_incorrect_sample_rate_rejected(self, tmp_path: Path) -> None:
        bad_sr_wav = create_synthetic_wav(tmp_path / "8khz.wav", sample_rate=8000, channels=1)
        with pytest.raises(InvalidPreprocessedAudioError, match="must be 16,000 Hz"):
            validate_asr_input(bad_sr_wav)

    def test_multi_channel_rejected(self, tmp_path: Path) -> None:
        stereo_wav = create_synthetic_wav(tmp_path / "stereo.wav", sample_rate=16000, channels=2)
        with pytest.raises(InvalidPreprocessedAudioError, match="single-channel mono"):
            validate_asr_input(stereo_wav)

    def test_zero_duration_rejected(self, tmp_path: Path) -> None:
        zero_wav = create_synthetic_wav(tmp_path / "empty.wav", sample_rate=16000, channels=1, duration_seconds=0.0)
        with pytest.raises(InvalidPreprocessedAudioError, match="duration must be greater than 0s"):
            validate_asr_input(zero_wav)


# ============================================================================
# Test Section 4: Timestamps & Anomaly Diagnostics
# ============================================================================

class TestTimestampAndAnomalyValidation:
    def test_valid_monotonic_segments_pass(self) -> None:
        segments = [
            TranscriptSegment(segment_id=0, start=0.0, end=2.5, text="Hello there."),
            TranscriptSegment(segment_id=1, start=2.5, end=5.0, text="How can I help you today?"),
        ]
        warnings = validate_timestamps(segments, audio_duration=5.0)
        assert len(warnings) == 0

    def test_negative_start_detected(self) -> None:
        segments = [
            TranscriptSegment(segment_id=0, start=-0.5, end=2.0, text="Invalid start."),
        ]
        warnings = validate_timestamps(segments, audio_duration=5.0)
        assert any("negative start" in w.lower() for w in warnings)

    def test_end_before_start_detected(self) -> None:
        segments = [
            TranscriptSegment(segment_id=0, start=3.0, end=2.0, text="Backwards time."),
        ]
        warnings = validate_timestamps(segments, audio_duration=5.0)
        assert any("invalid duration" in w.lower() for w in warnings)

    def test_segment_exceeding_duration_detected(self) -> None:
        segments = [
            TranscriptSegment(segment_id=0, start=0.0, end=12.0, text="Exceeds file length."),
        ]
        warnings = validate_timestamps(segments, audio_duration=5.0)
        assert any("beyond" in w.lower() or "exceeds" in w.lower() for w in warnings)

    def test_detect_repetition_hallucination(self) -> None:
        segments = [
            TranscriptSegment(segment_id=0, start=0.0, end=2.0, text="Thank you for watching."),
            TranscriptSegment(segment_id=1, start=2.0, end=4.0, text="Thank you for watching."),
            TranscriptSegment(segment_id=2, start=4.0, end=6.0, text="Thank you for watching."),
        ]
        warnings = detect_transcription_anomalies(
            text="Thank you for watching. Thank you for watching. Thank you for watching.",
            segments=segments,
            audio_duration=6.0,
        )
        assert any("hallucination" in w.lower() or "repeats" in w.lower() for w in warnings)

    def test_detect_empty_speech_with_duration(self) -> None:
        warnings = detect_transcription_anomalies(
            text="",
            segments=[],
            audio_duration=10.0,
        )
        assert any("no speech detected" in w.lower() for w in warnings)


# ============================================================================
# Test Section 5: WhisperTranscriber (Mocked Inference)
# ============================================================================

class TestWhisperTranscriber:
    @patch.object(WhisperModelManager, "get_model")
    def test_successful_transcription_pipeline(self, mock_get_model: MagicMock, temp_wav: Path) -> None:
        # Mock faster-whisper segment generator
        mock_word1 = SimpleNamespace(word="Hello", start=0.1, end=0.6, probability=0.98)
        mock_word2 = SimpleNamespace(word="world", start=0.7, end=1.2, probability=0.95)

        mock_segment = SimpleNamespace(
            id=0,
            start=0.0,
            end=1.5,
            text="Hello world",
            avg_logprob=-0.25,
            no_speech_prob=0.01,
            words=[mock_word1, mock_word2],
        )

        mock_info = SimpleNamespace(
            language="en",
            language_probability=0.992,
            duration=2.0,
        )

        mock_whisper_model = MagicMock()
        mock_whisper_model.transcribe.return_value = (iter([mock_segment]), mock_info)
        mock_get_model.return_value = mock_whisper_model

        cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type="int8")
        transcriber = WhisperTranscriber(cfg)

        result: TranscriptionResult = transcriber.transcribe(temp_wav)

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.language == "en"
        assert abs(result.language_probability - 0.992) < 0.001
        assert len(result.segments) == 1
        assert result.segments[0].segment_id == 0
        assert result.segments[0].start == 0.0
        assert result.segments[0].end == 1.5
        assert result.segments[0].text == "Hello world"
        assert result.segments[0].speaker is None  # Ready for Phase 4 diarization!
        assert len(result.segments[0].words) == 2
        assert result.segments[0].words[0].word == "Hello"
        assert result.real_time_factor >= 0.0
        assert result.metadata is not None
        assert result.metadata.model_name == "tiny"

    @patch.object(WhisperModelManager, "get_model")
    def test_explicit_language_override(self, mock_get_model: MagicMock, temp_wav: Path) -> None:
        mock_segment = SimpleNamespace(
            id=0,
            start=0.0,
            end=1.0,
            text="Bonjour",
            avg_logprob=-0.1,
            no_speech_prob=0.02,
            words=[],
        )
        mock_info = SimpleNamespace(language="fr", language_probability=0.99, duration=2.0)
        mock_whisper_model = MagicMock()
        mock_whisper_model.transcribe.return_value = (iter([mock_segment]), mock_info)
        mock_get_model.return_value = mock_whisper_model

        cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type="int8", language="fr")
        transcriber = WhisperTranscriber(cfg)
        result = transcriber.transcribe(temp_wav)

        mock_whisper_model.transcribe.assert_called_once()
        _, kwargs = mock_whisper_model.transcribe.call_args
        assert kwargs["language"] == "fr"
        assert result.language == "fr"

    @patch.object(WhisperModelManager, "get_model")
    def test_empty_speech_transcription(self, mock_get_model: MagicMock, temp_wav: Path) -> None:
        mock_info = SimpleNamespace(language="en", language_probability=0.5, duration=2.0)
        mock_whisper_model = MagicMock()
        mock_whisper_model.transcribe.return_value = (iter([]), mock_info)
        mock_get_model.return_value = mock_whisper_model

        cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type="int8")
        transcriber = WhisperTranscriber(cfg)
        result = transcriber.transcribe(temp_wav)

        assert result.text == ""
        assert len(result.segments) == 0
        assert any("no speech detected" in w.lower() for w in result.warnings)


# ============================================================================
# Test Section 6: Real Model Integration Test
# ============================================================================

class TestRealWhisperIntegration:
    @pytest.mark.integration
    def test_real_tiny_model_on_preprocessed_minds14(self) -> None:
        """Integration test using real faster-whisper tiny model on MInDS-14 demo WAV."""
        demo_audio = Path("data/processed/demo/demo_minds14_sample_0/audio.wav")
        if not demo_audio.exists():
            pytest.skip(f"Preprocessed test audio not found at {demo_audio}")

        cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type="int8", word_timestamps=True)
        transcriber = WhisperTranscriber(cfg)

        result = transcriber.transcribe(demo_audio)

        assert isinstance(result, TranscriptionResult)
        assert len(result.text) > 0
        assert result.language == "en"
        assert len(result.segments) >= 1
        assert result.audio_duration > 5.0
        assert result.processing_time_seconds > 0.0
        assert result.real_time_factor > 0.0
        assert result.segments[0].speaker is None  # Future diarization compatibility
        assert "joint account" in result.text.lower()
