# Speaker Diarization & Whisper Alignment — Phase 4

## Overview

The Speaker Diarization module identifies "who spoke when" across standardized call audio (`16 kHz, mono, PCM_16 WAV`) and temporally aligns these acoustic speaker boundaries with Phase 3 Whisper speech-to-text transcripts.

The resulting output represents the conversation as structured, speaker-attributed turns with exact timestamps, multi-speaker interruption measurements, and conversation share metrics.

```
Standardized Audio (Phase 2)
           │
           ├──► Whisper ASR (Phase 3) ──► Word & Segment Timestamps
           │                                      │
           └──► pyannote.audio (Phase 4) ──► Speaker Activity Boundaries
                                                  │
                                                  ▼
                                      Temporal Overlap Alignment
                                                  │
                                                  ▼
                                     Conversational Speaker Turns
                                                  │
                                                  ▼
                                    Speaker-Attributed Transcript
```

---

## Architecture & Data Flow

```
                      +---------------------------------------+
                      |   Phase 2 Standardized Audio File     |
                      |        (16 kHz Mono PCM16 WAV)        |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      PyannoteDiarizer Engine          |
                      |  (pyannote/speaker-diarization-3.1)   |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |       DiarizationSegment List         |
                      |    (speaker, start, end, duration)    |
                      +-------------------+-------------------+
                                          |
                      +-------------------+-------------------+
                      |      Phase 3 TranscriptionResult      |
                      |   (segments, word-level timestamps)   |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |          TranscriptAligner            |
                      | (Intersection overlap, collar search, |
                      |    cross-speaker splitting policy)    |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |     SpeakerAttributedTranscript       |
                      |   (SpeakerTurn 1, Turn 2, dialogue)   |
                      +---------------------------------------+
```

---

## Configuration Settings

Diarization is configured through `DiarizationConfig` and environment variables:

| Setting | Env Variable | Default | Allowed Values | Description |
|---|---|---|---|---|
| `model_name` | `DIARIZATION_MODEL` | `pyannote/speaker-diarization-3.1` | Hugging Face repo ID | Neural diarization pipeline |
| `hf_token` | `HF_TOKEN` / `HUGGINGFACE_TOKEN` | None | String (`hf_...`) | Hugging Face User Access Token |
| `device` | `DIARIZATION_DEVICE` / `DEVICE` | `auto` | `auto`, `cpu`, `cuda` | Hardware execution target |
| `min_speakers` | `MIN_SPEAKERS` | None | Integer $\ge 1$ | Optional lower speaker bound |
| `max_speakers` | `MAX_SPEAKERS` | None | Integer $\ge 1$ | Optional upper speaker bound |
| `collar` | `DIARIZATION_COLLAR` | `0.25` | Float $\ge 0$ | Temporal boundary tolerance (seconds) |
| `cross_speaker_policy` | `DIARIZATION_CROSS_SPEAKER_POLICY` | `dominant` | `dominant`, `word_level` | Handling ASR segments crossing multiple speakers |

---

## Authentication & Hugging Face Access

The default pipeline `pyannote/speaker-diarization-3.1` is a gated model hosted on Hugging Face. To download weights, users must:
1. Create a Hugging Face User Access Token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
2. Visit [huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) and accept the community user conditions.
3. Visit [huggingface.co/pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) and accept the user conditions.
4. Save the token into `.env`:
   ```bash
   HF_TOKEN=hf_your_token_here
   ```

If the token is missing or conditions are unaccepted, the system raises a descriptive `DiarizationModelLoadError` detailing the required links without crashing unhandled.

---

## Alignment Strategy & Policies

### 1. Overlap Duration Calculation
For each Whisper segment $[w_{start}, w_{end}]$ and diarization segment $[d_{start}, d_{end}]$, the temporal intersection is calculated as:
$$\text{overlap} = \max\left(0, \min(w_{end}, d_{end}) - \max(w_{start}, d_{start})\right)$$

Overlaps are summed across candidate speakers to determine proportional acoustic activity.

### 2. Cross-Speaker Segments Policy
When Whisper generates a single transcript segment spanning multiple active speakers:
- **`dominant` (default):** Assigns the segment to the speaker possessing the largest overlap duration. If a secondary speaker possesses $\ge 20\%$ overlap, a diagnostic warning is emitted.
- **`word_level`:** Uses Whisper's fine-grained word timestamps (`WordTiming`) to assign individual words to speakers. Consecutive words from the same speaker are grouped into sub-segments, cleanly splitting the turn while preserving 100% of the transcribed text with zero alterations.

### 3. Zero-Overlap Collar Fallback
If an ASR segment falls during a pause or slightly outside diarization tracks, the aligner searches for the nearest speaker activity within the configured `collar` tolerance (default: 0.25s). If no speaker is found within the collar, the segment is safely marked as `"UNKNOWN"`.

### 4. Turn Consolidation & Non-Speech Omission
Sequential segments spoken by the same speaker are automatically coalesced into coherent `SpeakerTurn`s. Non-speech audio and pure pauses do not generate empty turns.

---

## Critical Scope Rule: Speaker Roles

> [!IMPORTANT]
> **Acoustic diarization identifies distinct speaker tracks (e.g. `SPEAKER_00`, `SPEAKER_01`), but does NOT infer business roles.**
> The system does not assume `SPEAKER_00 = Agent` or `SPEAKER_01 = Customer`. Role attribution is addressed in downstream phases using conversational lexical cues, greetings, and intent analysis.

---

## Structured Output Contract

Representative output from `SpeakerAttributedTranscript.to_dict()`:

```json
{
  "full_text": "SPEAKER_00: Good morning, how can I help you today?\n\nSPEAKER_01: I would like to set up a joint account with my partner, how do I proceed with doing that.",
  "turns": [
    {
      "turn_id": 1,
      "speaker": "SPEAKER_00",
      "start": 0.25,
      "end": 2.1,
      "duration": 1.85,
      "text": "Good morning, how can I help you today?",
      "source_segment_ids": [0],
      "words": [],
      "overlap_score": 0.95,
      "warning": null
    },
    {
      "turn_id": 2,
      "speaker": "SPEAKER_01",
      "start": 2.4,
      "end": 9.8,
      "duration": 7.4,
      "text": "I would like to set up a joint account with my partner, how do I proceed with doing that.",
      "source_segment_ids": [1],
      "words": [],
      "overlap_score": 0.98,
      "warning": null
    }
  ],
  "speakers": ["SPEAKER_00", "SPEAKER_01"],
  "speaker_stats": {
    "SPEAKER_00": {
      "speaker": "SPEAKER_00",
      "total_speaking_time": 1.85,
      "segment_count": 1,
      "speech_percentage": 20.0
    },
    "SPEAKER_01": {
      "speaker": "SPEAKER_01",
      "total_speaking_time": 7.4,
      "segment_count": 1,
      "speech_percentage": 80.0
    }
  },
  "total_turns": 2,
  "audio_duration": 10.84,
  "speech_duration": 9.25,
  "overlap_duration": 0.0,
  "overlap_detected": false,
  "alignment_time_seconds": 0.002,
  "warnings": [],
  "transcription_metadata": {
    "model_name": "tiny",
    "device": "cpu"
  },
  "diarization_metadata": {
    "model_name": "pyannote/speaker-diarization-3.1",
    "device": "cpu"
  }
}
```

---

## Evaluation Note

Ground-truth speaker turn annotations are unavailable in the standard single-speaker MInDS-14 banking inquiry dataset. Therefore, formal Diarization Error Rate (DER) benchmarking was not performed on this dataset. Alignment logic was verified through synthetic test scenarios, cross-speaker collision audits, and end-to-end integration tests.

---

## CLI Usage

### Run End-to-End ASR + Diarization + Alignment Demo
```bash
python scripts/diarize_and_align.py --demo-minds14
```

### Process Custom Preprocessed WAV Audio
```bash
python scripts/diarize_and_align.py --input data/processed/call.wav --output output/call_turns.json --policy dominant
```
