"""
MInDS-14 Dataset Module.

Provides robust, production-grade functions and typed schemas for loading,
inspecting, validating, and splitting the MInDS-14 (Multilingual Intent Detection
and Slot Filling) dataset from Hugging Face or local cache.

Dataset: PolyAI/minds14
Paper: https://arxiv.org/abs/2104.08524
License: CC BY 4.0

The MInDS-14 dataset contains audio recordings of people interacting
with an e-banking system across 14 intent classes in 14 languages.
This module focuses primarily on the en-US (English) subset.

Key Capabilities:
- Explicit, configurable dataset loading (cache directory, offline, data directory)
- Strongly typed schema reports (dataclasses) for classes, missing data, duplicates, and audio
- Fine-grained intent distribution with counts, frequencies, and percentages
- Comprehensive missing value analysis (audio, text, labels, total invalid rows)
- Duplicate transcription detection with duplicate percentages
- Audio metadata validation (duration stats, channels, sample rate, direct header vs decoded array)
- Stratified train/val/test split preparation without data leakage
- Reusable validation engine with structured error and warning reporting
- Complete programmatic inspection summary
"""

from __future__ import annotations

import io
import logging
import os
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from datasets import Audio, Dataset, DatasetDict, Features, load_dataset, load_from_disk

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("ai_call_analytics.datasets.minds14")


# ============================================================================
# Constants & Defaults
# ============================================================================
DATASET_NAME = "PolyAI/minds14"
DEFAULT_SUBSET = "en-US"
DATASET_LICENSE = "CC BY 4.0"
DATASET_PAPER = "https://arxiv.org/abs/2104.08524"
REQUIRED_COLUMNS = ("audio", "transcription", "intent_class")


# ============================================================================
# Custom Exceptions
# ============================================================================
class MInDS14Error(Exception):
    """Base exception for MInDS-14 dataset operations."""


class MInDS14LoadError(MInDS14Error):
    """Raised when the MInDS-14 dataset cannot be loaded or located."""


class MInDS14ValidationError(MInDS14Error):
    """Raised when MInDS-14 dataset validation fails."""


class MInDS14ConfigError(MInDS14Error):
    """Raised when dataset configuration or split parameters are invalid."""


# ============================================================================
# Structured Schema Models (Dataclasses)
# ============================================================================
@dataclass(frozen=True)
class ClassDistributionItem:
    """Individual intent class count, relative frequency, and percentage."""

    label_id: int
    label_name: str
    count: int
    frequency: float
    percentage: float


@dataclass
class ClassDistributionReport:
    """Class distribution for a dataset split."""

    split: str
    total_samples: int
    classes: dict[str, ClassDistributionItem] = field(default_factory=dict)

    def to_counts(self) -> dict[str, int]:
        """Return label_name -> count mapping for backward compatibility."""
        return {name: item.count for name, item in self.classes.items()}

    def to_percentages(self) -> dict[str, float]:
        """Return label_name -> percentage mapping."""
        return {name: item.percentage for name, item in self.classes.items()}

    def to_frequencies(self) -> dict[str, float]:
        """Return label_name -> frequency mapping."""
        return {name: item.frequency for name, item in self.classes.items()}

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary."""
        return {
            "split": self.split,
            "total_samples": self.total_samples,
            "classes": {k: asdict(v) for k, v in self.classes.items()},
            "counts": self.to_counts(),
            "percentages": self.to_percentages(),
        }


@dataclass
class MissingDataReport:
    """Detailed audit of missing and invalid values in a dataset split."""

    split: str
    total_samples: int
    audio_missing: int = 0
    text_missing: int = 0
    label_missing: int = 0
    total_invalid_rows: int = 0
    per_column_missing: dict[str, int] = field(default_factory=dict)
    per_column_percentage: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary."""
        return asdict(self)


@dataclass
class DuplicateDataReport:
    """Detailed audit of duplicate transcriptions in a dataset split."""

    split: str
    column: str | None
    total_records: int
    non_empty_records: int
    unique_records: int
    duplicate_records: int
    duplicate_percentage: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary."""
        return asdict(self)


@dataclass
class AudioMetadataReport:
    """Audio metadata and duration statistics across a dataset split."""

    split: str
    count_with_audio: int
    count_missing_audio: int
    sampling_rate: int | None
    num_channels: int | None
    audio_format: str | None
    metadata_source: str  # 'direct_header' or 'decoded_array'
    min_duration_seconds: float
    max_duration_seconds: float
    mean_duration_seconds: float
    median_duration_seconds: float
    total_duration_seconds: float
    total_duration_minutes: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary."""
        return asdict(self)


@dataclass
class SplitInfo:
    """Partition statistics for train, validation, and test splits."""

    train_count: int
    val_count: int
    test_count: int
    total_count: int
    train_percentage: float
    val_percentage: float
    test_percentage: float
    stratified_by: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary."""
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of dataset validation checks."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize validation result to a dictionary."""
        return asdict(self)


@dataclass
class DatasetSummary:
    """Comprehensive structured summary of the MInDS-14 dataset."""

    name: str
    subset: str
    huggingface_id: str
    license: str
    paper: str
    splits: dict[str, int]
    columns: list[str]
    features: dict[str, str]
    intent_labels: list[str]
    num_intent_classes: int
    class_distribution: dict[str, dict[str, Any]]
    missing_values: dict[str, dict[str, Any]]
    duplicates: dict[str, dict[str, Any]]
    audio_statistics: dict[str, dict[str, Any]]
    validation: dict[str, Any]
    split_info: dict[str, Any] | None = None
    audio_info_sample: dict[str, Any] | None = None
    sample_transcription: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize summary to a dictionary."""
        return asdict(self)


# ============================================================================
# Dataset Loading
# ============================================================================
def load_minds14(
    subset: str = DEFAULT_SUBSET,
    split: str | None = None,
    decode_audio: bool = False,
    cache_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
    download_mode: str | None = None,
    token: str | None = None,
) -> DatasetDict | Dataset:
    """
    Load the MInDS-14 dataset from Hugging Face or a local directory.

    Args:
        subset: Language subset to load (default: "en-US").
        split: Specific split to load ("train", etc.).
               If None, returns all splits as a DatasetDict.
        decode_audio: If False (default), retains raw audio bytes to prevent
                      unnecessary memory overhead and external decoder dependencies.
                      Use decode_audio_array() to decode individual samples on demand.
        cache_dir: Optional custom cache directory. Defaults to MINDS14_CACHE_DIR
                   or HF_HOME environment variables if set.
        data_dir: Optional path to a local directory previously saved via
                  save_to_disk(). If provided and exists, loads from disk.
        download_mode: Optional Hugging Face download mode (e.g. "reuse_dataset_if_exists").
        token: Optional Hugging Face access token. Defaults to HF_TOKEN or
               HUGGINGFACE_TOKEN environment variables.

    Returns:
        DatasetDict if split is None, or a single Dataset split.

    Raises:
        MInDS14LoadError: If the dataset cannot be downloaded, located, or loaded.
    """
    resolved_cache = (
        str(cache_dir)
        if cache_dir
        else os.environ.get("MINDS14_CACHE_DIR") or os.environ.get("HF_HOME")
    )
    resolved_token = (
        token
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )

    logger.info(
        "Loading MInDS-14 dataset: subset=%s, split=%s, decode_audio=%s, cache_dir=%s, data_dir=%s",
        subset,
        split,
        decode_audio,
        resolved_cache,
        data_dir,
    )

    # Path 1: Load from local disk if specified and exists
    if data_dir is not None:
        local_path = Path(data_dir)
        if local_path.exists():
            try:
                logger.info("Loading MInDS-14 from local disk path: %s", local_path)
                ds = load_from_disk(str(local_path))
                if split is not None and isinstance(ds, DatasetDict):
                    if split not in ds:
                        raise MInDS14LoadError(
                            f"Requested split '{split}' not found in local dataset at {local_path}."
                        )
                    ds = ds[split]
                return ds
            except Exception as err:
                raise MInDS14LoadError(
                    f"Failed to load dataset from local directory '{data_dir}': {err}"
                ) from err
        else:
            raise MInDS14LoadError(
                f"Configured data_dir '{data_dir}' does not exist on disk."
            )

    # Path 2: Load via Hugging Face datasets loader
    try:
        kwargs: dict[str, Any] = {}
        if resolved_cache:
            kwargs["cache_dir"] = resolved_cache
        if download_mode:
            kwargs["download_mode"] = download_mode
        if resolved_token:
            kwargs["token"] = resolved_token

        ds = load_dataset(DATASET_NAME, subset, split=split, **kwargs)
    except Exception as err:
        logger.error(
            "Failed to load MInDS-14 dataset '%s' (subset=%s, split=%s): %s",
            DATASET_NAME,
            subset,
            split,
            err,
        )
        raise MInDS14LoadError(
            f"Failed to load MInDS-14 dataset '{DATASET_NAME}' (subset='{subset}', split='{split}'). "
            f"Please verify network access, Hugging Face credentials, or specify a valid local data_dir. "
            f"Original error: {err}"
        ) from err

    # Handle undecoded audio column casting
    if not decode_audio:
        if isinstance(ds, DatasetDict):
            ds = DatasetDict({
                k: v.cast_column("audio", Audio(decode=False))
                if "audio" in v.column_names
                else v
                for k, v in ds.items()
            })
        elif "audio" in ds.column_names:
            ds = ds.cast_column("audio", Audio(decode=False))

    if isinstance(ds, DatasetDict):
        for split_name, split_ds in ds.items():
            logger.info("  Split '%s': %d examples loaded", split_name, len(split_ds))
    else:
        logger.info("  Loaded %d examples", len(ds))

    return ds


# ============================================================================
# Intent Labels & Class Distribution
# ============================================================================
def get_intent_labels(dataset: DatasetDict | Dataset) -> list[str]:
    """
    Extract intent class label names from dataset features.

    Args:
        dataset: A DatasetDict or a single Dataset split.

    Returns:
        List of intent label name strings.
    """
    if isinstance(dataset, DatasetDict):
        if not dataset:
            return []
        split_name = list(dataset.keys())[0]
        ds = dataset[split_name]
    else:
        ds = dataset

    if "intent_class" not in ds.features:
        logger.warning("No 'intent_class' feature found in dataset.")
        return []

    intent_feature = ds.features["intent_class"]
    if hasattr(intent_feature, "names") and intent_feature.names:
        return list(intent_feature.names)

    # Fallback: compute unique integer ids if ClassLabel is absent
    unique_ids = sorted(set(ds["intent_class"]))
    return [f"class_{i}" for i in unique_ids]


def analyze_class_distribution(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> ClassDistributionReport:
    """
    Compute structured intent class distribution (counts, frequencies, percentages).

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze (ignored if dataset is a single Dataset).

    Returns:
        ClassDistributionReport with fine-grained statistics.
    """
    if isinstance(dataset, DatasetDict):
        if split not in dataset:
            raise MInDS14ConfigError(f"Split '{split}' not found in dataset. Available: {list(dataset.keys())}")
        ds = dataset[split]
    else:
        ds = dataset

    labels = get_intent_labels(dataset)
    total_samples = len(ds)

    if total_samples == 0:
        return ClassDistributionReport(split=split, total_samples=0, classes={})

    intent_ids = ds["intent_class"]
    counts = Counter(intent_ids)

    classes_report: dict[str, ClassDistributionItem] = {}
    # Iterate by descending count
    for label_id, count in sorted(counts.items(), key=lambda x: -x[1]):
        label_name = labels[label_id] if label_id < len(labels) else f"unknown_{label_id}"
        frequency = count / total_samples if total_samples > 0 else 0.0
        percentage = round(frequency * 100.0, 2)
        classes_report[label_name] = ClassDistributionItem(
            label_id=label_id,
            label_name=label_name,
            count=count,
            frequency=round(frequency, 5),
            percentage=percentage,
        )

    return ClassDistributionReport(
        split=split,
        total_samples=total_samples,
        classes=classes_report,
    )


def get_class_distribution(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> dict[str, int]:
    """
    Compute intent class distribution counts for backward compatibility.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.

    Returns:
        Dict mapping intent label names to their counts, sorted descending.
    """
    report = analyze_class_distribution(dataset, split=split)
    return report.to_counts()


# ============================================================================
# Missing Value Analysis
# ============================================================================
def analyze_missing_data(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> MissingDataReport:
    """
    Analyze missing and null values for critical fields and all dataset columns.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.

    Returns:
        MissingDataReport with audio, text, label missing counts and invalid row totals.
    """
    if isinstance(dataset, DatasetDict):
        if split not in dataset:
            raise MInDS14ConfigError(f"Split '{split}' not found in dataset. Available: {list(dataset.keys())}")
        ds = dataset[split]
    else:
        ds = dataset

    total_samples = len(ds)
    if total_samples == 0:
        return MissingDataReport(split=split, total_samples=0)

    # Locate transcript column
    text_col = None
    for cand in ("transcription", "english_transcription", "text"):
        if cand in ds.column_names:
            text_col = cand
            break

    audio_missing = 0
    text_missing = 0
    label_missing = 0
    invalid_rows = 0

    for i in range(total_samples):
        example = ds[i]
        row_has_error = False

        # Audio check
        audio = example.get("audio")
        if audio is None:
            audio_missing += 1
            row_has_error = True
        elif isinstance(audio, dict):
            has_bytes = audio.get("bytes") is not None
            has_arr = audio.get("array") is not None
            has_path = bool(audio.get("path") and os.path.exists(audio["path"]))
            if not (has_bytes or has_arr or has_path):
                audio_missing += 1
                row_has_error = True
        else:
            audio_missing += 1
            row_has_error = True

        # Text check
        if text_col is not None:
            text_val = example.get(text_col)
            if text_val is None or not isinstance(text_val, str) or text_val.strip() == "":
                text_missing += 1
                row_has_error = True
        else:
            text_missing += 1
            row_has_error = True

        # Label check
        label_val = example.get("intent_class")
        if label_val is None or not isinstance(label_val, (int, np.integer)) or label_val < 0:
            label_missing += 1
            row_has_error = True

        if row_has_error:
            invalid_rows += 1

    # Per-column null analysis
    per_col_missing: dict[str, int] = {}
    per_col_pct: dict[str, float] = {}

    for col in ds.column_names:
        if col == "audio":
            null_count = audio_missing
        else:
            values = ds[col]
            null_count = sum(
                1 for v in values if v is None or (isinstance(v, str) and v.strip() == "")
            )
        per_col_missing[col] = null_count
        per_col_pct[col] = round((null_count / total_samples) * 100.0, 2)

    return MissingDataReport(
        split=split,
        total_samples=total_samples,
        audio_missing=audio_missing,
        text_missing=text_missing,
        label_missing=label_missing,
        total_invalid_rows=invalid_rows,
        per_column_missing=per_col_missing,
        per_column_percentage=per_col_pct,
    )


def check_missing_values(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> dict[str, int]:
    """
    Check for missing/null values per column (backward compatibility helper).

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.

    Returns:
        Dict mapping column name to count of missing values.
    """
    report = analyze_missing_data(dataset, split=split)
    return report.per_column_missing


# ============================================================================
# Duplicate Transcription Analysis
# ============================================================================
def analyze_duplicates(
    dataset: DatasetDict | Dataset,
    split: str = "train",
    column: str | None = None,
) -> DuplicateDataReport:
    """
    Audit duplicate or repeated transcription entries in a split.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.
        column: Optional specific column to check. Defaults to 'transcription',
                'english_transcription', or 'text'.

    Returns:
        DuplicateDataReport with total, unique, duplicate counts, and duplicate percentage.
    """
    if isinstance(dataset, DatasetDict):
        if split not in dataset:
            raise MInDS14ConfigError(f"Split '{split}' not found in dataset. Available: {list(dataset.keys())}")
        ds = dataset[split]
    else:
        ds = dataset

    total = len(ds)
    if total == 0:
        return DuplicateDataReport(
            split=split,
            column=column,
            total_records=0,
            non_empty_records=0,
            unique_records=0,
            duplicate_records=0,
            duplicate_percentage=0.0,
        )

    transcript_col = column
    if transcript_col is None:
        for col_name in ("transcription", "english_transcription", "text"):
            if col_name in ds.column_names:
                transcript_col = col_name
                break

    if transcript_col is None or transcript_col not in ds.column_names:
        return DuplicateDataReport(
            split=split,
            column=None,
            total_records=total,
            non_empty_records=0,
            unique_records=0,
            duplicate_records=0,
            duplicate_percentage=0.0,
        )

    transcripts = ds[transcript_col]
    non_empty = [t.strip() for t in transcripts if t is not None and isinstance(t, str) and t.strip() != ""]
    unique_count = len(set(non_empty))
    dup_count = len(non_empty) - unique_count
    dup_pct = round((dup_count / len(non_empty)) * 100.0, 2) if non_empty else 0.0

    return DuplicateDataReport(
        split=split,
        column=transcript_col,
        total_records=total,
        non_empty_records=len(non_empty),
        unique_records=unique_count,
        duplicate_records=dup_count,
        duplicate_percentage=dup_pct,
    )


def check_duplicate_transcriptions(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> dict[str, Any]:
    """
    Check for duplicate transcriptions in a split (backward compatibility helper).

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.

    Returns:
        Dict with column, total, non_empty, unique, duplicates, and duplicate_percentage.
    """
    report = analyze_duplicates(dataset, split=split)
    return {
        "column": report.column,
        "total": report.total_records,
        "non_empty": report.non_empty_records,
        "unique": report.unique_records,
        "duplicates": report.duplicate_records,
        "duplicate_percentage": report.duplicate_percentage,
    }


# ============================================================================
# Audio Validation & Metadata Extraction
# ============================================================================
def get_audio_info(example: dict[str, Any]) -> dict[str, Any]:
    """
    Extract audio metadata from a single dataset example.
    Supports decoded audio arrays, undecoded audio bytes, and file paths.

    Differentiates between directly available stream header metadata
    and metadata requiring in-memory array decoding.

    Args:
        example: A single row from the dataset.

    Returns:
        Dict with keys:
            sampling_rate: int | None
            duration_seconds: float | None
            num_samples: int | None
            channels: int | None
            audio_format: str | None
            metadata_source: str ("direct_header", "decoded_array", or "none")
            has_audio: bool
    """
    audio = example.get("audio")

    if audio is None:
        return {
            "sampling_rate": None,
            "duration_seconds": None,
            "num_samples": None,
            "channels": None,
            "audio_format": None,
            "metadata_source": "none",
            "has_audio": False,
        }

    # Case 1: Audio is already decoded (has 'array')
    if isinstance(audio, dict) and "array" in audio and audio["array"] is not None:
        array = audio["array"]
        sampling_rate = audio.get("sampling_rate", 8000)
        if isinstance(array, np.ndarray):
            num_samples = len(array)
            channels = 1 if array.ndim == 1 else array.shape[1]
        elif isinstance(array, list):
            num_samples = len(array)
            channels = 1
        else:
            num_samples = len(array)
            channels = 1
        duration = num_samples / sampling_rate if sampling_rate and num_samples > 0 else 0.0
        return {
            "sampling_rate": sampling_rate,
            "duration_seconds": round(duration, 3),
            "num_samples": num_samples,
            "channels": channels,
            "audio_format": "PCM_FLOAT",
            "metadata_source": "decoded_array",
            "has_audio": num_samples > 0,
        }

    # Case 2: Audio bytes present (decode=False) -> direct header read without decoding
    if isinstance(audio, dict) and "bytes" in audio and audio["bytes"] is not None:
        try:
            info = sf.info(io.BytesIO(audio["bytes"]))
            return {
                "sampling_rate": info.samplerate,
                "duration_seconds": round(info.duration, 3),
                "num_samples": info.frames,
                "channels": info.channels,
                "audio_format": info.format,
                "metadata_source": "direct_header",
                "has_audio": info.frames > 0,
            }
        except Exception as e:
            logger.warning("Failed to read audio metadata from bytes: %s", e)

    # Case 3: Local file path -> direct header read
    if isinstance(audio, dict) and "path" in audio and audio["path"] and os.path.exists(audio["path"]):
        try:
            info = sf.info(audio["path"])
            return {
                "sampling_rate": info.samplerate,
                "duration_seconds": round(info.duration, 3),
                "num_samples": info.frames,
                "channels": info.channels,
                "audio_format": info.format,
                "metadata_source": "direct_header",
                "has_audio": info.frames > 0,
            }
        except Exception as e:
            logger.warning("Failed to read audio path metadata: %s", e)

    return {
        "sampling_rate": None,
        "duration_seconds": None,
        "num_samples": None,
        "channels": None,
        "audio_format": None,
        "metadata_source": "none",
        "has_audio": False,
    }


def decode_audio_array(audio_field: dict[str, Any]) -> tuple[np.ndarray, int]:
    """
    Decode audio bytes or file path into a numpy float32 array and sampling rate.
    Uses soundfile directly, working seamlessly across all platforms without external decoders.

    Args:
        audio_field: The 'audio' field from a dataset example.

    Returns:
        Tuple of (numpy_array, sampling_rate).

    Raises:
        ValueError: If audio data cannot be decoded from the field.
    """
    if "array" in audio_field and audio_field["array"] is not None:
        return np.asarray(audio_field["array"], dtype=np.float32), audio_field.get("sampling_rate", 8000)

    audio_bytes = audio_field.get("bytes")
    if audio_bytes is not None:
        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        return data, sr

    path = audio_field.get("path")
    if path is not None and os.path.exists(path):
        data, sr = sf.read(path, dtype="float32")
        return data, sr

    raise ValueError(f"Cannot decode audio from: {list(audio_field.keys())}")


def compute_duration_stats(
    dataset: DatasetDict | Dataset,
    split: str = "train",
    sample_size: int | None = None,
) -> dict[str, Any]:
    """
    Compute comprehensive audio duration and channel statistics across a split.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.
        sample_size: Optional limit on number of examples to inspect.

    Returns:
        Dict with min, max, mean, median, total duration in seconds and minutes,
        sample rate, channels, audio format, and metadata source.
    """
    if isinstance(dataset, DatasetDict):
        if split not in dataset:
            raise MInDS14ConfigError(f"Split '{split}' not found in dataset. Available: {list(dataset.keys())}")
        ds = dataset[split]
    else:
        ds = dataset

    if sample_size is not None and sample_size < len(ds):
        ds = ds.select(range(sample_size))

    durations: list[float] = []
    sampling_rates: list[int] = []
    channels_list: list[int] = []
    formats: set[str] = set()
    sources: set[str] = set()
    missing_count = 0

    for example in ds:
        info = get_audio_info(example)
        if info["has_audio"] and info["duration_seconds"] is not None:
            durations.append(info["duration_seconds"])
            if info["sampling_rate"]:
                sampling_rates.append(info["sampling_rate"])
            if info["channels"]:
                channels_list.append(info["channels"])
            if info["audio_format"]:
                formats.add(info["audio_format"])
            if info["metadata_source"]:
                sources.add(info["metadata_source"])
        else:
            missing_count += 1

    if not durations:
        return {
            "min_seconds": 0.0,
            "max_seconds": 0.0,
            "mean_seconds": 0.0,
            "median_seconds": 0.0,
            "total_seconds": 0.0,
            "total_minutes": 0.0,
            "count_with_audio": 0,
            "count_missing_audio": missing_count,
            "sampling_rate": None,
            "num_channels": None,
            "audio_format": None,
            "metadata_source": "none",
        }

    arr = np.array(durations)
    primary_sr = Counter(sampling_rates).most_common(1)[0][0] if sampling_rates else None
    primary_ch = Counter(channels_list).most_common(1)[0][0] if channels_list else None
    primary_fmt = ", ".join(sorted(formats)) if formats else None
    primary_src = ", ".join(sorted(sources)) if sources else "unknown"

    return {
        "min_seconds": round(float(arr.min()), 3),
        "max_seconds": round(float(arr.max()), 3),
        "mean_seconds": round(float(arr.mean()), 3),
        "median_seconds": round(float(np.median(arr)), 3),
        "total_seconds": round(float(arr.sum()), 3),
        "total_minutes": round(float(arr.sum()) / 60.0, 2),
        "count_with_audio": len(durations),
        "count_missing_audio": missing_count,
        "sampling_rate": primary_sr,
        "num_channels": primary_ch,
        "audio_format": primary_fmt,
        "metadata_source": primary_src,
    }


# ============================================================================
# Train / Validation / Test Preparation
# ============================================================================
def prepare_splits(
    dataset: DatasetDict | Dataset,
    train_size: float = 0.8,
    val_size: float = 0.1,
    test_size: float = 0.1,
    seed: int = 42,
    stratify_by: str | None = "intent_class",
) -> DatasetDict:
    """
    Prepare stratified train, validation, and test splits.

    Rationale:
        The Hugging Face PolyAI/minds14 repository only distributes a single 'train'
        split containing 563 examples for en-US. To evaluate and train downstream
        speech and NLP models without data leakage, we perform a deterministic,
        stratified partition ensuring balanced intent representation across all splits.

    Args:
        dataset: A DatasetDict or single Dataset to partition.
        train_size: Proportion of data allocated to training (default: 0.8).
        val_size: Proportion of data allocated to validation (default: 0.1).
        test_size: Proportion of data allocated to testing (default: 0.1).
        seed: Random seed for deterministic reproducibility (default: 42).
        stratify_by: Column name to stratify by (default: "intent_class").

    Returns:
        DatasetDict with keys "train", "validation", and "test".

    Raises:
        MInDS14ConfigError: If split ratios do not sum to 1.0 or are negative.
    """
    if train_size <= 0 or val_size < 0 or test_size < 0:
        raise MInDS14ConfigError(
            f"Split sizes must be non-negative with train_size > 0. Got: {train_size}, {val_size}, {test_size}"
        )

    if not np.isclose(train_size + val_size + test_size, 1.0, atol=1e-5):
        raise MInDS14ConfigError(
            f"Split sizes must sum to 1.0. Got train={train_size}, val={val_size}, test={test_size} "
            f"(sum={train_size + val_size + test_size})"
        )

    # Resolve source dataset
    if isinstance(dataset, DatasetDict):
        if "train" in dataset and "validation" in dataset and "test" in dataset:
            logger.info("Dataset already contains train/validation/test splits. Returning as-is.")
            return dataset
        if "train" in dataset:
            source_ds = dataset["train"]
        else:
            first_key = list(dataset.keys())[0]
            source_ds = dataset[first_key]
    else:
        source_ds = dataset

    total_len = len(source_ds)
    if total_len == 0:
        raise MInDS14ConfigError("Cannot partition an empty dataset.")

    if val_size == 0 and test_size == 0:
        return DatasetDict({"train": source_ds})

    # Determine stratification column
    stratify_col = stratify_by if (stratify_by and stratify_by in source_ds.column_names) else None

    # Step 1: Split train vs (val + test)
    temp_size = val_size + test_size
    try:
        split_1 = source_ds.train_test_split(
            test_size=temp_size,
            stratify_by_column=stratify_col,
            seed=seed,
        )
    except Exception as err:
        logger.warning(
            "Stratified split 1 failed (%s); falling back to unstratified split.",
            err,
        )
        split_1 = source_ds.train_test_split(
            test_size=temp_size,
            stratify_by_column=None,
            seed=seed,
        )

    train_ds = split_1["train"]
    temp_ds = split_1["test"]

    # Step 2: Split temp into validation and test
    if val_size == 0:
        val_ds = source_ds.select([])  # empty
        test_ds = temp_ds
    elif test_size == 0:
        val_ds = temp_ds
        test_ds = source_ds.select([])
    else:
        second_test_ratio = test_size / temp_size
        try:
            split_2 = temp_ds.train_test_split(
                test_size=second_test_ratio,
                stratify_by_column=stratify_col,
                seed=seed,
            )
        except Exception as err:
            logger.warning(
                "Stratified split 2 failed (%s); falling back to unstratified split.",
                err,
            )
            split_2 = temp_ds.train_test_split(
                test_size=second_test_ratio,
                stratify_by_column=None,
                seed=seed,
            )
        val_ds = split_2["train"]
        test_ds = split_2["test"]

    logger.info(
        "Partitioned dataset: train=%d (%.1f%%), validation=%d (%.1f%%), test=%d (%.1f%%)",
        len(train_ds),
        (len(train_ds) / total_len) * 100.0,
        len(val_ds),
        (len(val_ds) / total_len) * 100.0,
        len(test_ds),
        (len(test_ds) / total_len) * 100.0,
    )

    return DatasetDict({
        "train": train_ds,
        "validation": val_ds,
        "test": test_ds,
    })


def get_split_info(dataset: DatasetDict) -> SplitInfo:
    """
    Extract sample counts and percentages from a DatasetDict with train/validation/test splits.

    Args:
        dataset: A DatasetDict containing train/validation/test.

    Returns:
        SplitInfo instance.
    """
    train_c = len(dataset["train"]) if "train" in dataset else 0
    val_c = len(dataset["validation"]) if "validation" in dataset else 0
    test_c = len(dataset["test"]) if "test" in dataset else 0
    total = train_c + val_c + test_c

    return SplitInfo(
        train_count=train_c,
        val_count=val_c,
        test_count=test_c,
        total_count=total,
        train_percentage=round((train_c / total) * 100.0, 2) if total else 0.0,
        val_percentage=round((val_c / total) * 100.0, 2) if total else 0.0,
        test_percentage=round((test_c / total) * 100.0, 2) if total else 0.0,
        stratified_by="intent_class",
    )


# ============================================================================
# Reusable Dataset Validation Engine
# ============================================================================
def validate_minds14(
    dataset: DatasetDict | Dataset,
    split: str | None = None,
    sample_size: int | None = None,
) -> ValidationResult:
    """
    Execute rigorous validation rules on the MInDS-14 dataset.

    Validation checks:
    1. Dataset exists and is non-empty.
    2. Required columns ('audio', 'transcription', 'intent_class') are present.
    3. Intent labels are valid integers within expected class bounds [0, 13].
    4. Audio data is readable, non-empty, and has valid sampling rate (>0) and duration (>0).
    5. Transcriptions are non-null and non-empty strings.
    6. All declared splits are non-empty.

    Args:
        dataset: A DatasetDict or single Dataset split.
        split: Optional split to validate. If None, validates all splits.
        sample_size: Optional maximum rows per split to inspect for deep audio checks.

    Returns:
        ValidationResult containing boolean valid flag, list of errors,
        list of warnings, and diagnostic statistics.
    """
    errors: list[str] = []
    warnings: list[str] = []

    splits_to_check: dict[str, Dataset] = {}
    if isinstance(dataset, DatasetDict):
        if not dataset:
            errors.append("DatasetDict is empty (contains no splits).")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        if split is not None:
            if split not in dataset:
                errors.append(f"Specified split '{split}' not found in dataset. Available: {list(dataset.keys())}")
                return ValidationResult(valid=False, errors=errors, warnings=warnings)
            splits_to_check[split] = dataset[split]
        else:
            splits_to_check = dict(dataset.items())
    elif isinstance(dataset, Dataset):
        splits_to_check[split or "default"] = dataset
    else:
        errors.append(f"Invalid dataset type: {type(dataset)}. Expected Dataset or DatasetDict.")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    total_samples_inspected = 0
    total_valid_samples = 0
    total_corrupt_audio = 0
    total_empty_transcripts = 0

    for split_name, ds in splits_to_check.items():
        split_len = len(ds)
        if split_len == 0:
            errors.append(f"Split '{split_name}' contains 0 examples (empty dataset).")
            continue

        # 1. Required column validation
        missing_cols = [c for c in ("audio", "intent_class") if c not in ds.column_names]
        has_text = any(c in ds.column_names for c in ("transcription", "english_transcription", "text"))
        if not has_text:
            missing_cols.append("transcription")

        if missing_cols:
            errors.append(f"Split '{split_name}' missing required columns: {missing_cols}")

        # 2. Label validity check
        if "intent_class" in ds.column_names:
            intent_vals = ds["intent_class"]
            labels = get_intent_labels(ds)
            max_allowed = len(labels) - 1 if labels else 13

            invalid_ids = [
                i for i, v in enumerate(intent_vals)
                if v is None or not isinstance(v, (int, np.integer)) or v < 0 or v > max_allowed
            ]
            if invalid_ids:
                errors.append(
                    f"Split '{split_name}' contains {len(invalid_ids)} rows with out-of-range or invalid intent_class IDs."
                )

            # Check for unrepresented classes
            present_classes = set(intent_vals)
            if labels and len(present_classes) < len(labels):
                missing_labels = [labels[idx] for idx in range(len(labels)) if idx not in present_classes]
                warnings.append(
                    f"Split '{split_name}' has 0 samples for intent classes: {missing_labels}"
                )

        # 3. Audio & text deep validation
        inspect_count = min(split_len, sample_size) if sample_size is not None else split_len
        total_samples_inspected += inspect_count

        split_corrupt_audio = 0
        split_empty_text = 0

        # Text column resolution
        text_column = None
        for cand in ("transcription", "english_transcription", "text"):
            if cand in ds.column_names:
                text_column = cand
                break

        for i in range(inspect_count):
            row = ds[i]
            row_is_valid = True

            # Audio check
            if "audio" in ds.column_names:
                info = get_audio_info(row)
                if not info["has_audio"] or not info["duration_seconds"] or info["duration_seconds"] <= 0:
                    split_corrupt_audio += 1
                    row_is_valid = False

            # Text check
            if text_column is not None:
                txt = row.get(text_column)
                if txt is None or not isinstance(txt, str) or txt.strip() == "":
                    split_empty_text += 1

            if row_is_valid:
                total_valid_samples += 1

        if split_corrupt_audio > 0:
            errors.append(f"Split '{split_name}' has {split_corrupt_audio} records with invalid/unreadable audio.")

        if split_empty_text > 0:
            warnings.append(f"Split '{split_name}' has {split_empty_text} records with empty transcriptions.")

        total_corrupt_audio += split_corrupt_audio
        total_empty_transcripts += split_empty_text

    is_valid = len(errors) == 0

    stats = {
        "is_valid": is_valid,
        "splits_checked": list(splits_to_check.keys()),
        "total_samples_inspected": total_samples_inspected,
        "total_valid_samples": total_valid_samples,
        "corrupt_audio_count": total_corrupt_audio,
        "empty_transcripts_count": total_empty_transcripts,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }

    logger.info(
        "MInDS-14 Validation finished: valid=%s, errors=%d, warnings=%d",
        is_valid,
        len(errors),
        len(warnings),
    )

    return ValidationResult(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        statistics=stats,
    )


# ============================================================================
# Dataset Summary & Inspection Orchestration
# ============================================================================
def inspect_minds14(
    dataset: DatasetDict | Dataset,
    subset: str = DEFAULT_SUBSET,
    validate: bool = True,
) -> DatasetSummary:
    """
    Generate a complete, structured DatasetSummary object.

    Args:
        dataset: A DatasetDict or single Dataset split.
        subset: Language subset (default: 'en-US').
        validate: Whether to run deep dataset validation checks.

    Returns:
        Strongly typed DatasetSummary instance.
    """
    if isinstance(dataset, Dataset):
        ds_dict = DatasetDict({"train": dataset})
    else:
        ds_dict = dataset

    splits_info = {name: len(ds) for name, ds in ds_dict.items()}
    first_split = list(ds_dict.keys())[0] if ds_dict else "train"
    sample_ds = ds_dict[first_split] if ds_dict else None

    cols = sample_ds.column_names if sample_ds else []
    feats = {k: str(v) for k, v in sample_ds.features.items()} if sample_ds else {}
    labels = get_intent_labels(ds_dict)

    # Class distributions
    class_dists: dict[str, dict[str, Any]] = {}
    missing_reports: dict[str, dict[str, Any]] = {}
    duplicate_reports: dict[str, dict[str, Any]] = {}
    audio_stats: dict[str, dict[str, Any]] = {}

    for split_name in ds_dict:
        class_dists[split_name] = analyze_class_distribution(ds_dict, split=split_name).to_dict()
        missing_reports[split_name] = analyze_missing_data(ds_dict, split=split_name).to_dict()
        duplicate_reports[split_name] = analyze_duplicates(ds_dict, split=split_name).to_dict()
        audio_stats[split_name] = compute_duration_stats(ds_dict, split=split_name)

    # Validation
    val_res = validate_minds14(ds_dict).to_dict() if validate else {"valid": True, "skipped": True}

    # Split info if train/val/test are present
    split_meta = None
    if "train" in ds_dict and "validation" in ds_dict and "test" in ds_dict:
        split_meta = get_split_info(ds_dict).to_dict()

    # First example sample info
    sample_audio_info = None
    sample_transcript = None
    if sample_ds and len(sample_ds) > 0:
        first_example = sample_ds[0]
        sample_audio_info = get_audio_info(first_example)
        for cand in ("transcription", "english_transcription", "text"):
            if cand in sample_ds.column_names:
                sample_transcript = first_example.get(cand)
                break

    return DatasetSummary(
        name="MInDS-14",
        subset=subset,
        huggingface_id=DATASET_NAME,
        license=DATASET_LICENSE,
        paper=DATASET_PAPER,
        splits=splits_info,
        columns=cols,
        features=feats,
        intent_labels=labels,
        num_intent_classes=len(labels),
        class_distribution=class_dists,
        missing_values=missing_reports,
        duplicates=duplicate_reports,
        audio_statistics=audio_stats,
        validation=val_res,
        split_info=split_meta,
        audio_info_sample=sample_audio_info,
        sample_transcription=sample_transcript,
    )


def get_dataset_summary(dataset: DatasetDict | Dataset) -> dict[str, Any]:
    """
    Generate comprehensive summary dictionary for the MInDS-14 dataset.
    Maintains 100% backward compatibility with existing tests and scripts.

    Args:
        dataset: A DatasetDict or single Dataset split.

    Returns:
        Dict containing all inspection, validation, and schema results.
    """
    summary_obj = inspect_minds14(dataset)
    d = summary_obj.to_dict()

    # Provide direct top-level backward-compatible keys
    d["column_names"] = summary_obj.columns
    # Provide simple count dicts for class_distribution per split
    d["class_distribution"] = {
        split_name: analyze_class_distribution(dataset, split=split_name).to_counts()
        for split_name in summary_obj.splits
    }
    # Provide sample transcription if present
    if summary_obj.sample_transcription is not None:
        d["sample_transcription"] = summary_obj.sample_transcription

    return d
