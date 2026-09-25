#!/usr/bin/env python3
"""
AI Call Analytics — Theme Discovery CLI Tool (Phase 7).

Discovers recurring customer conversation topics using UMAP dimensionality reduction,
HDBSCAN density-based clustering, c-TF-IDF keyword extraction, and cluster statistics.

Usage:
    python scripts/discover_themes.py --demo
    python scripts/discover_themes.py --demo --output output/themes.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_service.clustering import (
    ThemeDiscoveryConfig,
    ThemeDiscoveryService,
)
from ai_service.embeddings import EmbeddingModelManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.discover_themes")


def generate_demo_corpus() -> tuple[list[str], list[dict]]:
    """
    Generate a diverse collection of banking dialogue chunks covering distinct topics
    plus outlier noise to demonstrate UMAP + HDBSCAN clustering.
    """
    topic_templates = {
        "card_freeze": [
            "My debit card was blocked at the store and I need to unfreeze it.",
            "Can you remove the security hold on my credit card so I can make a payment?",
            "My card is frozen and declined when purchasing online yesterday.",
            "Please unblock my Visa card, I was traveling and it got restricted.",
            "Card transactions are not going through because of an account freeze.",
            "I tried to use my card three times and it is completely locked.",
        ],
        "business_loan": [
            "I am applying for a commercial real estate business loan for my company.",
            "What are the interest rates and payback terms for a small business loan?",
            "We need commercial financing for warehouse expansion and equipment.",
            "Can I speak with a commercial loan specialist about lines of credit?",
            "Looking to refinance my business mortgage loan with Apex Bank.",
            "Do I need three years of financial statements to qualify for a business loan?",
        ],
        "account_balance": [
            "Could you please tell me what my checking account balance is right now?",
            "I want to check my available funds and current savings balance.",
            "How much money is left in my primary checking account?",
            "What is my balance after the recent direct debit cleared?",
            "Can you verify the funds available on my account statement?",
            "Checking my balance to make sure my paycheck direct deposit arrived.",
        ],
        "wire_delay": [
            "I initiated an international wire transfer to Europe that has not arrived.",
            "The recipient states they have not received the bank wire sent on Monday.",
            "Can you track the SWIFT confirmation code for my outgoing foreign wire?",
            "Why is my wire transfer taking more than three business days to settle?",
            "Checking on the status of a delayed domestic wire transfer to another bank.",
            "My client is asking why the wire payment is still pending in their account.",
        ],
        "noise_outliers": [
            "What time does the downtown branch close its lobby on Saturdays?",
            "The parking lot outside the main bank office was full this morning.",
            "I like the blue color of your new mobile app icon on my phone.",
        ],
    }

    texts: list[str] = []
    metadata: list[dict] = []
    chunk_counter = 1

    for topic_key, examples in topic_templates.items():
        intent_label = topic_key if topic_key != "noise_outliers" else "general_inquiry"
        for idx, text in enumerate(examples, 1):
            call_id = f"call_{topic_key}_{idx:02d}"
            texts.append(text)
            metadata.append({
                "chunk_id": chunk_counter,
                "call_id": call_id,
                "speaker_ids": ["SPEAKER_01"],
                "start": 0.0,
                "end": 8.0,
                "text": text,
                "metadata": {
                    "intent": intent_label,
                    "sentiment": "NEGATIVE" if "freeze" in topic_key or "delay" in topic_key else "NEUTRAL",
                },
            })
            chunk_counter += 1

    return texts, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Call Analytics — Theme Discovery CLI Tool")
    parser.add_argument("--demo", action="store_true", help="Execute theme discovery on realistic banking calls")
    parser.add_argument("--min-cluster-size", type=int, default=4, help="HDBSCAN min cluster size (default: 4)")
    parser.add_argument("--output", type=str, help="Path to save output JSON")

    args = parser.parse_args()

    if not args.demo:
        parser.print_help()
        sys.exit(1)

    logger.info("Generating realistic banking conversation corpus...")
    texts, metadata = generate_demo_corpus()
    logger.info("Corpus generated: %d chunks across distinct banking topics + outliers.", len(texts))

    # Generate real vector embeddings using Phase 6 EmbeddingModelManager
    logger.info("Computing real text embeddings using sentence-transformers/all-MiniLM-L6-v2...")
    manager = EmbeddingModelManager()
    vectors = manager.embed_batch(texts)
    logger.info("Generated %d real embeddings (dimension=%d).", len(vectors), len(vectors[0]))

    # Configure ThemeDiscoveryService
    config = ThemeDiscoveryConfig(
        min_embeddings=10,
        umap_n_neighbors=10,
        umap_n_components=5,
        hdbscan_min_cluster_size=args.min_cluster_size,
        hdbscan_min_samples=args.min_cluster_size,
    )
    service = ThemeDiscoveryService(config=config)

    logger.info("Running UMAP dimensionality reduction + HDBSCAN clustering...")
    result = service.discover_themes(
        embeddings=vectors,
        metadata=metadata,
        run_name="demo_banking_themes",
    )

    # Print Formatted Report
    print("\n" + "=" * 70)
    print("AI CALL ANALYTICS — PHASE 7 THEME DISCOVERY REPORT")
    print("=" * 70)
    print(f"Run ID:            {result.run_id}")
    print(f"Config Hash:       {result.config_hash}")
    print(f"Total Chunks:      {result.embedding_count}")
    print(f"Themes Discovered: {result.cluster_count}")
    print(f"Noise Chunks:      {result.noise_count} ({result.noise_percentage:.1f}%)")
    print(f"Silhouette Score:  {result.silhouette_score:.4f}" if result.silhouette_score else "Silhouette Score:  N/A")
    print(f"Processing Time:   {result.processing_time_seconds:.3f}s")
    print("=" * 70)

    for theme in result.themes:
        print(f"\n[{theme.theme_id}] {theme.label.upper()}")
        print(f"  Cluster ID:         {theme.cluster_id}")
        print(f"  Size:               {theme.size} chunks ({theme.percentage:.1f}% of corpus)")
        print(f"  Calls Involved:     {theme.call_count} distinct calls")
        print(f"  Top Keywords:       {', '.join(theme.keywords)}")
        if theme.intent_distribution:
            print(f"  Intent Breakdown:   {theme.intent_distribution}")
        if theme.sentiment_distribution:
            print(f"  Sentiment:          {theme.sentiment_distribution}")
        print("  Representative Chunks:")
        for r_idx, rep in enumerate(theme.representative_chunks, 1):
            print(f"    {r_idx}. [{rep.call_id}] \"{rep.text}\"")

    print("\n" + "=" * 70)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info("Saved theme discovery result to %s", out_path)


if __name__ == "__main__":
    main()
