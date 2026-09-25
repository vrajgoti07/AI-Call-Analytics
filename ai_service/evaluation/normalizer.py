"""
AI Call Analytics — ASR Text Normalizer.

Provides standardized, documented text normalization for speech recognition evaluation.
Guarantees identical transformation of reference and hypothesis transcripts before WER/CER.
"""

from __future__ import annotations

import re


class TextNormalizer:
    """
    Standardized transcript normalization pipeline.

    Normalization Policy:
    1. Case Folding: Convert all characters to lowercase.
    2. Punctuation Removal: Strip periods, commas, question marks, exclamation marks,
       quotes, semicolons, colons, and hyphens.
    3. Whitespace Normalization: Collapse multiple tabs/spaces into single spaces; trim boundaries.
    4. Contraction Expansion / Standardization: Normalize common English contractions (e.g. "can't" -> "cannot", "i'm" -> "i am").
    """

    POLICY_DESCRIPTION: str = (
        "lowercase + punctuation_stripped + whitespace_collapsed + contractions_standardized"
    )

    CONTRACTION_MAP: dict[str, str] = {
        "can't": "cannot",
        "won't": "will not",
        "i'm": "i am",
        "it's": "it is",
        "you're": "you are",
        "they're": "they are",
        "we're": "we are",
        "don't": "do not",
        "didn't": "did not",
        "doesn't": "does not",
        "haven't": "have not",
        "hasn't": "has not",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        """
        Apply standardized text normalization.

        Args:
            text: Raw input transcript string.

        Returns:
            Clean, normalized transcript string.
        """
        if not text:
            return ""

        # 1. Lowercase
        normalized = text.lower()

        # 2. Expand common contractions
        for contraction, replacement in cls.CONTRACTION_MAP.items():
            normalized = re.sub(r"\b" + re.escape(contraction) + r"\b", replacement, normalized)

        # 3. Remove punctuation (keep alphanumeric and basic whitespace)
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # 4. Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized
