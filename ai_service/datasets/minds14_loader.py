"""
MInDS-14 Dataset Loader.

Provides reusable functions for loading and inspecting the MInDS-14
(Multilingual Intent Detection and Slot Filling) dataset from Hugging Face.

Dataset: PolyAI/minds14
Paper: https://arxiv.org/abs/2104.08524
License: CC BY 4.0

The MInDS-14 dataset contains audio recordings of people interacting
with an e-banking system across 14 intent classes in 14 languages.
This module focuses on the en-US (English) subset.

IMPORTANT:
- This module does NOT modify the original dataset.
- This module does NOT mix MInDS-14 with other datasets.
- All statistics are computed programmatically from the actual data.
- Decodes audio robustly via soundfile without requiring torchcodec.
"""

from __future__ import annotations

import io
import logging
import os
from collections import Counter
from typing import Any

import numpy as np
import soundfile as sf
from datasets import Audio, Dataset, DatasetDict, load_dataset

logger = logging.getLogger("ai_call_analytics.datasets.minds14")


# ---- Constants ----
DATASET_NAME = "PolyAI/minds14"
DEFAULT_SUBSET = "en-US"
DATASET_LICENSE = "CC BY 4.0"
DATASET_PAPER = "https://arxiv.org/abs/2104.08524"


def load_minds14(
    subset: str = DEFAULT_SUBSET,
    split: str | None = None,
    decode_audio: bool = False,
) -> DatasetDict | Dataset:
    """
    Load the MInDS-14 dataset from Hugging Face.

    Args:
        subset: Language subset to load (default: "en-US").
        split: Specific split to load ("train", etc.).
               If None, returns all splits as a DatasetDict.
        decode_audio: If False (default), retains raw audio bytes to prevent
                      unnecessary memory overhead and external decoder dependencies.
                      Use decode_audio_array() to decode individual samples on demand.

    Returns:
        DatasetDict if split is None, or a single Dataset split.

    Raises:
        Exception: If the dataset cannot be downloaded or loaded.
    """
    logger.info("Loading MInDS-14 dataset: subset=%s, split=%s, decode_audio=%s", subset, split, decode_audio)

    ds = load_dataset(DATASET_NAME, subset, split=split)

    if not decode_audio:
        if isinstance(ds, DatasetDict):
            ds = DatasetDict({
                k: v.cast_column("audio", Audio(decode=False)) if "audio" in v.column_names else v
                for k, v in ds.items()
            })
        elif "audio" in ds.column_names:
            ds = ds.cast_column("audio", Audio(decode=False))

    if isinstance(ds, DatasetDict):
        for split_name, split_ds in ds.items():
            logger.info("  %s: %d examples", split_name, len(split_ds))
    else:
        logger.info("  Loaded %d examples", len(ds))

    return ds


def get_intent_labels(dataset: DatasetDict | Dataset) -> list[str]:
    """
    Extract intent class label names from the dataset.

    Args:
        dataset: A DatasetDict or a single Dataset split.

    Returns:
        List of intent label name strings.
    """
    if isinstance(dataset, DatasetDict):
        split_name = list(dataset.keys())[0]
        ds = dataset[split_name]
    else:
        ds = dataset

    intent_feature = ds.features.get("intent_class")
    if intent_feature is None:
        logger.warning("No 'intent_class' feature found in dataset.")
        return []

    return intent_feature.names


def get_class_distribution(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> dict[str, int]:
    """
    Compute the intent class distribution for a given split.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze (ignored if dataset is a single Dataset).

    Returns:
        Dict mapping intent label names to their counts, sorted by count descending.
    """
    if isinstance(dataset, DatasetDict):
        ds = dataset[split]
    else:
        ds = dataset

    labels = get_intent_labels(dataset)
    intent_ids = ds["intent_class"]
    counts = Counter(intent_ids)

    distribution = {}
    for label_id, count in sorted(counts.items(), key=lambda x: -x[1]):
        label_name = labels[label_id] if label_id < len(labels) else f"unknown_{label_id}"
        distribution[label_name] = count

    return distribution


def get_audio_info(example: dict[str, Any]) -> dict[str, Any]:
    """
    Extract audio metadata from a single dataset example.
    Supports both decoded audio arrays and undecoded audio bytes.

    Args:
        example: A single row from the dataset.

    Returns:
        Dict with keys: sampling_rate, duration_seconds, num_samples, has_audio.
    """
    audio = example.get("audio")

    if audio is None:
        return {
            "sampling_rate": None,
            "duration_seconds": None,
            "num_samples": None,
            "has_audio": False,
        }

    # Case 1: Audio is already decoded (has 'array')
    if isinstance(audio, dict) and "array" in audio and audio["array"] is not None:
        array = audio["array"]
        sampling_rate = audio.get("sampling_rate", 8000)
        num_samples = len(array)
        duration = num_samples / sampling_rate if sampling_rate and num_samples > 0 else 0.0
        return {
            "sampling_rate": sampling_rate,
            "duration_seconds": round(duration, 3),
            "num_samples": num_samples,
            "has_audio": num_samples > 0,
        }

    # Case 2: Audio bytes present (decode=False)
    if isinstance(audio, dict) and "bytes" in audio and audio["bytes"] is not None:
        try:
            info = sf.info(io.BytesIO(audio["bytes"]))
            return {
                "sampling_rate": info.samplerate,
                "duration_seconds": round(info.duration, 3),
                "num_samples": info.frames,
                "has_audio": info.frames > 0,
            }
        except Exception as e:
            logger.warning("Failed to read audio metadata: %s", e)

    # Case 3: Local file path
    if isinstance(audio, dict) and "path" in audio and audio["path"] and os.path.exists(audio["path"]):
        try:
            info = sf.info(audio["path"])
            return {
                "sampling_rate": info.samplerate,
                "duration_seconds": round(info.duration, 3),
                "num_samples": info.frames,
                "has_audio": info.frames > 0,
            }
        except Exception as e:
            logger.warning("Failed to read audio path metadata: %s", e)

    return {
        "sampling_rate": None,
        "duration_seconds": None,
        "num_samples": None,
        "has_audio": False,
    }


def decode_audio_array(audio_field: dict[str, Any]) -> tuple[np.ndarray, int]:
    """
    Decodes audio bytes or file path into a numpy float32 array and sampling rate.
    Uses soundfile directly, working seamlessly across all platforms without torchcodec.

    Args:
        audio_field: The 'audio' field from a dataset example.

    Returns:
        Tuple of (numpy_array, sampling_rate).
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
) -> dict[str, float]:
    """
    Compute audio duration statistics across a split.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.
        sample_size: If set, analyze only this many examples (for speed).

    Returns:
        Dict with min, max, mean, median, total duration in seconds.
    """
    if isinstance(dataset, DatasetDict):
        ds = dataset[split]
    else:
        ds = dataset

    if sample_size is not None and sample_size < len(ds):
        ds = ds.select(range(sample_size))

    durations = []
    for example in ds:
        info = get_audio_info(example)
        if info["has_audio"] and info["duration_seconds"] is not None:
            durations.append(info["duration_seconds"])

    if not durations:
        return {
            "min_seconds": 0.0,
            "max_seconds": 0.0,
            "mean_seconds": 0.0,
            "median_seconds": 0.0,
            "total_seconds": 0.0,
            "total_minutes": 0.0,
            "count_with_audio": 0,
        }

    arr = np.array(durations)
    return {
        "min_seconds": round(float(arr.min()), 3),
        "max_seconds": round(float(arr.max()), 3),
        "mean_seconds": round(float(arr.mean()), 3),
        "median_seconds": round(float(np.median(arr)), 3),
        "total_seconds": round(float(arr.sum()), 3),
        "total_minutes": round(float(arr.sum()) / 60.0, 2),
        "count_with_audio": len(durations),
    }


def check_missing_values(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> dict[str, int]:
    """
    Check for missing/null values in each column of a split.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.

    Returns:
        Dict mapping column name to count of missing values.
    """
    if isinstance(dataset, DatasetDict):
        ds = dataset[split]
    else:
        ds = dataset

    missing = {}
    for col in ds.column_names:
        if col == "audio":
            null_count = 0
            for example in ds:
                audio = example.get("audio")
                if audio is None:
                    null_count += 1
                elif audio.get("array") is None and audio.get("bytes") is None:
                    null_count += 1
            missing[col] = null_count
        else:
            values = ds[col]
            null_count = sum(1 for v in values if v is None or (isinstance(v, str) and v.strip() == ""))
            missing[col] = null_count

    return missing


def check_duplicate_transcriptions(
    dataset: DatasetDict | Dataset,
    split: str = "train",
) -> dict[str, Any]:
    """
    Check for duplicate transcriptions in a split.

    Args:
        dataset: A DatasetDict or a single Dataset split.
        split: Split name to analyze.

    Returns:
        Dict with total, unique, and duplicate counts.
    """
    if isinstance(dataset, DatasetDict):
        ds = dataset[split]
    else:
        ds = dataset

    transcript_col = None
    for col_name in ["transcription", "english_transcription", "text"]:
        if col_name in ds.column_names:
            transcript_col = col_name
            break

    if transcript_col is None:
        return {
            "column": None,
            "total": len(ds),
            "unique": 0,
            "duplicates": 0,
        }

    transcripts = ds[transcript_col]
    non_empty = [t for t in transcripts if t is not None and t.strip() != ""]
    unique = set(non_empty)

    return {
        "column": transcript_col,
        "total": len(ds),
        "non_empty": len(non_empty),
        "unique": len(unique),
        "duplicates": len(non_empty) - len(unique),
    }


def get_dataset_summary(dataset: DatasetDict) -> dict[str, Any]:
    """
    Generate a comprehensive summary of the MInDS-14 dataset.

    Args:
        dataset: The loaded DatasetDict.

    Returns:
        Dict containing all inspection results.
    """
    summary: dict[str, Any] = {
        "name": "MInDS-14",
        "huggingface_id": DATASET_NAME,
        "license": DATASET_LICENSE,
        "paper": DATASET_PAPER,
    }

    # Splits
    summary["splits"] = {name: len(ds) for name, ds in dataset.items()}

    # Features
    first_split = list(dataset.keys())[0]
    ds = dataset[first_split]
    summary["features"] = {
        name: str(feat) for name, feat in ds.features.items()
    }
    summary["column_names"] = ds.column_names

    # Intent labels
    summary["intent_labels"] = get_intent_labels(dataset)
    summary["num_intent_classes"] = len(summary["intent_labels"])

    # Class distribution per split
    summary["class_distribution"] = {}
    for split_name in dataset:
        summary["class_distribution"][split_name] = get_class_distribution(
            dataset, split=split_name
        )

    # Audio info from first example
    first_example = ds[0]
    summary["audio_info_sample"] = get_audio_info(first_example)

    # Transcription sample
    for col in ["transcription", "english_transcription", "text"]:
        if col in ds.column_names:
            sample = first_example.get(col)
            summary[f"sample_{col}"] = sample

    return summary
