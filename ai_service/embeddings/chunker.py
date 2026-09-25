"""
AI Call Analytics — Conversational Transcript Chunker.

Implements turn-aware text chunking for customer support calls (Step 6, 7, 8, 9, 10).
Preserves chronological speaker dialogue context, timestamps, speaker attribution,
and turn identifiers without information loss.
"""

from __future__ import annotations

import logging
from typing import Any

from ai_service.diarization.schema import SpeakerAttributedTranscript, SpeakerTurn
from ai_service.embeddings.exceptions import ChunkingError
from ai_service.embeddings.schema import TranscriptChunk

logger = logging.getLogger("ai_call_analytics.embeddings.chunker")


class TextChunker:
    """
    Conversational chunker that groups sequential speaker turns into
    semantically coherent windows suited for embedding transformer models.
    """

    def __init__(
        self,
        max_chunk_tokens: int = 200,
        chunk_overlap_turns: int = 1,
    ) -> None:
        """
        Initialize the chunker.

        Args:
            max_chunk_tokens: Maximum approximate tokens per chunk (~4 chars/token).
            chunk_overlap_turns: Number of trailing turns to carry forward into the next chunk.
        """
        if max_chunk_tokens < 10:
            raise ChunkingError("max_chunk_tokens must be at least 10")
        if chunk_overlap_turns < 0:
            raise ChunkingError("chunk_overlap_turns cannot be negative")

        self.max_chunk_tokens = max_chunk_tokens
        self.chunk_overlap_turns = chunk_overlap_turns

    def _estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation (~4 characters per token or whitespace split)."""
        words = len(text.split())
        chars = len(text)
        return max(words, chars // 4)

    def chunk_turns(
        self,
        turns: list[SpeakerTurn],
        call_id: str = "default_call",
        base_metadata: dict[str, Any] | None = None,
    ) -> list[TranscriptChunk]:
        """
        Chunk a sequence of speaker turns into overlapping conversational blocks.

        Args:
            turns: Sequential SpeakerTurn objects from Phase 4 alignment.
            call_id: Unique call identifier.
            base_metadata: Optional dictionary of call-level metadata (e.g. sentiment, intent).

        Returns:
            List of strongly-typed TranscriptChunk instances.
        """
        if not turns:
            return []

        chunks: list[TranscriptChunk] = []
        meta = dict(base_metadata or {})
        n = len(turns)
        chunk_id = 1
        idx = 0

        while idx < n:
            current_window: list[SpeakerTurn] = []
            accumulated_tokens = 0
            end_idx = idx

            while end_idx < n:
                turn = turns[end_idx]
                turn_text = f"{turn.speaker}: {turn.text.strip()}"
                turn_tokens = self._estimate_tokens(turn_text)

                # If single turn exceeds budget, include it alone to prevent infinite loop
                if not current_window and turn_tokens >= self.max_chunk_tokens:
                    current_window.append(turn)
                    accumulated_tokens += turn_tokens
                    end_idx += 1
                    break

                if current_window and (accumulated_tokens + turn_tokens > self.max_chunk_tokens):
                    break

                current_window.append(turn)
                accumulated_tokens += turn_tokens
                end_idx += 1

            if not current_window:
                break

            # Format formatted dialogue
            lines = [f"{t.speaker}: {t.text.strip()}" for t in current_window if t.text.strip()]
            chunk_text = "\n".join(lines) if lines else current_window[0].text

            # Collect speaker IDs and turn IDs in order
            unique_speakers: list[str] = []
            for t in current_window:
                if t.speaker not in unique_speakers:
                    unique_speakers.append(t.speaker)

            turn_ids = [t.turn_id for t in current_window]
            start_time = current_window[0].start
            end_time = current_window[-1].end

            chunks.append(
                TranscriptChunk(
                    chunk_id=chunk_id,
                    call_id=call_id,
                    speaker_ids=unique_speakers,
                    turn_ids=turn_ids,
                    start=start_time,
                    end=end_time,
                    text=chunk_text,
                    token_count=accumulated_tokens,
                    metadata=dict(meta),
                )
            )
            chunk_id += 1

            # Advance index respecting overlap
            if end_idx >= n:
                break

            # Advance by at least 1 turn
            step = max(1, len(current_window) - self.chunk_overlap_turns)
            idx += step

        logger.info(
            "Chunked call '%s' (%d turns) into %d chunks (overlap=%d)",
            call_id,
            n,
            len(chunks),
            self.chunk_overlap_turns,
        )
        return chunks

    def chunk_transcript(
        self,
        transcript: SpeakerAttributedTranscript,
        call_id: str = "default_call",
        base_metadata: dict[str, Any] | None = None,
    ) -> list[TranscriptChunk]:
        """Convenience method to chunk directly from a SpeakerAttributedTranscript."""
        return self.chunk_turns(
            turns=transcript.turns,
            call_id=call_id,
            base_metadata=base_metadata,
        )
