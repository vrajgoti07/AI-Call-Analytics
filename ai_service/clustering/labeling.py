"""
AI Call Analytics — Theme Label Synthesizer.

Synthesizes readable, descriptive theme titles from cluster keywords (Step 20).
Explicitly marks labels as machine-generated summaries rather than human ground truth.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ai_call_analytics.clustering.labeling")


class ThemeLabeler:
    """
    Generates human-readable theme titles from top keyword phrases.
    """

    def generate_label(self, cluster_id: int, keywords: list[str]) -> str:
        """
        Synthesize a title for a cluster from its top keywords.

        Args:
            cluster_id: Integer cluster identifier.
            keywords: List of top keyword terms.

        Returns:
            Title-cased descriptive theme string.
        """
        if not keywords:
            return f"Theme {cluster_id}"

        # Take up to 3 highest-ranking terms
        top_terms = keywords[:3]
        # Capitalize cleanly
        title_words = [t.title() for t in top_terms]
        label = " / ".join(title_words)

        return label or f"Theme {cluster_id}"
