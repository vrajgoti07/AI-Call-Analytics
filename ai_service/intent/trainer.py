"""
AI Call Analytics — MInDS-14 Intent Model Training Pipeline.

Provides reproducible training and evaluation for the 14-class e-banking intent
classifier using stratified data splits, TF-IDF feature extraction, and calibrated
multinomial classification.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline

from ai_service.datasets import get_intent_labels, load_minds14, prepare_splits
from ai_service.intent.schema import MINDS14_INTENT_LABELS

logger = logging.getLogger("ai_call_analytics.intent.trainer")

DEFAULT_MODEL_DIR = Path("models/intent")
DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / "minds14_intent_model.joblib"
DEFAULT_METADATA_PATH = DEFAULT_MODEL_DIR / "model_metadata.json"


def train_minds14_intent_model(
    output_dir: Path | str = DEFAULT_MODEL_DIR,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
) -> dict[str, Any]:
    """
    Train and evaluate intent classifier on MInDS-14 dataset.

    Steps:
    1. Load full MInDS-14 en-US dataset.
    2. Split into stratified train, val, test subsets without data leakage (Step 16).
    3. Fit TF-IDF + balanced Logistic Regression pipeline.
    4. Compute evaluation metrics on held-out test split (Step 35).
    5. Save model artifact and metadata (Step 38).

    Returns:
        Dictionary of evaluation metrics and artifact paths.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading MInDS-14 en-US dataset for intent model training...")
    dataset = load_minds14(subset="en-US", split="train", decode_audio=False)

    class_names = get_intent_labels(dataset)
    if not class_names:
        class_names = MINDS14_INTENT_LABELS

    logger.info("Splitting dataset: train=%.0f%%, val=%.0f%%, test=%.0f%% (seed=%d)",
                train_ratio * 100, val_ratio * 100, test_ratio * 100, random_seed)
    splits = prepare_splits(
        dataset,
        train_size=train_ratio,
        val_size=val_ratio,
        test_size=test_ratio,
        seed=random_seed,
        stratify_by="intent_class",
    )

    train_data = splits["train"]
    val_data = splits["validation"]
    test_data = splits["test"]

    X_train = [str(t).strip() for t in train_data["transcription"]]
    y_train = [int(lbl) for lbl in train_data["intent_class"]]

    X_val = [str(t).strip() for t in val_data["transcription"]]
    y_val = [int(lbl) for lbl in val_data["intent_class"]]

    X_test = [str(t).strip() for t in test_data["transcription"]]
    y_test = [int(lbl) for lbl in test_data["intent_class"]]

    logger.info("Dataset sizes: train=%d, val=%d, test=%d", len(X_train), len(X_val), len(X_test))

    # Pipeline definition
    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=1,
                strip_accents="unicode",
            ),
        ),
        (
            "clf",
            LogisticRegression(
                C=2.5,
                max_iter=1000,
                class_weight="balanced",
                random_state=random_seed,
            ),
        ),
    ])

    logger.info("Fitting TF-IDF + LogisticRegression model...")
    model.fit(X_train, y_train)

    # Evaluate on held-out test split (Step 35)
    logger.info("Evaluating on held-out test set...")
    y_pred = model.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    prec_macro = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    f1_weighted = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "dataset": "PolyAI/minds14",
        "subset": "en-US",
        "num_classes": len(class_names),
        "class_names": class_names,
        "sample_counts": {
            "train": len(X_train),
            "val": len(X_val),
            "test": len(X_test),
        },
        "test_metrics": {
            "accuracy": round(acc, 4),
            "macro_precision": round(prec_macro, 4),
            "macro_recall": round(rec_macro, 4),
            "macro_f1": round(f1_macro, 4),
            "weighted_f1": round(f1_weighted, 4),
        },
        "model_architecture": "TfidfVectorizer(1,2) + LogisticRegression(C=2.5, balanced)",
        "confusion_matrix": cm,
    }

    # Save model artifact
    model_artifact_path = out_dir / "minds14_intent_model.joblib"
    joblib.dump({"pipeline": model, "classes": class_names}, model_artifact_path)
    logger.info("Saved trained intent model artifact to: %s", model_artifact_path)

    # Save metadata JSON
    metadata_path = out_dir / "model_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Saved model evaluation metadata to: %s", metadata_path)

    metrics["artifact_path"] = str(model_artifact_path)
    metrics["metadata_path"] = str(metadata_path)
    return metrics
