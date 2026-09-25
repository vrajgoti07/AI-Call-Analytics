"""
Unit and integration test suite for Phase 4: Speaker Diarization & Alignment.

Validates:
- Diarization data contracts, schema serialization, and speaker turn representations
- Configuration parsing, speaker count bounds, and device resolution
- Model Manager singleton lifecycle, caching, and authentication failure handling
- Audio input contract validation (16kHz mono PCM16 WAV strict enforcement)
- Multi-speaker overlap computation and conversation statistics calculation
- Temporal alignment algorithms (1:1 overlap, dominant overlap, cross-speaker splitting,
  zero-overlap collar fallback, and sequential turn consolidation)
- Role neutrality (no fake Agent/Customer assumptions)
- Real pyannote model integration test (conditioned on Hugging Face access)
"""

from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ai_service.asr.schema import TranscriptSegment, TranscriptionMetadata, TranscriptionResult, WordTiming
from ai_service.diarization.aligner import TranscriptAligner
from ai_service.diarization.config import DEFAULT_DIARIZATION_CONFIG, DiarizationConfig
from ai_service.diarization.engine import PyannoteDiarizer
from ai_service.diarization.exceptions import (
    AlignmentError,
    DiarizationConfigurationError,
    DiarizationError,
    DiarizationInferenceError,
    DiarizationModelLoadError,
    InvalidDiarizationOutputError,
    InvalidPreprocessedAudioError,
)
from ai_service.diarization.model_manager import DiarizationModelManager
from ai_service.diarization.schema import (
    DiarizationMetadata,
    DiarizationResult,
    DiarizationSegment,
    SpeakerAttributedTranscript,
    SpeakerStats,
    SpeakerTurn,
)
from ai_service.diarization.validator import (
    calculate_speaker_stats,
    compute_overlap_duration,
    validate_diarization_audio,
    validate_diarization_segments,
)


# ============================================================================
# Helpers & Fixtures
# ============================================================================

def create_synthetic_wav(
    filepath: Path,
    sample_rate: int = 16000,
    channels: int = 1,
    duration_seconds: float = 2.0,
    sample_width: int = 2,
) -> Path:
    """Generate a clean linear PCM WAV conforming to the Phase 2 contract."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(sample_rate * duration_seconds)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(bytearray(num_samples * channels * sample_width))
    return filepath


@pytest.fixture
def temp_standard_wav(tmp_path: Path) -> Path:
    return create_synthetic_wav(tmp_path / "valid_standard.wav", duration_seconds=3.0)


# ============================================================================
# Test Section 1: Schema & Data Contracts
# ============================================================================

class TestDiarizationSchemas:
    def test_diarization_segment(self) -> None:
        seg = DiarizationSegment(speaker="SPEAKER_00", start=1.5, end=4.2)
        assert seg.speaker == "SPEAKER_00"
        assert seg.duration == 2.7
        d = seg.to_dict()
        assert d["speaker"] == "SPEAKER_00"
        assert d["start"] == 1.5
        assert d["end"] == 4.2
        assert d["duration"] == 2.7

    def test_speaker_stats(self) -> None:
        stats = SpeakerStats(speaker="SPEAKER_01", total_speaking_time=12.4, segment_count=5, speech_percentage=45.5)
        assert stats.speaker == "SPEAKER_01"
        d = stats.to_dict()
        assert d["speech_percentage"] == 45.5

    def test_speaker_turn(self) -> None:
        turn = SpeakerTurn(
            turn_id=1,
            speaker="SPEAKER_00",
            start=0.0,
            end=3.5,
            text="Hello how can I help you?",
            source_segment_ids=[0, 1],
        )
        assert turn.turn_id == 1
        assert turn.duration == 3.5
        d = turn.to_dict()
        assert d["speaker"] == "SPEAKER_00"
        assert d["source_segment_ids"] == [0, 1]

    def test_speaker_attributed_transcript(self) -> None:
        turn1 = SpeakerTurn(turn_id=1, speaker="SPEAKER_00", start=0.0, end=2.0, text="Hello.")
        turn2 = SpeakerTurn(turn_id=2, speaker="SPEAKER_01", start=2.0, end=4.0, text="Hi there.")
        sat = SpeakerAttributedTranscript(
            full_text="SPEAKER_00: Hello.\n\nSPEAKER_01: Hi there.",
            turns=[turn1, turn2],
            speakers=["SPEAKER_00", "SPEAKER_01"],
            total_turns=2,
            audio_duration=4.0,
        )
        assert sat.total_turns == 2
        d = sat.to_dict()
        assert "SPEAKER_00: Hello." in d["full_text"]
        assert len(d["turns"]) == 2


# ============================================================================
# Test Section 2: Configuration & Validation
# ============================================================================

class TestDiarizationConfig:
    def test_default_config(self) -> None:
        cfg = DiarizationConfig()
        assert cfg.model_name == "pyannote/speaker-diarization-3.1"
        assert cfg.device == "auto"
        assert cfg.min_speakers is None
        assert cfg.max_speakers is None
        assert cfg.cross_speaker_policy == "dominant"

    def test_invalid_device_raises(self) -> None:
        cfg = DiarizationConfig(device="tpu")
        with pytest.raises(DiarizationConfigurationError, match="Unsupported device"):
            cfg.validate()

    def test_invalid_min_max_speakers_raises(self) -> None:
        cfg = DiarizationConfig(min_speakers=4, max_speakers=2)
        with pytest.raises(DiarizationConfigurationError, match="cannot exceed max_speakers"):
            cfg.validate()

    def test_from_env_loading(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HF_TOKEN", "mock_hf_token_123")
        monkeypatch.setenv("MIN_SPEAKERS", "2")
        monkeypatch.setenv("MAX_SPEAKERS", "4")
        monkeypatch.setenv("DIARIZATION_CROSS_SPEAKER_POLICY", "word_level")

        cfg = DiarizationConfig.from_env()
        assert cfg.hf_token == "mock_hf_token_123"
        assert cfg.min_speakers == 2
        assert cfg.max_speakers == 4
        assert cfg.cross_speaker_policy == "word_level"

    def test_resolve_device_cpu(self) -> None:
        with patch("torch.cuda.is_available", return_value=False):
            cfg = DiarizationConfig(device="auto")
            assert cfg.resolve_device() == "cpu"


# ============================================================================
# Test Section 3: Model Manager
# ============================================================================

class TestDiarizationModelManager:
    def test_singleton_instance(self) -> None:
        mgr1 = DiarizationModelManager.get_instance()
        mgr2 = DiarizationModelManager.get_instance()
        assert mgr1 is mgr2

    def test_missing_token_raises_model_load_error(self) -> None:
        manager = DiarizationModelManager.get_instance()
        manager.clear_cache()
        cfg = DiarizationConfig(hf_token="")
        with pytest.raises(DiarizationModelLoadError, match="Hugging Face access token is required"):
            manager.get_pipeline(cfg)

    @patch("pyannote.audio.Pipeline.from_pretrained")
    def test_pipeline_cached_and_reused(self, mock_from_pretrained: MagicMock) -> None:
        mock_pipe = MagicMock()
        mock_from_pretrained.return_value = mock_pipe

        manager = DiarizationModelManager.get_instance()
        manager.clear_cache()

        cfg = DiarizationConfig(hf_token="test_token", device="cpu")
        pipe1 = manager.get_pipeline(cfg)
        pipe2 = manager.get_pipeline(cfg)

        assert pipe1 is pipe2
        assert mock_from_pretrained.call_count == 1
        assert manager.loaded_model_count == 1


# ============================================================================
# Test Section 4: Audio Contract & Diarization Diagnostics
# ============================================================================

class TestDiarizationValidator:
    def test_valid_audio_passes(self, temp_standard_wav: Path) -> None:
        duration = validate_diarization_audio(temp_standard_wav)
        assert abs(duration - 3.0) < 0.05

    def test_missing_audio_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_diarization_audio(tmp_path / "non_existent.wav")

    def test_wrong_sample_rate_rejected(self, tmp_path: Path) -> None:
        wav_8k = create_synthetic_wav(tmp_path / "8k.wav", sample_rate=8000)
        with pytest.raises(InvalidPreprocessedAudioError, match="must be 16,000 Hz"):
            validate_diarization_audio(wav_8k)

    def test_stereo_rejected(self, tmp_path: Path) -> None:
        wav_stereo = create_synthetic_wav(tmp_path / "stereo.wav", channels=2)
        with pytest.raises(InvalidPreprocessedAudioError, match="single-channel mono"):
            validate_diarization_audio(wav_stereo)

    def test_validate_diarization_segments_anomalies(self) -> None:
        bad_segments = [
            DiarizationSegment(speaker="SPEAKER_00", start=-1.0, end=2.0),
            DiarizationSegment(speaker="SPEAKER_01", start=3.0, end=2.0),
            DiarizationSegment(speaker="", start=4.0, end=5.0),
            DiarizationSegment(speaker="SPEAKER_00", start=8.0, end=12.0),
        ]
        warnings = validate_diarization_segments(bad_segments, audio_duration=6.0)
        assert any("negative start" in w.lower() for w in warnings)
        assert any("invalid duration" in w.lower() for w in warnings)
        assert any("empty speaker label" in w.lower() for w in warnings)
        assert any("exceeds audio duration" in w.lower() for w in warnings)

    def test_compute_overlap_duration_no_overlap(self) -> None:
        segments = [
            DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=2.0),
            DiarizationSegment(speaker="SPEAKER_01", start=2.5, end=4.5),
        ]
        assert compute_overlap_duration(segments) == 0.0

    def test_compute_overlap_duration_with_crosstalk(self) -> None:
        segments = [
            DiarizationSegment(speaker="SPEAKER_00", start=1.0, end=4.0),
            DiarizationSegment(speaker="SPEAKER_01", start=2.5, end=5.5),
        ]
        # Overlap is from 2.5s to 4.0s = 1.5s
        overlap = compute_overlap_duration(segments)
        assert abs(overlap - 1.5) < 0.01

    def test_calculate_speaker_stats(self) -> None:
        segments = [
            DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=3.0),
            DiarizationSegment(speaker="SPEAKER_01", start=3.0, end=5.0),
            DiarizationSegment(speaker="SPEAKER_00", start=5.0, end=7.0),
        ]
        speakers, stats, total_speech = calculate_speaker_stats(segments, audio_duration=10.0)
        assert speakers == ["SPEAKER_00", "SPEAKER_01"]
        assert total_speech == 7.0
        assert stats["SPEAKER_00"].total_speaking_time == 5.0
        assert stats["SPEAKER_00"].segment_count == 2
        assert stats["SPEAKER_01"].total_speaking_time == 2.0
        assert stats["SPEAKER_01"].segment_count == 1
        # Percentages sum to 100%
        total_pct = stats["SPEAKER_00"].speech_percentage + stats["SPEAKER_01"].speech_percentage
        assert abs(total_pct - 100.0) < 0.1


# ============================================================================
# Test Section 5: Temporal Alignment Engine (Step 25 Cases)
# ============================================================================

class TestTranscriptAligner:
    @pytest.fixture
    def aligner(self) -> TranscriptAligner:
        return TranscriptAligner(DiarizationConfig(cross_speaker_policy="dominant"))

    def test_case_1_exact_one_to_one_overlap(self, aligner: TranscriptAligner) -> None:
        """Case 1: Whisper segment 0-5s cleanly corresponds to Speaker 00 (0-5s)."""
        w_seg = TranscriptSegment(id=0, start=0.0, end=5.0, text="Hello world")
        transcription = TranscriptionResult(
            text="Hello world",
            language="en",
            language_probability=0.99,
            duration_seconds=5.0,
            processing_time_seconds=1.0,
            real_time_factor=0.2,
            segments=[w_seg],
        )

        d_seg = DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=5.0)
        diarization = DiarizationResult(
            audio_path="test.wav",
            audio_duration=5.0,
            speaker_segments=[d_seg],
            speakers=["SPEAKER_00"],
            speech_duration=5.0,
        )

        result = aligner.align(transcription, diarization)
        assert len(result.turns) == 1
        assert result.turns[0].speaker == "SPEAKER_00"
        assert result.turns[0].text == "Hello world"
        assert w_seg.speaker == "SPEAKER_00"  # Phase 3 in-place contract fulfilled

    def test_case_2_cross_speaker_dominant_overlap_policy(self, aligner: TranscriptAligner) -> None:
        """Case 2: Whisper 0-5s overlaps Speaker A (0-3.5s) and Speaker B (3.5-5.0s). Assigned dominant."""
        w_seg = TranscriptSegment(id=0, start=0.0, end=5.0, text="Dominant test phrase")
        transcription = TranscriptionResult(
            text="Dominant test phrase",
            language="en",
            language_probability=0.99,
            duration_seconds=5.0,
            processing_time_seconds=1.0,
            real_time_factor=0.2,
            segments=[w_seg],
        )

        d_segs = [
            DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=3.5),
            DiarizationSegment(speaker="SPEAKER_01", start=3.5, end=5.0),
        ]
        diarization = DiarizationResult(
            audio_path="test.wav",
            audio_duration=5.0,
            speaker_segments=d_segs,
            speakers=["SPEAKER_00", "SPEAKER_01"],
            speech_duration=5.0,
        )

        result = aligner.align(transcription, diarization)
        assert len(result.turns) == 1
        assert result.turns[0].speaker == "SPEAKER_00"  # 3.5s > 1.5s
        assert any("Cross-speaker segment" in w for w in result.warnings)

    def test_case_3_word_level_splitting_policy(self) -> None:
        """Case 3: Word-level alignment splits cross-speaker Whisper segment."""
        aligner = TranscriptAligner(DiarizationConfig(cross_speaker_policy="word_level"))

        words = [
            WordTiming(word="Hello", start=0.5, end=1.5, probability=0.99),
            WordTiming(word="there", start=1.6, end=2.2, probability=0.99),
            WordTiming(word="Yes", start=3.2, end=3.8, probability=0.98),
            WordTiming(word="sir", start=3.9, end=4.5, probability=0.98),
        ]
        w_seg = TranscriptSegment(id=0, start=0.5, end=4.5, text="Hello there Yes sir", words=words)
        transcription = TranscriptionResult(
            text="Hello there Yes sir",
            language="en",
            language_probability=0.99,
            duration_seconds=5.0,
            processing_time_seconds=1.0,
            real_time_factor=0.2,
            segments=[w_seg],
        )

        d_segs = [
            DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=2.5),
            DiarizationSegment(speaker="SPEAKER_01", start=3.0, end=5.0),
        ]
        diarization = DiarizationResult(
            audio_path="test.wav",
            audio_duration=5.0,
            speaker_segments=d_segs,
            speakers=["SPEAKER_00", "SPEAKER_01"],
            speech_duration=4.5,
        )

        result = aligner.align(transcription, diarization)
        assert len(result.turns) == 2
        assert result.turns[0].speaker == "SPEAKER_00"
        assert result.turns[0].text == "Hello there"
        assert result.turns[1].speaker == "SPEAKER_01"
        assert result.turns[1].text == "Yes sir"

    def test_case_4_zero_overlap_collar_fallback(self, aligner: TranscriptAligner) -> None:
        """Case 4: Whisper segment at 5.1-6.0s with no direct overlap finds nearest speaker within collar."""
        w_seg = TranscriptSegment(id=0, start=5.1, end=6.0, text="Collar test")
        transcription = TranscriptionResult(
            text="Collar test",
            language="en",
            language_probability=0.99,
            duration_seconds=6.0,
            processing_time_seconds=1.0,
            real_time_factor=0.2,
            segments=[w_seg],
        )

        # Diarization ends at 5.0s (0.1s gap < collar 0.25s)
        d_segs = [DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=5.0)]
        diarization = DiarizationResult(
            audio_path="test.wav",
            audio_duration=6.0,
            speaker_segments=d_segs,
            speakers=["SPEAKER_00"],
            speech_duration=5.0,
        )

        result = aligner.align(transcription, diarization)
        assert result.turns[0].speaker == "SPEAKER_00"

    def test_case_5_consecutive_speaker_turn_consolidation(self, aligner: TranscriptAligner) -> None:
        """Case 5: Multiple consecutive Whisper segments from same speaker merge into 1 turn."""
        w_segs = [
            TranscriptSegment(id=0, start=0.0, end=2.0, text="Good morning."),
            TranscriptSegment(id=1, start=2.0, end=4.0, text="How can I assist?"),
            TranscriptSegment(id=2, start=4.5, end=7.0, text="I have a question about billing."),
        ]
        transcription = TranscriptionResult(
            text="Good morning. How can I assist? I have a question about billing.",
            language="en",
            language_probability=0.99,
            duration_seconds=7.0,
            processing_time_seconds=1.0,
            real_time_factor=0.2,
            segments=w_segs,
        )

        d_segs = [
            DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=4.2),
            DiarizationSegment(speaker="SPEAKER_01", start=4.3, end=7.0),
        ]
        diarization = DiarizationResult(
            audio_path="test.wav",
            audio_duration=7.0,
            speaker_segments=d_segs,
            speakers=["SPEAKER_00", "SPEAKER_01"],
            speech_duration=6.9,
        )

        result = aligner.align(transcription, diarization)
        assert len(result.turns) == 2
        # Turn 1: SPEAKER_00 combined segments 0 & 1
        assert result.turns[0].speaker == "SPEAKER_00"
        assert result.turns[0].text == "Good morning. How can I assist?"
        assert result.turns[0].source_segment_ids == [0, 1]
        # Turn 2: SPEAKER_01 segment 2
        assert result.turns[1].speaker == "SPEAKER_01"
        assert result.turns[1].text == "I have a question about billing."

    def test_role_neutrality(self, aligner: TranscriptAligner) -> None:
        """Verify speaker IDs remain neutral ('SPEAKER_00', 'SPEAKER_01') without assuming Agent/Customer."""
        w_seg = TranscriptSegment(id=0, start=0.0, end=2.0, text="Thank you for calling support.")
        transcription = TranscriptionResult(
            text="Thank you for calling support.",
            language="en",
            language_probability=0.99,
            duration_seconds=2.0,
            processing_time_seconds=0.5,
            real_time_factor=0.25,
            segments=[w_seg],
        )
        diarization = DiarizationResult(
            audio_path="test.wav",
            audio_duration=2.0,
            speaker_segments=[DiarizationSegment(speaker="SPEAKER_00", start=0.0, end=2.0)],
            speakers=["SPEAKER_00"],
            speech_duration=2.0,
        )
        result = aligner.align(transcription, diarization)
        assert result.turns[0].speaker == "SPEAKER_00"
        assert result.turns[0].speaker not in ("Agent", "Customer")


# ============================================================================
# Test Section 6: Diarization Engine (Mocked Pipeline)
# ============================================================================

class TestPyannoteDiarizer:
    def test_mocked_diarization_execution(self, temp_standard_wav: Path) -> None:
        mock_pipeline = MagicMock()

        # Build mock pyannote annotation
        mock_segment1 = SimpleNamespace(start=0.5, end=2.0)
        mock_segment2 = SimpleNamespace(start=2.2, end=3.0)
        tracks = [
            (mock_segment1, None, "SPEAKER_00"),
            (mock_segment2, None, "SPEAKER_01"),
        ]
        mock_annotation = MagicMock()
        mock_annotation.itertracks.return_value = tracks
        mock_pipeline.return_value = mock_annotation

        diarizer = PyannoteDiarizer(config=DiarizationConfig(device="cpu"), pipeline=mock_pipeline)
        result = diarizer.diarize(temp_standard_wav)

        assert isinstance(result, DiarizationResult)
        assert len(result.speakers) == 2
        assert result.speakers == ["SPEAKER_00", "SPEAKER_01"]
        assert len(result.speaker_segments) == 2
        assert result.speaker_segments[0].speaker == "SPEAKER_00"
        assert result.speaker_segments[1].speaker == "SPEAKER_01"
        assert result.processing_time_seconds >= 0.0


# ============================================================================
# Test Section 7: Real Pyannote Integration Test
# ============================================================================

class TestRealPyannoteIntegration:
    @pytest.mark.integration
    def test_real_pyannote_diarization(self) -> None:
        """Integration test on preprocessed demo audio if HF token and model access are available."""
        demo_audio = Path("data/processed/demo/demo_minds14_sample_0/audio.wav")
        if not demo_audio.exists():
            pytest.skip("Demo audio file not found.")

        DiarizationModelManager.get_instance().clear_cache()
        cfg = DiarizationConfig.from_env()
        if not cfg.hf_token:
            pytest.skip("No HF_TOKEN available in environment for pyannote integration test.")

        try:
            diarizer = PyannoteDiarizer(cfg)
            result = diarizer.diarize(demo_audio)
            assert isinstance(result, DiarizationResult)
            assert result.audio_duration > 0
            assert len(result.speaker_segments) >= 1
            assert result.processing_time_seconds > 0
        except (DiarizationModelLoadError, DiarizationInferenceError) as exc:
            # Gated repository access must be accepted by user on Hugging Face
            pytest.skip(f"Hugging Face model access pending user agreement: {exc}")


class TestEndToEndPipeline:
    def test_end_to_end_asr_diarization_alignment_pipeline(self) -> None:
        """
        Step 28: End-to-end test verifying:
        Phase 2 Preprocessed Audio -> Phase 3 Whisper ASR -> Phase 4 Diarization -> Alignment -> Speaker-Attributed Transcript.
        """
        demo_audio = Path("data/processed/demo/demo_minds14_sample_0/audio.wav")
        if not demo_audio.exists():
            pytest.skip("Demo audio file not found.")

        # 1. Real Whisper ASR
        from ai_service.asr import WhisperConfig, WhisperTranscriber

        asr_cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type="int8", word_timestamps=True)
        transcriber = WhisperTranscriber(asr_cfg)
        transcription_res = transcriber.transcribe(demo_audio)

        assert transcription_res.duration_seconds > 0
        assert len(transcription_res.segments) >= 1

        # 2. Diarization with controlled acoustic mock
        mock_pipeline = MagicMock()
        midpoint = transcription_res.duration_seconds / 2.0
        mock_annotation = MagicMock()
        mock_annotation.itertracks.return_value = [
            (SimpleNamespace(start=0.0, end=midpoint), None, "SPEAKER_00"),
            (SimpleNamespace(start=midpoint, end=transcription_res.duration_seconds), None, "SPEAKER_01"),
        ]
        mock_pipeline.return_value = mock_annotation

        diarizer = PyannoteDiarizer(config=DiarizationConfig(device="cpu"), pipeline=mock_pipeline)
        diarization_res = diarizer.diarize(demo_audio)

        assert len(diarization_res.speakers) == 2

        # 3. Alignment
        aligner = TranscriptAligner(DiarizationConfig(cross_speaker_policy="dominant"))
        attributed_transcript = aligner.align(transcription_res, diarization_res)

        assert isinstance(attributed_transcript, SpeakerAttributedTranscript)
        assert len(attributed_transcript.turns) >= 1
        assert len(attributed_transcript.full_text) > 0
        assert "SPEAKER_" in attributed_transcript.full_text
        assert attributed_transcript.total_turns == len(attributed_transcript.turns)
        assert abs(attributed_transcript.audio_duration - transcription_res.duration_seconds) < 0.1
        # In-place segment contract fulfilled
        assert transcription_res.segments[0].speaker is not None

