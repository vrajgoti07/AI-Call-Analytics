"""
AI Call Analytics — Escalation Risk Service Orchestrator.

Coordinates feature extraction, risk scoring, explainability generation,
and optional database persistence for Phase 8.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ai_service.diarization.schema import SpeakerAttributedTranscript
from ai_service.intent.schema import IntentPrediction
from ai_service.ner.schema import NERResult
from ai_service.risk.config import EscalationConfig
from ai_service.risk.exceptions import EscalationPersistenceError, EscalationRiskError
from ai_service.risk.explainer import EscalationExplainer
from ai_service.risk.extractor import EscalationFeatureExtractor
from ai_service.risk.heuristic_model import HeuristicEscalationModel
from ai_service.risk.schema import EscalationPrediction
from ai_service.risk.supervised_model import SupervisedEscalationModel

logger = logging.getLogger(__name__)


class EscalationRiskService:
    """
    Main entry point for Phase 8 Escalation Risk Detection.
    Orchestrates signal ingestion, feature engineering, model inference, and persistence.
    """

    def __init__(
        self,
        config: EscalationConfig | None = None,
        supervised_model: SupervisedEscalationModel | None = None,
    ) -> None:
        self.config = config or EscalationConfig()
        self.extractor = EscalationFeatureExtractor(self.config)
        self.heuristic_model = HeuristicEscalationModel(self.config)
        self.supervised_model = supervised_model

    def analyze(
        self,
        call_id: str,
        transcript: SpeakerAttributedTranscript | None = None,
        sentiment: Any | None = None,
        intent: IntentPrediction | None = None,
        entities: NERResult | None = None,
        themes: list[dict[str, Any]] | None = None,
        db_session: Any | None = None,
    ) -> EscalationPrediction:
        """
        Execute end-to-end escalation risk analysis on a single call.

        Args:
            call_id: Identifier for the call.
            transcript: Phase 4 speaker-attributed transcript.
            sentiment: Phase 5 sentiment evaluation.
            intent: Phase 5 intent classification.
            entities: Phase 5 named entities.
            themes: Phase 7 discovered theme memberships.
            db_session: Optional SQLAlchemy session for persisting risk records.

        Returns:
            Populated EscalationPrediction contract with explainability and telemetry.
        """
        start_time = time.perf_counter()
        logger.info("Initiating escalation risk analysis for call %s (model_type=%s)", call_id, self.config.model_type)

        try:
            # 1. Feature Extraction
            features, temporal_points = self.extractor.extract(
                call_id=call_id,
                transcript=transcript,
                sentiment=sentiment,
                intent=intent,
                entities=entities,
                themes=themes,
            )

            # 2. Model Scoring
            if self.config.model_type == "supervised" and self.supervised_model is not None and self.supervised_model.is_fitted:
                prediction = self.supervised_model.predict(
                    call_id=call_id,
                    features=features,
                    temporal_risk=temporal_points,
                )
            else:
                prediction = self.heuristic_model.predict(
                    call_id=call_id,
                    features=features,
                    temporal_risk=temporal_points,
                )

            # 3. Generate Human-Readable Explanation
            prediction.explanation = EscalationExplainer.explain(prediction)

            # 4. Record execution elapsed time
            elapsed = time.perf_counter() - start_time
            prediction.processing_time_seconds = round(elapsed, 4)

            logger.info(
                "Escalation risk evaluated for call %s: score=%.1f/100, level=%s, processing_time=%.3fs",
                call_id,
                prediction.risk_score,
                prediction.risk_level.value,
                prediction.processing_time_seconds,
            )

            # 5. Optional Database Persistence
            if db_session is not None:
                self.persist(prediction, db_session)

            return prediction

        except Exception as exc:
            logger.error("Escalation analysis failed for call %s: %s", call_id, exc)
            if isinstance(exc, EscalationRiskError):
                raise
            raise EscalationRiskError(f"Escalation risk analysis failed for '{call_id}': {exc}") from exc

    def persist(self, prediction: EscalationPrediction, db_session: Any) -> None:
        """
        Persist an escalation prediction record into the PostgreSQL database.
        """
        try:
            from backend.app.models.escalation import EscalationRisk

            record = EscalationRisk(
                call_id=prediction.call_id,
                model_type=prediction.model_type,
                model_name=prediction.model_name,
                model_version=prediction.model_version,
                feature_version=prediction.feature_version,
                risk_score=prediction.risk_score,
                risk_probability=prediction.risk_probability,
                risk_level=prediction.risk_level.value,
                threshold_version=prediction.threshold_version,
                top_factors=[f.to_dict() for f in prediction.top_factors],
                explanation=prediction.explanation,
                feature_snapshot=prediction.feature_snapshot,
                temporal_risk=[t.to_dict() for t in prediction.temporal_risk],
                processing_time_seconds=prediction.processing_time_seconds,
                metadata_payload=prediction.metadata,
            )
            db_session.add(record)
            db_session.flush()
            logger.info("Persisted escalation risk record for call %s (id=%s)", prediction.call_id, record.id)
        except Exception as exc:
            logger.error("Failed to persist escalation risk record for call %s: %s", prediction.call_id, exc)
            raise EscalationPersistenceError(
                f"Failed to persist escalation risk record for call '{prediction.call_id}': {exc}"
            ) from exc
