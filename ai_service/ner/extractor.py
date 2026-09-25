"""
AI Call Analytics — Named Entity Recognition Engine.

Extracts named entities from conversational call transcripts using spaCy
statistical models combined with banking-domain regex rules (Step 19, 20, 21, 22).
Maps entities to specific speaker turns and enforces strict PII logging policies (Step 23).
"""

from __future__ import annotations

import logging
import re
import threading
from collections import Counter
from typing import Any

from ai_service.diarization.schema import SpeakerTurn
from ai_service.ner.exceptions import (
    NERInferenceError,
    NERModelLoadError,
)
from ai_service.ner.schema import (
    SUPPORTED_ENTITY_LABELS,
    EntityItem,
    NERResult,
)

logger = logging.getLogger("ai_call_analytics.ner.extractor")

DEFAULT_SPACY_MODEL = "en_core_web_sm"

# Banking and communications regex patterns
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)[-.\s]?|\d{3}[-.\s])\d{3}[-.\s]\d{4}\b")
ACCOUNT_PATTERN = re.compile(r"\b(?:account|acct)\s*(?:#|no\.?|number)?\s*([0-9]{8,16})\b", re.IGNORECASE)


class EntityExtractor:
    """
    Named Entity Recognition service combining spaCy models with banking domain rules.
    """

    _cached_nlp: Any | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_name: str = DEFAULT_SPACY_MODEL,
        nlp: Any | None = None,
    ) -> None:
        """
        Initialize the entity extractor.

        Args:
            model_name: spaCy model name (defaults to 'en_core_web_sm').
            nlp: Optional pre-loaded spaCy Language instance (for DI/testing).
        """
        self.model_name = model_name
        self._nlp = nlp

    def _get_nlp(self) -> Any:
        """Retrieve spaCy language model with thread-safe singleton caching."""
        if self._nlp is not None:
            return self._nlp

        with self._lock:
            if EntityExtractor._cached_nlp is not None:
                return EntityExtractor._cached_nlp

            logger.info("Loading spaCy model: %s", self.model_name)
            try:
                import spacy
                nlp = spacy.load(self.model_name)
                EntityExtractor._cached_nlp = nlp
                return nlp
            except Exception as err:
                logger.warning("Could not load spaCy model '%s' (%s). Using blank English pipeline.", self.model_name, err)
                try:
                    import spacy
                    nlp = spacy.blank("en")
                    EntityExtractor._cached_nlp = nlp
                    return nlp
                except Exception as inner_err:
                    raise NERModelLoadError(f"Failed to initialize spaCy NLP pipeline: {inner_err}") from inner_err

    def extract_from_text(
        self,
        text: str,
        speaker: str | None = None,
        turn_id: int | None = None,
        start_id: int = 0,
    ) -> list[EntityItem]:
        """
        Extract named entities from an individual text utterance.

        Args:
            text: Utterance or conversation segment string.
            speaker: Attributed speaker identifier (e.g. 'SPEAKER_00').
            turn_id: Attributed conversational turn ID.
            start_id: Base counter for entity numbering.

        Returns:
            List of EntityItem instances with exact character offsets.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        nlp = self._get_nlp()
        entities: list[EntityItem] = []
        entity_id_counter = start_id
        occupied_spans: list[tuple[int, int]] = []

        try:
            # 1. High-precision banking domain rules (EMAIL, PHONE, ACCOUNT_NUMBER) take precedence
            for match in EMAIL_PATTERN.finditer(text):
                s, e = match.start(), match.end()
                entities.append(
                    EntityItem(
                        entity_id=entity_id_counter,
                        text=match.group(0),
                        label="EMAIL",
                        start=s,
                        end=e,
                        speaker=speaker,
                        turn_id=turn_id,
                        confidence=0.98,
                    )
                )
                occupied_spans.append((s, e))
                entity_id_counter += 1

            for match in PHONE_PATTERN.finditer(text):
                s, e = match.start(), match.end()
                if not any(max(s, os) < min(e, oe) for os, oe in occupied_spans):
                    entities.append(
                        EntityItem(
                            entity_id=entity_id_counter,
                            text=match.group(0),
                            label="PHONE",
                            start=s,
                            end=e,
                            speaker=speaker,
                            turn_id=turn_id,
                            confidence=0.95,
                        )
                    )
                    occupied_spans.append((s, e))
                    entity_id_counter += 1

            for match in ACCOUNT_PATTERN.finditer(text):
                digits = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                s = match.start(1) if match.lastindex and match.lastindex >= 1 else match.start()
                e = s + len(digits)
                if not any(max(s, os) < min(e, oe) for os, oe in occupied_spans):
                    entities.append(
                        EntityItem(
                            entity_id=entity_id_counter,
                            text=digits,
                            label="ACCOUNT_NUMBER",
                            start=s,
                            end=e,
                            speaker=speaker,
                            turn_id=turn_id,
                            confidence=0.92,
                        )
                    )
                    occupied_spans.append((s, e))
                    entity_id_counter += 1

            # 2. Statistical model extraction (spaCy) fills remaining entities without overwriting domain matches
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in SUPPORTED_ENTITY_LABELS:
                    s, e = ent.start_char, ent.end_char
                    if not any(max(s, os) < min(e, oe) for os, oe in occupied_spans):
                        entities.append(
                            EntityItem(
                                entity_id=entity_id_counter,
                                text=ent.text,
                                label=ent.label_,
                                start=s,
                                end=e,
                                speaker=speaker,
                                turn_id=turn_id,
                                confidence=0.90,
                            )
                        )
                        occupied_spans.append((s, e))
                        entity_id_counter += 1

            # Sort entities chronologically by start offset
            entities.sort(key=lambda item: (item.start, item.end))
            return entities

        except Exception as err:
            logger.error("NER extraction failed for text: %s", err)
            raise NERInferenceError(f"NER extraction failed: {err}") from err

    def extract_from_turns(self, turns: list[SpeakerTurn]) -> NERResult:
        """
        Extract entities across all conversational turns (Step 19, 21, 22).

        Returns:
            NERResult with structured EntityItem list and category counts.
        """
        all_entities: list[EntityItem] = []
        counter = 1

        for turn in turns:
            turn_ents = self.extract_from_text(
                text=turn.text,
                speaker=turn.speaker,
                turn_id=turn.turn_id,
                start_id=counter,
            )
            all_entities.extend(turn_ents)
            counter += len(turn_ents)

        # Count frequencies
        counts = dict(Counter(e.label for e in all_entities))

        # Privacy-conscious logging: Log only categories, NEVER raw PII values (Step 23, 39)
        logger.info(
            "NER completed: extracted %d entities across %d turns (counts=%s)",
            len(all_entities),
            len(turns),
            counts,
        )

        return NERResult(
            entities=all_entities,
            entity_counts=counts,
            model_name=f"spacy_{self.model_name}+banking_rules",
        )
