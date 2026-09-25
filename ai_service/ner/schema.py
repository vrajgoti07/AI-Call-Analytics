"""
AI Call Analytics — Named Entity Recognition Schemas.

Defines schemas for extracted entities with character offsets, speaker attribution,
turn attribution, and aggregate entity counts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Supported core entity types across SpaCy and domain patterns
SUPPORTED_ENTITY_LABELS = {
    "PERSON",
    "ORG",
    "DATE",
    "TIME",
    "MONEY",
    "PRODUCT",
    "GPE",
    "LOC",
    "CARDINAL",
    "PERCENT",
    "EMAIL",
    "PHONE",
    "ACCOUNT_NUMBER",
}


@dataclass(frozen=True)
class EntityItem:
    """
    Extracted named entity with temporal and speaker attribution (Step 21 & 22).
    """

    entity_id: int
    text: str
    label: str  # e.g. 'PERSON', 'ORG', 'DATE', 'MONEY', 'ACCOUNT_NUMBER'
    start: int  # Character start index within the source text
    end: int    # Character end index within the source text
    speaker: str | None = None
    turn_id: int | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize entity to dictionary."""
        return {
            "entity_id": self.entity_id,
            "text": self.text,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "speaker": self.speaker,
            "turn_id": self.turn_id,
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
        }


@dataclass
class NERResult:
    """Complete Named Entity Recognition result for a call transcript."""

    entities: list[EntityItem] = field(default_factory=list)
    entity_counts: dict[str, int] = field(default_factory=dict)
    model_name: str = "spacy_en_core_web_sm+banking_rules"

    def to_dict(self) -> dict[str, Any]:
        """Serialize NER result to dictionary."""
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_counts": dict(self.entity_counts),
            "model_name": self.model_name,
        }
