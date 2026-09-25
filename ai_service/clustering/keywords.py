"""
AI Call Analytics — Theme Keyword Extractor.

Extracts cluster-distinguishing keywords using Class-based TF-IDF (c-TF-IDF)
with unigrams and bigrams, filtering conversational boilerplate (Step 18, 19).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer

from ai_service.clustering.exceptions import KeywordExtractionError

logger = logging.getLogger("ai_call_analytics.clustering.keywords")

# Conversational boilerplate words to remove from theme keywords
CONVERSATIONAL_STOPWORDS = {
    "hello", "hi", "hey", "thank", "thanks", "okay", "ok", "yes", "yeah",
    "no", "good", "morning", "afternoon", "evening", "calling", "call", "help",
    "assist", "assistance", "support", "today", "please", "sure", "customer",
    "service", "speaker", "speaker_00", "speaker_01", "speaker_02", "day",
    "wonderful", "great", "welcome", "need", "want", "like", "know", "just",
}


class ThemeKeywordExtractor:
    """
    Extracts descriptive keywords for each discovered cluster using c-TF-IDF.
    """

    def __init__(self, top_k: int = 5) -> None:
        """Initialize the keyword extractor."""
        self.top_k = top_k

    def _clean_text(self, text: str) -> str:
        """Strip speaker prefixes and non-alphanumeric noise."""
        # Remove 'SPEAKER_XX:' prefixes
        cleaned = re.sub(r"SPEAKER_\d+:\s*", " ", text, flags=re.IGNORECASE)
        # Remove numbers and punctuation
        cleaned = re.sub(r"[^A-Za-z\s]", " ", cleaned)
        return cleaned.lower()

    def extract_cluster_keywords(
        self,
        cluster_texts: dict[int, list[str]],
    ) -> dict[int, list[str]]:
        """
        Extract top-k keywords for each cluster using class-level TF-IDF.

        Args:
            cluster_texts: Mapping from cluster_id to list of chunk texts.

        Returns:
            Mapping from cluster_id to list of top keyword strings.
        """
        if not cluster_texts:
            return {}

        cluster_ids = sorted(cluster_texts.keys())
        # Combine all texts per cluster into a single document
        docs = [
            " ".join(self._clean_text(t) for t in cluster_texts[cid])
            for cid in cluster_ids
        ]

        if not any(d.strip() for d in docs):
            return {cid: [f"theme_{cid}"] for cid in cluster_ids}

        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                max_features=1000,
                sublinear_tf=True,
            )
            tfidf_matrix = vectorizer.fit_transform(docs)
            feature_names = vectorizer.get_feature_names_out()

            cluster_keywords: dict[int, list[str]] = {}

            for idx, cid in enumerate(cluster_ids):
                row = tfidf_matrix.getrow(idx).toarray().flatten()
                # Sort features by descending TF-IDF score
                top_indices = row.argsort()[::-1]

                selected_terms: list[str] = []
                for feat_idx in top_indices:
                    term = feature_names[feat_idx]
                    # Filter out conversational boilerplate
                    term_words = set(term.split())
                    if not term_words.intersection(CONVERSATIONAL_STOPWORDS) and len(term) > 2:
                        selected_terms.append(term)
                    if len(selected_terms) >= self.top_k:
                        break

                if not selected_terms:
                    selected_terms = [f"topic_{cid}"]

                cluster_keywords[cid] = selected_terms

            return cluster_keywords

        except Exception as err:
            logger.warning("TF-IDF keyword extraction encountered error (%s). Using fallback.", err)
            return {cid: [f"theme_{cid}"] for cid in cluster_ids}
