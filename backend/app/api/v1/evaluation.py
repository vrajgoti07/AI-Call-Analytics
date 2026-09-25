"""
AI Call Analytics — AI Evaluation & Benchmark API Router.

Exposes evaluated metrics, component scorecards, and confusion matrices
from the Phase 9 evaluation run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_EVAL_FILE = _PROJECT_ROOT / "reports" / "evaluation" / "evaluation_results.json"


@router.get(
    "",
    summary="Retrieve latest AI quality benchmarks and component evaluation results",
)
def get_evaluation_results() -> dict[str, Any]:
    """
    Returns benchmark scores (WER, DER, F1, MRR, AUC) and component breakdowns
    generated during Phase 9 evaluation against MInDS-14 ground truth.
    """
    if not _EVAL_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation run results found on server.",
        )

    try:
        with open(_EVAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read evaluation report: {e}",
        )
