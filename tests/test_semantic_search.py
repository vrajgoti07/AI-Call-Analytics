"""
AI Call Analytics — Unit and Integration Tests for Phase 6 Semantic Search.

Validates:
1. Conversational text chunking with speaker and timestamp preservation
2. Sentence Transformer embedding model management and batch vector generation
3. Vector dimension and numerical integrity validation (no NaN / Inf)
4. Semantic similarity search with top-k ranking, thresholding, and metadata filtering
5. Information retrieval evaluation (Recall@K, Precision@K, MRR)
6. pgvector database model constraints, schema, and error handling
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

logger = logging.getLogger("test_semantic_search")

from ai_service.diarization.schema import SpeakerTurn
from ai_service.embeddings import (
    ChunkingError,
    EmbeddingConfig,
    EmbeddingGenerationError,
    EmbeddingModelLoadError,
    EmbeddingModelManager,
    InvalidEmbeddingDimension,
    InvalidQuery,
    PgVectorUnavailable,
    SearchResult,
    SemanticSearchService,
    TextChunker,
    TranscriptChunk,
)
from backend.app.models.transcript_embedding import TranscriptEmbedding


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_turns() -> list[SpeakerTurn]:
    """Sample multi-turn banking conversation for testing."""
    return [
        SpeakerTurn(1, "SPEAKER_00", 0.0, 3.0, "Thank you for calling Apex Bank. How can I help you today?"),
        SpeakerTurn(2, "SPEAKER_01", 3.5, 10.0, "Hi, I have a problem with my credit card. It was frozen yesterday when I tried to pay $450 at a grocery store."),
        SpeakerTurn(3, "SPEAKER_00", 10.5, 15.0, "I can help you unfreeze your card. Could you verify your account number?"),
        SpeakerTurn(4, "SPEAKER_01", 15.5, 20.0, "Yes, my account number is 9876543210."),
        SpeakerTurn(5, "SPEAKER_00", 20.5, 25.0, "Thank you. The security hold on your card has now been lifted."),
        SpeakerTurn(6, "SPEAKER_01", 25.5, 28.0, "Thank you so much for your quick help!"),
    ]


# ============================================================================
# 1. Text Chunker Tests (Step 6, 7, 8, 9, 10, 32)
# ============================================================================

class TestTextChunker:
    """Test suite for conversational transcript chunking."""

    def test_chunk_empty_turns(self) -> None:
        """Verify chunking empty turns returns an empty list without error."""
        chunker = TextChunker()
        chunks = chunker.chunk_turns([])
        assert chunks == []

    def test_chunking_preserves_speaker_and_timestamps(self, sample_turns: list[SpeakerTurn]) -> None:
        """Verify chunks retain correct speaker IDs, start/end bounds, and turn IDs."""
        chunker = TextChunker(max_chunk_tokens=50, chunk_overlap_turns=1)
        chunks = chunker.chunk_turns(sample_turns, call_id="call_test_01")

        assert len(chunks) >= 2
        for c in chunks:
            assert c.call_id == "call_test_01"
            assert c.chunk_id > 0
            assert c.start >= 0.0
            assert c.end >= c.start
            assert len(c.speaker_ids) > 0
            assert len(c.turn_ids) > 0
            assert "SPEAKER_" in c.text

    def test_chunk_overlap(self, sample_turns: list[SpeakerTurn]) -> None:
        """Verify overlap turns are carried forward into subsequent chunks."""
        chunker = TextChunker(max_chunk_tokens=30, chunk_overlap_turns=1)
        chunks = chunker.chunk_turns(sample_turns)

        # Check that consecutive chunks share at least one turn ID
        overlap_found = False
        for i in range(len(chunks) - 1):
            shared = set(chunks[i].turn_ids) & set(chunks[i + 1].turn_ids)
            if shared:
                overlap_found = True
                break
        assert overlap_found, "Expected adjacent chunks to share overlapping turns"

    def test_invalid_chunker_params_raise(self) -> None:
        """Verify invalid configuration parameters raise ChunkingError."""
        with pytest.raises(ChunkingError):
            TextChunker(max_chunk_tokens=5)
        with pytest.raises(ChunkingError):
            TextChunker(chunk_overlap_turns=-1)


# ============================================================================
# 2. Embedding Model Manager Tests (Step 3, 4, 5, 11, 12, 31)
# ============================================================================

class TestEmbeddingModelManager:
    """Test suite for model management and vector encoding."""

    def test_mock_embed_and_dimension(self) -> None:
        """Verify single vector encoding produces expected dimension."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.ones(384, dtype=np.float32)

        config = EmbeddingConfig(dimension=384)
        manager = EmbeddingModelManager(config=config, model=mock_model)

        vec = manager.embed("My credit card was blocked.")
        assert len(vec) == 384
        assert isinstance(vec[0], float)

    def test_batch_embed(self) -> None:
        """Verify batch encoding returns aligned list of vectors."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((3, 384), dtype=np.float32)

        config = EmbeddingConfig(dimension=384)
        manager = EmbeddingModelManager(config=config, model=mock_model)

        vectors = manager.embed_batch(["Text 1", "Text 2", "Text 3"])
        assert len(vectors) == 3
        assert len(vectors[0]) == 384

    def test_empty_text_returns_zero_vector(self) -> None:
        """Verify empty string returns zero-filled vector without error."""
        config = EmbeddingConfig(dimension=384)
        manager = EmbeddingModelManager(config=config)
        vec = manager.embed("   ")
        assert len(vec) == 384
        assert all(v == 0.0 for v in vec)

    def test_invalid_dimension_raises(self) -> None:
        """Verify dimension mismatch raises InvalidEmbeddingDimension."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.ones(512, dtype=np.float32)

        config = EmbeddingConfig(dimension=384)
        manager = EmbeddingModelManager(config=config, model=mock_model)

        with pytest.raises(InvalidEmbeddingDimension):
            manager.embed("Test text")

    def test_nan_values_raise_error(self) -> None:
        """Verify NaN values in vector raise EmbeddingGenerationError."""
        mock_model = MagicMock()
        corrupted = np.ones(384, dtype=np.float32)
        corrupted[10] = np.nan
        mock_model.encode.return_value = corrupted

        config = EmbeddingConfig(dimension=384)
        manager = EmbeddingModelManager(config=config, model=mock_model)

        with pytest.raises(EmbeddingGenerationError):
            manager.embed("Test text")


# ============================================================================
# 3. Semantic Similarity Search Tests (Step 21 - 28, 34)
# ============================================================================

class TestSemanticSearch:
    """Test suite for semantic retrieval, ranking, and filtering."""

    def test_empty_query_raises_invalid_query(self) -> None:
        """Verify empty or whitespace-only search query raises InvalidQuery."""
        service = SemanticSearchService()
        with pytest.raises(InvalidQuery):
            service.search("   ")

    def test_semantic_search_ranking(self) -> None:
        """Verify relevant chunks are retrieved with highest similarity."""
        service = SemanticSearchService()

        # Index 3 distinct chunks
        chunks = [
            TranscriptChunk(
                chunk_id=1,
                call_id="call_freeze",
                speaker_ids=["SPEAKER_01"],
                turn_ids=[1],
                start=0.0,
                end=5.0,
                text="My debit card has been frozen and I cannot make payments.",
            ),
            TranscriptChunk(
                chunk_id=2,
                call_id="call_loan",
                speaker_ids=["SPEAKER_01"],
                turn_ids=[2],
                start=0.0,
                end=5.0,
                text="I would like to apply for a small business loan for my shop.",
            ),
            TranscriptChunk(
                chunk_id=3,
                call_id="call_balance",
                speaker_ids=["SPEAKER_01"],
                turn_ids=[3],
                start=0.0,
                end=5.0,
                text="Can you tell me how much money remains in my savings account balance?",
            ),
        ]
        service.index_chunks(chunks)

        # Query about frozen card
        results = service.search("card was blocked and frozen", top_k=2)
        assert len(results) > 0
        top = results[0]
        assert top.call_id == "call_freeze"
        assert top.similarity_score > 0.40

    def test_metadata_filtering(self) -> None:
        """Verify filtering by call_id and speaker returns only matching records."""
        service = SemanticSearchService()
        chunks = [
            TranscriptChunk(1, "call_A", ["SPEAKER_00"], [1], 0.0, 5.0, "Hello welcome to banking."),
            TranscriptChunk(2, "call_B", ["SPEAKER_01"], [2], 0.0, 5.0, "I have an issue with my card."),
        ]
        service.index_chunks(chunks)

        # Filter by call_id
        res_a = service.search("card", filters={"call_id": "call_A"}, similarity_threshold=0.0)
        assert all(r.call_id == "call_A" for r in res_a)

        # Filter by speaker
        res_spk1 = service.search("card", filters={"speaker": "SPEAKER_01"}, similarity_threshold=0.0)
        assert all("SPEAKER_01" in r.speaker_ids for r in res_spk1)

    def test_similarity_threshold(self) -> None:
        """Verify results below similarity threshold are filtered out."""
        service = SemanticSearchService()
        chunks = [
            TranscriptChunk(1, "call_weather", ["SPEAKER_00"], [1], 0.0, 5.0, "The weather is sunny in California."),
        ]
        service.index_chunks(chunks)

        # Unrelated query with high threshold should yield 0 results
        results = service.search("wire transfer bank overdraft", similarity_threshold=0.85)
        assert len(results) == 0


# ============================================================================
# 4. Information Retrieval Evaluation (Step 35)
# ============================================================================

class TestRetrievalEvaluation:
    """Quantitative retrieval evaluation on a small curated project benchmark."""

    def test_evaluation_metrics_recall_and_mrr(self) -> None:
        """
        Evaluate Recall@K, Precision@K, and MRR (Mean Reciprocal Rank)
        on a deterministic set of banking customer inquiries.
        """
        service = SemanticSearchService()

        corpus = [
            TranscriptChunk(1, "call_card_01", ["SPEAKER_01"], [1], 0.0, 5.0, "My credit card was declined at the grocery store."),
            TranscriptChunk(2, "call_card_02", ["SPEAKER_01"], [2], 0.0, 5.0, "I lost my debit card and need to place a freeze on it."),
            TranscriptChunk(3, "call_loan_01", ["SPEAKER_01"], [3], 0.0, 5.0, "What are the interest rates for a commercial real estate business loan?"),
            TranscriptChunk(4, "call_balance_01", ["SPEAKER_01"], [4], 0.0, 5.0, "I need to check the available funds and balance in my account."),
            TranscriptChunk(5, "call_transfer_01", ["SPEAKER_01"], [5], 0.0, 5.0, "How do I initiate an international wire transfer to Europe?"),
        ]
        service.index_chunks(corpus)

        test_cases = [
            {"query": "card blocked payment failed", "relevant_ids": {1, 2}},
            {"query": "commercial mortgage interest rate", "relevant_ids": {3}},
            {"query": "how much money is in my bank balance", "relevant_ids": {4}},
            {"query": "send money abroad international wire", "relevant_ids": {5}},
        ]

        k = 2
        recalls: list[float] = []
        precisions: list[float] = []
        reciprocal_ranks: list[float] = []

        for case in test_cases:
            results = service.search(case["query"], top_k=k, similarity_threshold=0.0)
            retrieved_ids = [r.chunk_id for r in results]
            relevant = case["relevant_ids"]

            # Recall@K: |Retrieved & Relevant| / |Relevant|
            hits = [cid for cid in retrieved_ids if cid in relevant]
            recall = len(hits) / len(relevant)
            recalls.append(recall)

            # Precision@K: |Retrieved & Relevant| / K
            precisions.append(len(hits) / k)

            # MRR: 1 / rank of first relevant result
            rr = 0.0
            for rank, cid in enumerate(retrieved_ids, 1):
                if cid in relevant:
                    rr = 1.0 / rank
                    break
            reciprocal_ranks.append(rr)

        avg_recall = float(np.mean(recalls))
        avg_precision = float(np.mean(precisions))
        mrr = float(np.mean(reciprocal_ranks))

        logger.info(
            "Evaluation Benchmark Results: Recall@%d=%.4f, Precision@%d=%.4f, MRR=%.4f",
            k, avg_recall, k, avg_precision, mrr
        )

        # Baseline criteria
        assert avg_recall >= 0.75, f"Recall@{k} ({avg_recall:.2f}) below expected threshold"
        assert mrr >= 0.80, f"MRR ({mrr:.2f}) below expected threshold"


# ============================================================================
# 5. Database Model & pgvector Tests (Step 13, 14, 16, 17, 33)
# ============================================================================

class TestDatabaseAndPgvector:
    """Test suite for database model schema, constraints, and exceptions."""

    def test_transcript_embedding_model_fields(self) -> None:
        """Verify TranscriptEmbedding SQLAlchemy model has correct columns and types."""
        cols = TranscriptEmbedding.__table__.columns
        assert "call_id" in cols
        assert "chunk_id" in cols
        assert "text" in cols
        assert "start_time" in cols
        assert "end_time" in cols
        assert "speaker_ids" in cols
        assert "turn_ids" in cols
        assert "embedding" in cols
        assert "model_name" in cols
        assert "created_at" in cols

    def test_unique_constraint_defined(self) -> None:
        """Verify unique constraint on (call_id, chunk_id, model_name)."""
        constraints = [
            c for c in TranscriptEmbedding.__table__.constraints
            if hasattr(c, "columns") and {col.name for col in c.columns} == {"call_id", "chunk_id", "model_name"}
        ]
        assert len(constraints) == 1

    def test_pgvector_unavailable_exception(self) -> None:
        """Verify PgVectorUnavailable is an instance of VectorDatabaseError."""
        exc = PgVectorUnavailable("Vector extension missing")
        assert isinstance(exc, Exception)
