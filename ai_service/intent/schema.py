"""
AI Call Analytics — Intent Classification Schemas.

Defines schemas for candidate predictions, top-k ranking, and intent results.
Uses the official MInDS-14 14-class e-banking taxonomy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# The official 14 MInDS-14 intent classes
MINDS14_INTENT_LABELS = [
    "abroad",
    "address",
    "app_error",
    "atm_limit",
    "balance",
    "business_loan",
    "card_issues",
    "cash_deposit",
    "direct_debit",
    "freeze",
    "high_value_payment",
    "joint_account",
    "latest_transactions",
    "pay_bill",
]


@dataclass(frozen=True)
class IntentCandidate:
    """Individual ranked candidate intent with posterior confidence score."""

    intent: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize candidate to dictionary."""
        return {
            "intent": self.intent,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class IntentPrediction:
    """
    Standardized Intent Classification Output Contract.
    Identifies the underlying reason/topic of the customer interaction.
    """

    predicted_intent: str
    confidence: float
    top_k: list[IntentCandidate] = field(default_factory=list)
    model_name: str = "minds14_tfidf_logistic"
    taxonomy: str = "MInDS-14"

    def to_dict(self) -> dict[str, Any]:
        """Serialize intent prediction to dictionary."""
        return {
            "predicted_intent": self.predicted_intent,
            "confidence": round(self.confidence, 4),
            "top_k": [c.to_dict() for c in self.top_k],
            "model_name": self.model_name,
            "taxonomy": self.taxonomy,
        }
