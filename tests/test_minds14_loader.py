"""
Unit tests for MInDS-14 Dataset Loader.

Tests all helper and loading functions in ai_service/datasets/minds14_loader.py
using synthetic data and in-memory audio buffers to ensure fast, deterministic,
and offline-capable testing.
"""

from __future__ import annotations

import io
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf
from datasets import ClassLabel, Dataset, DatasetDict, Features, Value

from ai_service.datasets.minds14_loader import (
    DATASET_LICENSE,
    DATASET_NAME,
    check_duplicate_transcriptions,
    check_missing_values,
    compute_duration_stats,
    decode_audio_array,
    get_audio_info,
    get_class_distribution,
    get_dataset_summary,
    get_intent_labels,
)


class TestMInDS14Loader(unittest.TestCase):
    """Test suite for MInDS-14 loader functions."""

    def setUp(self) -> None:
        """Create a synthetic dataset for testing."""
        # Create a 1-second 8000 Hz synthetic sine wave
        self.sampling_rate = 8000
        duration_s = 1.0
        t = np.linspace(0, duration_s, int(self.sampling_rate * duration_s), endpoint=False)
        self.audio_samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        # Write to in-memory WAV bytes
        buf = io.BytesIO()
        sf.write(buf, self.audio_samples, self.sampling_rate, format="WAV")
        self.wav_bytes = buf.getvalue()

        # Labels
        self.intent_names = ["balance", "pay_bill", "freeze"]

        # Synthetic records
        self.mock_records = {
            "path": ["audio_0.wav", "audio_1.wav", "audio_2.wav", "audio_3.wav"],
            "audio": [
                {"bytes": self.wav_bytes, "path": "audio_0.wav"},
                {"bytes": self.wav_bytes, "path": "audio_1.wav"},
                {"bytes": self.wav_bytes, "path": "audio_2.wav"},
                {"bytes": None, "path": None},  # Missing audio
            ],
            "transcription": [
                "check my balance",
                "pay my credit card bill",
                "check my balance",  # duplicate
                "",                  # empty transcription
            ],
            "english_transcription": [
                "check my balance",
                "pay my credit card bill",
                "check my balance",
                "",
            ],
            "intent_class": [0, 1, 0, 2],
            "lang_id": [4, 4, 4, 4],
        }

        features = Features({
            "path": Value("string"),
            "audio": {"bytes": Value("binary"), "path": Value("string")},
            "transcription": Value("string"),
            "english_transcription": Value("string"),
            "intent_class": ClassLabel(names=self.intent_names),
            "lang_id": Value("int32"),
        })

        self.mock_dataset = Dataset.from_dict(self.mock_records, features=features)
        self.mock_dataset_dict = DatasetDict({"train": self.mock_dataset})

    def test_get_intent_labels(self) -> None:
        """Verify intent labels extraction from features."""
        labels = get_intent_labels(self.mock_dataset)
        self.assertEqual(labels, self.intent_names)

        labels_from_dict = get_intent_labels(self.mock_dataset_dict)
        self.assertEqual(labels_from_dict, self.intent_names)

    def test_get_class_distribution(self) -> None:
        """Verify intent distribution computation."""
        distribution = get_class_distribution(self.mock_dataset)
        # Class 0: 2, Class 1: 1, Class 2: 1
        self.assertEqual(distribution["balance"], 2)
        self.assertEqual(distribution["pay_bill"], 1)
        self.assertEqual(distribution["freeze"], 1)
        self.assertEqual(sum(distribution.values()), 4)

    def test_get_audio_info_from_bytes(self) -> None:
        """Verify audio metadata parsing from raw bytes."""
        example = {"audio": {"bytes": self.wav_bytes, "path": "test.wav"}}
        info = get_audio_info(example)

        self.assertTrue(info["has_audio"])
        self.assertEqual(info["sampling_rate"], 8000)
        self.assertEqual(info["num_samples"], 8000)
        self.assertAlmostEqual(info["duration_seconds"], 1.0, places=2)

    def test_get_audio_info_from_array(self) -> None:
        """Verify audio metadata parsing when array is pre-decoded."""
        example = {
            "audio": {
                "array": self.audio_samples,
                "sampling_rate": 8000,
            }
        }
        info = get_audio_info(example)

        self.assertTrue(info["has_audio"])
        self.assertEqual(info["sampling_rate"], 8000)
        self.assertEqual(info["num_samples"], 8000)
        self.assertAlmostEqual(info["duration_seconds"], 1.0, places=2)

    def test_get_audio_info_missing(self) -> None:
        """Verify audio metadata handling when audio is absent."""
        info = get_audio_info({"audio": None})
        self.assertFalse(info["has_audio"])
        self.assertIsNone(info["sampling_rate"])

    def test_decode_audio_array(self) -> None:
        """Verify decoding audio bytes to numpy float array."""
        audio_field = {"bytes": self.wav_bytes, "path": "test.wav"}
        arr, sr = decode_audio_array(audio_field)

        self.assertEqual(sr, 8000)
        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(len(arr), 8000)
        self.assertEqual(arr.dtype, np.float32)

    def test_compute_duration_stats(self) -> None:
        """Verify duration aggregation statistics."""
        stats = compute_duration_stats(self.mock_dataset)

        self.assertEqual(stats["count_with_audio"], 3)
        self.assertAlmostEqual(stats["min_seconds"], 1.0, places=2)
        self.assertAlmostEqual(stats["max_seconds"], 1.0, places=2)
        self.assertAlmostEqual(stats["mean_seconds"], 1.0, places=2)
        self.assertAlmostEqual(stats["total_seconds"], 3.0, places=2)

    def test_check_missing_values(self) -> None:
        """Verify missing/empty value detection across columns."""
        missing = check_missing_values(self.mock_dataset)

        self.assertEqual(missing["path"], 0)
        self.assertEqual(missing["audio"], 1)  # 1 example has None bytes
        self.assertEqual(missing["transcription"], 1)  # 1 example has empty string
        self.assertEqual(missing["intent_class"], 0)

    def test_check_duplicate_transcriptions(self) -> None:
        """Verify detection of duplicate utterances."""
        dups = check_duplicate_transcriptions(self.mock_dataset)

        self.assertEqual(dups["total"], 4)
        self.assertEqual(dups["non_empty"], 3)
        self.assertEqual(dups["unique"], 2)  # 'check my balance' appears twice
        self.assertEqual(dups["duplicates"], 1)

    def test_get_dataset_summary(self) -> None:
        """Verify comprehensive summary structure."""
        summary = get_dataset_summary(self.mock_dataset_dict)

        self.assertEqual(summary["name"], "MInDS-14")
        self.assertEqual(summary["license"], DATASET_LICENSE)
        self.assertEqual(summary["num_intent_classes"], 3)
        self.assertIn("train", summary["splits"])
        self.assertEqual(summary["splits"]["train"], 4)


if __name__ == "__main__":
    unittest.main()
