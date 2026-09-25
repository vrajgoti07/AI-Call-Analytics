"""
Unit and Integration tests for MInDS-14 Dataset Module.

Tests all helper, schema, inspection, validation, and loading functions in
ai_service/datasets/minds14_loader.py using synthetic data and in-memory audio buffers
to ensure fast, deterministic, and offline-capable testing, along with an optional
integration test against the actual MInDS-14 dataset.
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
    AudioMetadataReport,
    ClassDistributionReport,
    DatasetSummary,
    DuplicateDataReport,
    MInDS14ConfigError,
    MInDS14Error,
    MInDS14LoadError,
    MInDS14ValidationError,
    MissingDataReport,
    SplitInfo,
    ValidationResult,
    analyze_class_distribution,
    analyze_duplicates,
    analyze_missing_data,
    check_duplicate_transcriptions,
    check_missing_values,
    compute_duration_stats,
    decode_audio_array,
    get_audio_info,
    get_class_distribution,
    get_dataset_summary,
    get_intent_labels,
    get_split_info,
    inspect_minds14,
    load_minds14,
    prepare_splits,
    validate_minds14,
)


class TestMInDS14Loader(unittest.TestCase):
    """Test suite for MInDS-14 loader and inspection functions."""

    def setUp(self) -> None:
        """Create a synthetic dataset for deterministic testing."""
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

    # ------------------------------------------------------------------------
    # Intent labels and distribution tests
    # ------------------------------------------------------------------------
    def test_get_intent_labels(self) -> None:
        """Verify intent labels extraction from features."""
        labels = get_intent_labels(self.mock_dataset)
        self.assertEqual(labels, self.intent_names)

        labels_from_dict = get_intent_labels(self.mock_dataset_dict)
        self.assertEqual(labels_from_dict, self.intent_names)

    def test_get_class_distribution(self) -> None:
        """Verify intent distribution computation (count dict)."""
        distribution = get_class_distribution(self.mock_dataset)
        self.assertEqual(distribution["balance"], 2)
        self.assertEqual(distribution["pay_bill"], 1)
        self.assertEqual(distribution["freeze"], 1)
        self.assertEqual(sum(distribution.values()), 4)

    def test_analyze_class_distribution_structured(self) -> None:
        """Verify structured class distribution report with frequencies and percentages."""
        report = analyze_class_distribution(self.mock_dataset)
        self.assertIsInstance(report, ClassDistributionReport)
        self.assertEqual(report.total_samples, 4)
        self.assertEqual(report.split, "train")

        balance_item = report.classes["balance"]
        self.assertEqual(balance_item.count, 2)
        self.assertAlmostEqual(balance_item.frequency, 0.5, places=3)
        self.assertAlmostEqual(balance_item.percentage, 50.0, places=1)

        pay_bill_item = report.classes["pay_bill"]
        self.assertEqual(pay_bill_item.count, 1)
        self.assertAlmostEqual(pay_bill_item.percentage, 25.0, places=1)

        # Total frequencies should sum to 1.0
        total_freq = sum(item.frequency for item in report.classes.values())
        self.assertAlmostEqual(total_freq, 1.0, places=3)

    # ------------------------------------------------------------------------
    # Audio metadata tests
    # ------------------------------------------------------------------------
    def test_get_audio_info_from_bytes(self) -> None:
        """Verify audio metadata parsing directly from raw bytes header without array decoding."""
        example = {"audio": {"bytes": self.wav_bytes, "path": "test.wav"}}
        info = get_audio_info(example)

        self.assertTrue(info["has_audio"])
        self.assertEqual(info["sampling_rate"], 8000)
        self.assertEqual(info["num_samples"], 8000)
        self.assertEqual(info["channels"], 1)
        self.assertEqual(info["audio_format"], "WAV")
        self.assertEqual(info["metadata_source"], "direct_header")
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
        self.assertEqual(info["channels"], 1)
        self.assertEqual(info["metadata_source"], "decoded_array")
        self.assertAlmostEqual(info["duration_seconds"], 1.0, places=2)

    def test_get_audio_info_missing(self) -> None:
        """Verify audio metadata handling when audio is absent."""
        info = get_audio_info({"audio": None})
        self.assertFalse(info["has_audio"])
        self.assertIsNone(info["sampling_rate"])
        self.assertEqual(info["metadata_source"], "none")

    def test_decode_audio_array(self) -> None:
        """Verify decoding audio bytes to numpy float array."""
        audio_field = {"bytes": self.wav_bytes, "path": "test.wav"}
        arr, sr = decode_audio_array(audio_field)

        self.assertEqual(sr, 8000)
        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(len(arr), 8000)
        self.assertEqual(arr.dtype, np.float32)

    def test_compute_duration_stats(self) -> None:
        """Verify duration aggregation statistics and audio format details."""
        stats = compute_duration_stats(self.mock_dataset)

        self.assertEqual(stats["count_with_audio"], 3)
        self.assertEqual(stats["count_missing_audio"], 1)
        self.assertEqual(stats["num_channels"], 1)
        self.assertEqual(stats["audio_format"], "WAV")
        self.assertEqual(stats["metadata_source"], "direct_header")
        self.assertAlmostEqual(stats["min_seconds"], 1.0, places=2)
        self.assertAlmostEqual(stats["max_seconds"], 1.0, places=2)
        self.assertAlmostEqual(stats["mean_seconds"], 1.0, places=2)
        self.assertAlmostEqual(stats["total_seconds"], 3.0, places=2)

    # ------------------------------------------------------------------------
    # Missing data tests
    # ------------------------------------------------------------------------
    def test_check_missing_values(self) -> None:
        """Verify missing/empty value detection across columns."""
        missing = check_missing_values(self.mock_dataset)

        self.assertEqual(missing["path"], 0)
        self.assertEqual(missing["audio"], 1)  # 1 example has None bytes
        self.assertEqual(missing["transcription"], 1)  # 1 example has empty string
        self.assertEqual(missing["intent_class"], 0)

    def test_analyze_missing_data_structured(self) -> None:
        """Verify structured missing data report (audio, text, label, total invalid rows)."""
        report = analyze_missing_data(self.mock_dataset)
        self.assertIsInstance(report, MissingDataReport)
        self.assertEqual(report.total_samples, 4)
        self.assertEqual(report.audio_missing, 1)
        self.assertEqual(report.text_missing, 1)
        self.assertEqual(report.label_missing, 0)
        # Sample 3 has both missing audio and empty text, so total invalid rows is 1
        self.assertEqual(report.total_invalid_rows, 1)
        self.assertEqual(report.per_column_percentage["audio"], 25.0)

    # ------------------------------------------------------------------------
    # Duplicate transcription tests
    # ------------------------------------------------------------------------
    def test_check_duplicate_transcriptions(self) -> None:
        """Verify detection of duplicate utterances and duplicate percentage."""
        dups = check_duplicate_transcriptions(self.mock_dataset)

        self.assertEqual(dups["total"], 4)
        self.assertEqual(dups["non_empty"], 3)
        self.assertEqual(dups["unique"], 2)  # 'check my balance' appears twice
        self.assertEqual(dups["duplicates"], 1)
        self.assertAlmostEqual(dups["duplicate_percentage"], 33.33, places=1)

    def test_analyze_duplicates_structured(self) -> None:
        """Verify structured duplicate report."""
        report = analyze_duplicates(self.mock_dataset)
        self.assertIsInstance(report, DuplicateDataReport)
        self.assertEqual(report.total_records, 4)
        self.assertEqual(report.duplicate_records, 1)
        self.assertAlmostEqual(report.duplicate_percentage, 33.33, places=1)

    # ------------------------------------------------------------------------
    # Train / Validation / Test split tests
    # ------------------------------------------------------------------------
    def test_prepare_splits_deterministic(self) -> None:
        """Verify dataset splitting into train, validation, and test partitions."""
        # Create a synthetic dataset with 30 examples (10 per class) to test stratification
        records = {
            "path": [f"audio_{i}.wav" for i in range(30)],
            "audio": [{"bytes": self.wav_bytes, "path": f"audio_{i}.wav"} for i in range(30)],
            "transcription": [f"transcription {i}" for i in range(30)],
            "intent_class": [i % 3 for i in range(30)],
        }
        features = Features({
            "path": Value("string"),
            "audio": {"bytes": Value("binary"), "path": Value("string")},
            "transcription": Value("string"),
            "intent_class": ClassLabel(names=self.intent_names),
        })
        ds = Dataset.from_dict(records, features=features)

        split_dict = prepare_splits(
            ds,
            train_size=0.8,
            val_size=0.1,
            test_size=0.1,
            seed=42,
            stratify_by="intent_class",
        )

        self.assertIn("train", split_dict)
        self.assertIn("validation", split_dict)
        self.assertIn("test", split_dict)

        self.assertEqual(len(split_dict["train"]), 24)
        self.assertEqual(len(split_dict["validation"]), 3)
        self.assertEqual(len(split_dict["test"]), 3)

        info = get_split_info(split_dict)
        self.assertEqual(info.total_count, 30)
        self.assertAlmostEqual(info.train_percentage, 80.0, places=1)
        self.assertAlmostEqual(info.val_percentage, 10.0, places=1)
        self.assertAlmostEqual(info.test_percentage, 10.0, places=1)

        # Check stratification: all 3 classes represented in validation and test
        val_classes = set(split_dict["validation"]["intent_class"])
        test_classes = set(split_dict["test"]["intent_class"])
        self.assertEqual(len(val_classes), 3)
        self.assertEqual(len(test_classes), 3)

    def test_prepare_splits_invalid_proportions(self) -> None:
        """Verify error when split ratios do not sum to 1.0."""
        with self.assertRaises(MInDS14ConfigError):
            prepare_splits(self.mock_dataset, train_size=0.7, val_size=0.1, test_size=0.1)

    # ------------------------------------------------------------------------
    # Dataset validation engine tests
    # ------------------------------------------------------------------------
    def test_validate_minds14_valid_dataset(self) -> None:
        """Verify validation passes on a well-formed clean dataset."""
        clean_records = {
            "path": ["audio_0.wav", "audio_1.wav"],
            "audio": [
                {"bytes": self.wav_bytes, "path": "audio_0.wav"},
                {"bytes": self.wav_bytes, "path": "audio_1.wav"},
            ],
            "transcription": ["check balance", "pay bill"],
            "intent_class": [0, 1],
        }
        features = Features({
            "path": Value("string"),
            "audio": {"bytes": Value("binary"), "path": Value("string")},
            "transcription": Value("string"),
            "intent_class": ClassLabel(names=["balance", "pay_bill"]),
        })
        clean_ds = Dataset.from_dict(clean_records, features=features)

        result = validate_minds14(clean_ds)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.statistics["total_valid_samples"], 2)

    def test_validate_minds14_missing_required_column(self) -> None:
        """Verify validation fails when a required column (e.g. audio) is missing."""
        invalid_records = {
            "transcription": ["test"],
            "intent_class": [0],
        }
        ds = Dataset.from_dict(invalid_records)
        result = validate_minds14(ds)
        self.assertFalse(result.valid)
        self.assertTrue(any("audio" in err for err in result.errors))

    def test_validate_minds14_invalid_label_ids(self) -> None:
        """Verify validation catches out-of-range intent class IDs."""
        bad_label_records = {
            "audio": [{"bytes": self.wav_bytes, "path": "a.wav"}],
            "transcription": ["test text"],
            "intent_class": [-5],  # Invalid negative ID
        }
        features = Features({
            "audio": {"bytes": Value("binary"), "path": Value("string")},
            "transcription": Value("string"),
            "intent_class": Value("int32"),
        })
        ds = Dataset.from_dict(bad_label_records, features=features)
        result = validate_minds14(ds)
        self.assertFalse(result.valid)
        self.assertTrue(any("intent_class" in err for err in result.errors))

    def test_validate_minds14_empty_dataset(self) -> None:
        """Verify validation catches empty datasets."""
        empty_ds = self.mock_dataset.select([])
        result = validate_minds14(empty_ds)
        self.assertFalse(result.valid)
        self.assertTrue(any("empty" in err for err in result.errors))

    # ------------------------------------------------------------------------
    # Summary & Inspection tests
    # ------------------------------------------------------------------------
    def test_inspect_minds14_structured(self) -> None:
        """Verify inspect_minds14 returns typed DatasetSummary."""
        summary = inspect_minds14(self.mock_dataset_dict)
        self.assertIsInstance(summary, DatasetSummary)
        self.assertEqual(summary.name, "MInDS-14")
        self.assertEqual(summary.license, DATASET_LICENSE)
        self.assertEqual(summary.num_intent_classes, 3)
        self.assertIn("train", summary.splits)
        self.assertEqual(summary.splits["train"], 4)
        self.assertIn("train", summary.class_distribution)
        self.assertIn("train", summary.missing_values)
        self.assertIn("train", summary.duplicates)
        self.assertIn("train", summary.audio_statistics)

    def test_get_dataset_summary_backward_compatibility(self) -> None:
        """Verify get_dataset_summary maintains existing dictionary contract."""
        summary = get_dataset_summary(self.mock_dataset_dict)

        self.assertEqual(summary["name"], "MInDS-14")
        self.assertEqual(summary["license"], DATASET_LICENSE)
        self.assertEqual(summary["num_intent_classes"], 3)
        self.assertIn("train", summary["splits"])
        self.assertEqual(summary["splits"]["train"], 4)
        self.assertIn("train", summary["class_distribution"])
        self.assertEqual(summary["class_distribution"]["train"]["balance"], 2)

    # ------------------------------------------------------------------------
    # Dataset Loader tests (mocked & error handling)
    # ------------------------------------------------------------------------
    @patch("ai_service.datasets.minds14_loader.load_dataset")
    def test_load_minds14_success(self, mock_load: MagicMock) -> None:
        """Verify load_minds14 calls load_dataset with configured arguments."""
        mock_load.return_value = self.mock_dataset_dict

        ds = load_minds14(subset="en-US", split="train", cache_dir="custom_cache")
        self.assertIsNotNone(ds)
        mock_load.assert_called_once()
        _, kwargs = mock_load.call_args
        self.assertEqual(kwargs.get("cache_dir"), "custom_cache")

    def test_load_minds14_missing_local_data_dir(self) -> None:
        """Verify load_minds14 raises MInDS14LoadError when data_dir does not exist."""
        with self.assertRaises(MInDS14LoadError):
            load_minds14(data_dir="non_existent_directory_99999")

    @patch("ai_service.datasets.minds14_loader.load_dataset")
    def test_load_minds14_wraps_hf_exception(self, mock_load: MagicMock) -> None:
        """Verify unhandled load exceptions are wrapped in MInDS14LoadError."""
        mock_load.side_effect = RuntimeError("Hugging Face Connection Refused")
        with self.assertRaises(MInDS14LoadError) as ctx:
            load_minds14(subset="en-US")
        self.assertIn("Failed to load MInDS-14 dataset", str(ctx.exception))


class TestMInDS14RealDatasetIntegration(unittest.TestCase):
    """
    Integration tests against the real MInDS-14 dataset.
    Exercises real loading, full dataset schema, validation, and stratified splitting.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Attempt to load real MInDS-14 en-US dataset if locally cached or network available."""
        try:
            cls.real_dataset = load_minds14(subset="en-US", split="train")
        except Exception as e:
            cls.real_dataset = None
            cls.skip_reason = f"Real MInDS-14 dataset unavailable: {e}"

    def test_real_dataset_integrity(self) -> None:
        """Validate the full 563-sample real MInDS-14 dataset."""
        if self.real_dataset is None:
            self.skipTest(self.skip_reason)

        self.assertEqual(len(self.real_dataset), 563)
        self.assertIn("audio", self.real_dataset.column_names)
        self.assertIn("transcription", self.real_dataset.column_names)
        self.assertIn("intent_class", self.real_dataset.column_names)

        labels = get_intent_labels(self.real_dataset)
        self.assertEqual(len(labels), 14)

        # Validate with validation engine
        val_result = validate_minds14(self.real_dataset)
        self.assertTrue(val_result.valid, f"Validation failed: {val_result.errors}")

    def test_real_dataset_stratified_split(self) -> None:
        """Validate 80/10/10 stratified train/val/test splitting on real dataset."""
        if self.real_dataset is None:
            self.skipTest(self.skip_reason)

        splits = prepare_splits(self.real_dataset, train_size=0.8, val_size=0.1, test_size=0.1, seed=42)
        self.assertEqual(len(splits["train"]), 450)
        self.assertEqual(len(splits["validation"]), 56)
        self.assertEqual(len(splits["test"]), 57)

        # Ensure all 14 classes are represented in validation and test
        val_classes = set(splits["validation"]["intent_class"])
        test_classes = set(splits["test"]["intent_class"])
        self.assertEqual(len(val_classes), 14)
        self.assertEqual(len(test_classes), 14)


if __name__ == "__main__":
    unittest.main()
