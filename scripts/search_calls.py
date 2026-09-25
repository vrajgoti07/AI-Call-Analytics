#!/usr/bin/env python3
"""
AI Call Analytics — Semantic Vector Search CLI Tool (Phase 6).

Indexes call transcripts into vector embeddings and executes semantic similarity
search with top-k ranking, thresholding, and speaker/call filtering.

Usage:
    python scripts/search_calls.py --demo
    python scripts/search_calls.py --demo --query "credit card was frozen"
    python scripts/search_calls.py --demo --benchmark
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

from ai_service.diarization.schema import SpeakerTurn
from ai_service.embeddings import (
    EmbeddingConfig,
    EmbeddingModelManager,
    SemanticSearchService,
    TextChunker,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_call_analytics.scripts.search_calls")


def get_demo_conversations() -> dict[str, list[SpeakerTurn]]:
    """Generate realistic banking conversational call transcripts for demonstration."""
    return {
        "call_001_card_freeze": [
            SpeakerTurn(1, "SPEAKER_00", 0.0, 3.2, "Thank you for calling Apex Bank support. How can I help?"),
            SpeakerTurn(2, "SPEAKER_01", 3.5, 9.8, "Hi, I have a big problem. My credit card was frozen yesterday when I tried to pay $450."),
            SpeakerTurn(3, "SPEAKER_00", 10.2, 15.0, "I completely understand and can assist in unfreezing your card. Let me verify your account."),
            SpeakerTurn(4, "SPEAKER_01", 15.5, 20.0, "Account number is 9876543210. I really need to make this payment today."),
            SpeakerTurn(5, "SPEAKER_00", 20.5, 26.0, "The security hold on your credit card has been successfully lifted."),
        ],
        "call_002_mortgage_loan": [
            SpeakerTurn(1, "SPEAKER_00", 0.0, 3.0, "Apex Bank loan department, Alex speaking."),
            SpeakerTurn(2, "SPEAKER_01", 3.5, 11.2, "Hello, I am interested in applying for a business loan or commercial mortgage for my restaurant expansion."),
            SpeakerTurn(3, "SPEAKER_00", 11.8, 17.5, "We offer commercial lending rates starting at 5.5% with flexible repayment options."),
            SpeakerTurn(4, "SPEAKER_01", 18.0, 24.0, "That sounds competitive. What financial documents do I need to submit?"),
        ],
        "call_003_account_balance": [
            SpeakerTurn(1, "SPEAKER_00", 0.0, 3.0, "Customer service, how may I direct your call?"),
            SpeakerTurn(2, "SPEAKER_01", 3.2, 8.5, "Could you check the current available balance in my primary checking account?"),
            SpeakerTurn(3, "SPEAKER_00", 9.0, 14.2, "Your current checking balance is $2,845.50 as of this morning."),
            SpeakerTurn(4, "SPEAKER_01", 14.5, 18.0, "Great, thanks for verifying that for me."),
        ],
        "call_004_wire_transfer_delay": [
            SpeakerTurn(1, "SPEAKER_00", 0.0, 3.0, "Apex Bank support, this is David."),
            SpeakerTurn(2, "SPEAKER_01", 3.4, 11.5, "I sent an international wire transfer of $5,000 three days ago, but the recipient says it has not arrived."),
            SpeakerTurn(3, "SPEAKER_00", 12.0, 18.5, "International wires normally take 3 to 5 business days to clear intermediary banks."),
            SpeakerTurn(4, "SPEAKER_01", 19.0, 23.5, "Can you trace the SWIFT confirmation reference for me?"),
        ],
    }


def run_benchmark(service: SemanticSearchService) -> None:
    """Benchmark query embedding latency, retrieval speed, and semantic similarity sanity checks."""
    print("\n" + "=" * 70)
    print("AI CALL ANALYTICS — PHASE 6 SEMANTIC SEARCH BENCHMARK")
    print("=" * 70)

    # 1. Latency Benchmark
    test_queries = [
        "problem with my credit card being blocked",
        "applying for a small business loan",
        "what is my checking account balance",
        "wire payment not received by recipient",
    ]

    print("\n[Latency Measurements]:")
    embed_times = []
    total_times = []

    for q in test_queries:
        t0 = time.perf_counter()
        _ = service.model_manager.embed(q)
        t_embed = time.perf_counter() - t0

        t1 = time.perf_counter()
        _ = service.search(q, top_k=3)
        t_total = time.perf_counter() - t1

        embed_times.append(t_embed)
        total_times.append(t_total)
        print(f"  • Query: \"{q[:35]}...\" | Embed: {t_embed*1000:6.2f}ms | Total Retrieval: {t_total*1000:6.2f}ms")

    avg_embed = sum(embed_times) / len(embed_times) * 1000
    avg_total = sum(total_times) / len(total_times) * 1000
    print(f"\n  Average Query Embedding Time: {avg_embed:.2f} ms")
    print(f"  Average Total Retrieval Time:  {avg_total:.2f} ms")

    # 2. Semantic Sanity Check (Step 36)
    print("\n" + "-" * 50)
    print("SEMANTIC EMBEDDING SANITY CHECK (Step 36)")
    print("-" * 50)
    s1 = "payment failed"
    s2 = "transaction was declined"
    s3 = "package arrived yesterday"

    v1 = service.model_manager.embed(s1)
    v2 = service.model_manager.embed(s2)
    v3 = service.model_manager.embed(s3)

    from ai_service.embeddings.search import _numpy_cosine_similarity
    sim_1_2 = _numpy_cosine_similarity(v1, v2)
    sim_1_3 = _numpy_cosine_similarity(v1, v3)

    print(f"Similarity(\"{s1}\", \"{s2}\") = {sim_1_2:.4f}")
    print(f"Similarity(\"{s1}\", \"{s3}\") = {sim_1_3:.4f}")
    assert sim_1_2 > sim_1_3, "Semantic sanity check failed: domain similarity should exceed out-of-domain similarity"
    print("  -> Result: VALID (Domain similarity significantly exceeds unrelated text)")
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Call Analytics — Semantic Vector Search CLI")
    parser.add_argument("--demo", action="store_true", help="Index realistic banking demo calls")
    parser.add_argument("--query", type=str, default="card got frozen when paying", help="Query string to search")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results to retrieve (default: 3)")
    parser.add_argument("--threshold", type=float, default=0.25, help="Minimum similarity score threshold")
    parser.add_argument("--filter-speaker", type=str, help="Filter results by speaker ID (e.g. SPEAKER_01)")
    parser.add_argument("--filter-call", type=str, help="Filter results by specific call ID")
    parser.add_argument("--benchmark", action="store_true", help="Run latency benchmark and semantic sanity check")

    args = parser.parse_args()

    service = SemanticSearchService()

    if args.demo or args.benchmark:
        logger.info("Indexing realistic demo banking calls into vector store...")
        calls = get_demo_conversations()
        for call_id, turns in calls.items():
            service.chunker.chunk_overlap_turns = 1
            chunks = service.chunker.chunk_turns(turns, call_id=call_id)
            service.index_chunks(chunks)
        logger.info("Indexed %d demo calls successfully.", len(calls))

    if args.benchmark:
        run_benchmark(service)
        return

    # Execute search
    filters = {}
    if args.filter_speaker:
        filters["speaker"] = args.filter_speaker
    if args.filter_call:
        filters["call_id"] = args.filter_call

    logger.info("Executing semantic search for query: '%s'...", args.query)
    results = service.search(
        query=args.query,
        top_k=args.top_k,
        similarity_threshold=args.threshold,
        filters=filters,
    )

    print("\n" + "=" * 70)
    print(f"SEMANTIC SEARCH RESULTS FOR: \"{args.query}\"")
    print(f"Top-K: {args.top_k} | Min Threshold: {args.threshold} | Matches Found: {len(results)}")
    print("=" * 70)

    if not results:
        print("No matching transcript chunks found above the similarity threshold.")
    else:
        for idx, res in enumerate(results, 1):
            bar = "#" * int(res.similarity_score * 20)
            print(f"\n[{idx}] Call ID: {res.call_id} (Chunk #{res.chunk_id})")
            print(f"    Similarity Score: {res.similarity_score:.4f}  |{bar:<20}|")
            print(f"    Time Interval:    {res.start:.1f}s - {res.end:.1f}s")
            print(f"    Speakers:         {', '.join(res.speaker_ids)}")
            print(f"    Turn IDs:         {res.turn_ids}")
            print(f"    Transcript Text:")
            for line in res.text.split("\n"):
                print(f"      {line}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
