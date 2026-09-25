"""
AI Call Analytics — Conversational NLP Pipeline Orchestrator.

Coordinates Sentiment Analysis, Intent Classification, and Named Entity Recognition
over Phase 4 speaker-attributed transcripts. Enforces error isolation, language
validation, multi-level speaker aggregation, and PII-safe logging.
"""

from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from typing import Any

from ai_service.diarization.schema import SpeakerAttributedTranscript
from ai_service.intent.classifier import IntentClassifier
from ai_service.intent.schema import IntentPrediction
from ai_service.ner.extractor import EntityExtractor
from ai_service.ner.schema import NERResult
from ai_service.pipeline.schema import (
    AnalysisStatus,
    CallNLPAnalysis,
    ComponentMetadata,
    ComponentStatus,
    NLPAnalysisMetadata,
    SpeakerAnalysisSummary,
)
from ai_service.sentiment.analyzer import SentimentAnalyzer
from ai_service.sentiment.schema import CallSentiment

logger = logging.getLogger("ai_call_analytics.pipeline.nlp_analyzer")

SUPPORTED_LANGUAGES = {"en", "english", "en-us", "en-gb", "en-au", "en-ca"}


class NLPAnalyzer:
    """
    Unified Phase 5 Orchestrator.

    Consumes a SpeakerAttributedTranscript from Phase 4 and produces a complete,
    structured CallNLPAnalysis object with error isolation across modules.
    """

    def __init__(
        self,
        sentiment_analyzer: SentimentAnalyzer | None = None,
        intent_classifier: IntentClassifier | None = None,
        entity_extractor: EntityExtractor | None = None,
    ) -> None:
        """
        Initialize the NLP Analyzer orchestrator.

        Args:
            sentiment_analyzer: Optional pre-configured SentimentAnalyzer instance.
            intent_classifier: Optional pre-configured IntentClassifier instance.
            entity_extractor: Optional pre-configured EntityExtractor instance.
        """
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.entity_extractor = entity_extractor or EntityExtractor()

    def analyze(
        self,
        transcript: SpeakerAttributedTranscript,
        top_k_intents: int = 3,
    ) -> CallNLPAnalysis:
        """
        Execute comprehensive NLP analysis on a speaker-attributed transcript.

        Args:
            transcript: Structured SpeakerAttributedTranscript from Phase 4.
            top_k_intents: Number of top candidate intents to retain.

        Returns:
            CallNLPAnalysis with sentiment, intent, entities, speaker summaries, and audit metadata.
        """
        start_time = time.perf_counter()
        warnings: list[str] = list(transcript.warnings)
        component_statuses: dict[str, ComponentMetadata] = {}

        # 1. Multi-language validation (Step 25)
        raw_lang = transcript.transcription_metadata.get("language", "en")
        language = str(raw_lang).lower().strip() if raw_lang else "en"
        is_lang_supported = language in SUPPORTED_LANGUAGES

        logger.info(
            "Starting Phase 5 NLP analysis: turns=%d, speakers=%d, language='%s'",
            transcript.total_turns,
            len(transcript.speakers),
            language,
        )

        call_sentiment: CallSentiment | None = None
        intent_prediction: IntentPrediction | None = None
        ner_result: NERResult | None = None

        if not is_lang_supported:
            warning_msg = (
                f"Transcript language '{language}' is not officially supported by current NLP models. "
                "English ('en') is required for reliable Sentiment, Intent, and NER analysis."
            )
            logger.warning(warning_msg)
            warnings.append(warning_msg)

            for comp in ["sentiment", "intent", "ner"]:
                component_statuses[comp] = ComponentMetadata(
                    status=ComponentStatus.NOT_SUPPORTED.value,
                    error=warning_msg,
                )

            total_elapsed = time.perf_counter() - start_time
            metadata = NLPAnalysisMetadata(
                language=language,
                is_language_supported=False,
                status=AnalysisStatus.NOT_SUPPORTED.value,
                processing_time_seconds=total_elapsed,
                component_statuses=component_statuses,
                audio_duration=transcript.audio_duration,
                total_turns=transcript.total_turns,
                total_speakers=len(transcript.speakers),
                warnings=warnings,
            )
            return CallNLPAnalysis(
                sentiment=None,
                intent=None,
                entities=None,
                speaker_analysis={},
                metadata=metadata,
                warnings=warnings,
            )

        # 2. Sentiment Analysis (Component A) with Error Isolation (Step 29)
        sent_start = time.perf_counter()
        try:
            call_sentiment = self.sentiment_analyzer.analyze_turns(transcript.turns)
            sent_elapsed = time.perf_counter() - sent_start
            component_statuses["sentiment"] = ComponentMetadata(
                status=ComponentStatus.SUCCESS.value,
                model_name=getattr(self.sentiment_analyzer, "model_name", "sentiment_model"),
                processing_time_seconds=sent_elapsed,
            )
            logger.info(
                "Sentiment completed in %.3fs: label=%s, score=%.4f (neg_ratio=%.2f)",
                sent_elapsed,
                call_sentiment.label,
                call_sentiment.score,
                call_sentiment.negative_ratio,
            )
        except Exception as err:
            sent_elapsed = time.perf_counter() - sent_start
            err_msg = f"Sentiment analysis failed: {err}"
            logger.error(err_msg, exc_info=True)
            warnings.append(err_msg)
            component_statuses["sentiment"] = ComponentMetadata(
                status=ComponentStatus.FAILED.value,
                processing_time_seconds=sent_elapsed,
                error=str(err),
            )

        # 3. Intent Classification (Component B) with Error Isolation (Step 29)
        intent_start = time.perf_counter()
        try:
            # Construct text for intent classification: combine non-empty turns or use full_text
            dialogue_text = transcript.full_text.strip()
            if not dialogue_text and transcript.turns:
                dialogue_text = " ".join(t.text for t in transcript.turns if t.text.strip())

            intent_prediction = self.intent_classifier.predict(dialogue_text, top_k=top_k_intents)
            intent_elapsed = time.perf_counter() - intent_start
            component_statuses["intent"] = ComponentMetadata(
                status=ComponentStatus.SUCCESS.value,
                model_name=intent_prediction.model_name,
                processing_time_seconds=intent_elapsed,
            )
            logger.info(
                "Intent classification completed in %.3fs: predicted=%s, confidence=%.4f",
                intent_elapsed,
                intent_prediction.predicted_intent,
                intent_prediction.confidence,
            )
        except Exception as err:
            intent_elapsed = time.perf_counter() - intent_start
            err_msg = f"Intent classification failed: {err}"
            logger.error(err_msg, exc_info=True)
            warnings.append(err_msg)
            component_statuses["intent"] = ComponentMetadata(
                status=ComponentStatus.FAILED.value,
                processing_time_seconds=intent_elapsed,
                error=str(err),
            )

        # 4. Named Entity Recognition (Component C) with Error Isolation (Step 29)
        ner_start = time.perf_counter()
        try:
            ner_result = self.entity_extractor.extract_from_turns(transcript.turns)
            ner_elapsed = time.perf_counter() - ner_start
            component_statuses["ner"] = ComponentMetadata(
                status=ComponentStatus.SUCCESS.value,
                model_name=ner_result.model_name,
                processing_time_seconds=ner_elapsed,
            )
            logger.info(
                "NER completed in %.3fs: found %d entities",
                ner_elapsed,
                len(ner_result.entities),
            )
        except Exception as err:
            ner_elapsed = time.perf_counter() - ner_start
            err_msg = f"NER extraction failed: {err}"
            logger.error(err_msg, exc_info=True)
            warnings.append(err_msg)
            component_statuses["ner"] = ComponentMetadata(
                status=ComponentStatus.FAILED.value,
                processing_time_seconds=ner_elapsed,
                error=str(err),
            )

        # 5. Build Unified Speaker Analysis Summaries (Step 9 & 22)
        speaker_analysis: dict[str, SpeakerAnalysisSummary] = {}
        all_speakers = set(transcript.speakers)
        if transcript.speaker_stats:
            all_speakers.update(transcript.speaker_stats.keys())
        for turn in transcript.turns:
            all_speakers.add(turn.speaker)

        # Entity attribution map: speaker -> list of entities
        speaker_entities: dict[str, list[Any]] = defaultdict(list)
        if ner_result and ner_result.entities:
            for ent in ner_result.entities:
                if ent.speaker:
                    speaker_entities[ent.speaker].append(ent)

        for spk in sorted(all_speakers):
            stat = transcript.speaker_stats.get(spk)
            spk_sentiment = call_sentiment.speaker_sentiments.get(spk) if call_sentiment else None
            ents = speaker_entities.get(spk, [])
            ent_counts_by_type = dict(Counter(e.label for e in ents))

            pos_cnt = spk_sentiment.positive_count if spk_sentiment else 0
            neu_cnt = spk_sentiment.neutral_count if spk_sentiment else 0
            neg_cnt = spk_sentiment.negative_count if spk_sentiment else 0
            tot_turns = pos_cnt + neu_cnt + neg_cnt
            neg_ratio = (neg_cnt / tot_turns) if tot_turns > 0 else 0.0

            # Determine dominant speaker sentiment
            if spk_sentiment:
                if neg_ratio >= 0.35:
                    dom_label = "NEGATIVE"
                elif spk_sentiment.positive_ratio > spk_sentiment.neutral_ratio:
                    dom_label = "POSITIVE"
                else:
                    dom_label = "NEUTRAL"
                dom_score = spk_sentiment.average_score
            else:
                dom_label = None
                dom_score = None

            speaker_analysis[spk] = SpeakerAnalysisSummary(
                speaker=spk,
                speaking_time=stat.total_speaking_time if stat else 0.0,
                speech_percentage=stat.speech_percentage if stat else 0.0,
                sentiment_label=dom_label,
                sentiment_score=dom_score,
                positive_turns=pos_cnt,
                neutral_turns=neu_cnt,
                negative_turns=neg_cnt,
                negative_turn_ratio=neg_ratio,
                entity_count=len(ents),
                entities_by_type=ent_counts_by_type,
            )

        # 6. Overall Status Determination (Step 30)
        statuses = [m.status for m in component_statuses.values()]
        if all(s == ComponentStatus.SUCCESS.value for s in statuses):
            overall_status = AnalysisStatus.SUCCESS.value
        elif any(s == ComponentStatus.SUCCESS.value for s in statuses):
            overall_status = AnalysisStatus.PARTIAL_SUCCESS.value
        else:
            overall_status = AnalysisStatus.FAILED.value

        total_elapsed = time.perf_counter() - start_time
        logger.info(
            "Phase 5 NLP analysis finished in %.3fs: status=%s",
            total_elapsed,
            overall_status,
        )

        metadata = NLPAnalysisMetadata(
            language=language,
            is_language_supported=True,
            status=overall_status,
            processing_time_seconds=total_elapsed,
            component_statuses=component_statuses,
            audio_duration=transcript.audio_duration,
            total_turns=transcript.total_turns,
            total_speakers=len(speaker_analysis),
            warnings=warnings,
        )

        return CallNLPAnalysis(
            sentiment=call_sentiment,
            intent=intent_prediction,
            entities=ner_result,
            speaker_analysis=speaker_analysis,
            metadata=metadata,
            warnings=warnings,
        )
