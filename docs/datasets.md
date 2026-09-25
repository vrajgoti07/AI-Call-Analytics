# Dataset Documentation — AI Call Analytics

This document describes all datasets used (or planned) for the AI Call Analytics project.

Each entry covers: modality, purpose, license, training/evaluation role, and known limitations.

> **Rule**: Do not invent dataset statistics. All numbers must come from
> programmatic inspection or official dataset documentation.

---

## 1. MInDS-14

| Field | Value |
|-------|-------|
| **Full Name** | Multilingual Intent Detection and Slot Filling — 14 languages |
| **Hugging Face ID** | `PolyAI/minds14` |
| **Subset Used** | `en-US` |
| **Modality** | Audio + transcription + intent label |
| **Task** | Spoken intent classification |
| **Domain** | E-banking customer support |
| **License** | CC BY 4.0 |
| **Paper** | [arXiv:2104.08524](https://arxiv.org/abs/2104.08524) |
| **Role** | Training & evaluation for ASR + intent classification pipeline |

### Purpose
Primary audio dataset for developing the speech-to-text and spoken intent classification pipeline. Contains real spoken utterances with human transcriptions and intent labels across 14 categories.

### Configuration & Loading

The loader is located in `ai_service.datasets.minds14_loader` and can be imported directly or via `ai_service.datasets`.

```python
from ai_service.datasets import load_minds14, inspect_minds14, validate_minds14, prepare_splits

# 1. Load default en-US subset (explicit loading, no auto-download on app startup)
dataset = load_minds14(subset="en-US", split="train", decode_audio=False)

# 2. Configurable cache / offline paths
# Supports MINDS14_CACHE_DIR or HF_HOME environment variables
dataset = load_minds14(subset="en-US", cache_dir="./models/huggingface")

# 3. Load from local disk if pre-downloaded
dataset = load_minds14(data_dir="./data/raw/minds14_en_us")
```

### Expected Dataset Structure & Schema

The dataset exposes 6 standard features:

| Field | Type | Description |
|-------|------|-------------|
| `path` | `Value('string')` | Local audio file path or identifier |
| `audio` | `Audio(decode=False)` | Audio dictionary containing `bytes` or `array` and sampling metadata |
| `transcription` | `Value('string')` | Spoken customer utterance transcribed in natural text |
| `english_transcription` | `Value('string')` | English translation (identical to `transcription` for `en-US`) |
| `intent_class` | `ClassLabel(14)` | Categorical integer label ID [0–13] representing customer intent |
| `lang_id` | `ClassLabel(14)` | Language identifier (index 4 for `en-US`) |

The module provides strongly typed dataclass models for all inspection telemetry:
- `ClassDistributionReport` / `ClassDistributionItem` (counts, frequencies, percentages)
- `MissingDataReport` (`audio_missing`, `text_missing`, `label_missing`, `total_invalid_rows`, per-column percentages)
- `DuplicateDataReport` (`total_records`, `non_empty_records`, `unique_records`, `duplicate_records`, `duplicate_percentage`)
- `AudioMetadataReport` (durations, sampling rate, channels, format, `metadata_source`)
- `SplitInfo` (train, validation, test sample counts and percentages)
- `ValidationResult` (`valid`, `errors`, `warnings`, `statistics`)
- `DatasetSummary` (composite typed summary)

### Audio Validation & Metadata

The loader distinguishes between two metadata extraction modes:
1. **Direct Stream Header (`metadata_source="direct_header"`)**: Reads duration, sampling rate, channel count, and format directly from audio file/stream headers (`soundfile.info`) without decoding the full PCM array into memory.
2. **Decoded Array (`metadata_source="decoded_array"`)**: Extracts array length and channels from pre-decoded float32 numpy arrays when `decode_audio=True`.

### Train / Validation / Test Stratified Split

- **Official Split Limitation**: Hugging Face `PolyAI/minds14` distributes only a single `train` split of 563 examples for `en-US`. No official validation or test splits exist.
- **Leakage Prevention**: To evaluate downstream models reliably, `prepare_splits()` creates deterministic, stratified partitions (default 80/10/10) keyed by `intent_class`.
- **Resulting Splits (Seed 42)**:
  - **Train**: 450 examples (79.9%, 14/14 classes represented)
  - **Validation**: 56 examples (9.9%, 14/14 classes represented)
  - **Test**: 57 examples (10.1%, 14/14 classes represented)
  - **Total**: 563 examples

### Data Validation Rules

The module provides `validate_minds14(dataset)` which verifies:
1. Dataset is non-empty.
2. Required columns (`audio`, `transcription`, `intent_class`) are present.
3. Intent labels are within valid integer range `[0, 13]`.
4. Audio entries have valid headers, duration > 0, and valid sampling rate.
5. Text entries are non-null strings.
6. Validation returns a structured `ValidationResult` with `valid: bool`, `errors: list[str]`, `warnings: list[str]`, and `statistics: dict`.

### How to Run Inspection & Validation

```bash
# Run programmatic inspection and generate report
python scripts/inspect_minds14.py
```

### How to Run Tests

```bash
# Run unit and integration tests
python -m pytest tests/ -v
```

### Verified Programmatic Statistics (en-US Subset)

Inspected programmatically via `scripts/inspect_minds14.py`:

- **Split Structure**: Only `train` split provided natively by Hugging Face (563 examples).
- **Total Examples**: 563
- **Audio Availability**: 563 / 563 (100% available, 0 missing)
- **Audio Format & Sampling Rate**: 8000 Hz, 1 channel (mono), WAV container.
- **Audio Duration Statistics**:
  - Min duration: 1.707 seconds
  - Max duration: 58.453 seconds
  - Mean duration: 8.577 seconds
  - Median duration: 6.400 seconds
  - Total duration: 4,829.067 seconds (80.48 minutes / ~1.34 hours)
- **Transcription Columns**:
  - `transcription`: 563 records (541 unique, 22 duplicate utterances, **3.91% duplicates**)
  - `english_transcription`: 563 records (identical to `transcription` for en-US)
- **Missing Data Audit**:
  - `audio_missing`: 0
  - `text_missing`: 0
  - `label_missing`: 0
  - `total_invalid_rows`: 0
  - 0 missing values across all columns (`path`, `audio`, `transcription`, `english_transcription`, `intent_class`, `lang_id`).
- **Intent Classes (14 total)**:
  - `cash_deposit`: 48 (8.53%)
  - `card_issues`: 46 (8.17%)
  - `freeze`: 45 (7.99%)
  - `joint_account`: 42 (7.46%)
  - `app_error`: 42 (7.46%)
  - `balance`: 41 (7.28%)
  - `pay_bill`: 41 (7.28%)
  - `atm_limit`: 41 (7.28%)
  - `high_value_payment`: 40 (7.10%)
  - `business_loan`: 39 (6.93%)
  - `direct_debit`: 36 (6.39%)
  - `address`: 34 (6.04%)
  - `abroad`: 34 (6.04%)
  - `latest_transactions`: 34 (6.04%)
  - Total: 563 examples (well balanced across all 14 classes, ranging between 34 and 48 per class).
- **Validation Audit**:
  - Status: PASSED (0 errors, 0 warnings)

---

## 2. BANKING77 *(planned — not yet loaded)*

| Field | Value |
|-------|-------|
| **Full Name** | BANKING77 |
| **Hugging Face ID** | `PolyAI/banking77` |
| **Modality** | Text only |
| **Task** | Intent classification (77 classes) |
| **Domain** | Banking customer support |
| **License** | CC BY 4.0 |
| **Role** | Text-based intent classification training |

### Purpose
Provides a large, fine-grained set of banking intent categories for text-based intent classification. Complements MInDS-14 by offering more intent diversity in the same domain.

### Known Limitations
- Text-only — no audio component.
- Banking domain only.
- Statistics not yet inspected (dataset not loaded).

---

## 3. Bitext *(planned — not yet loaded)*

| Field | Value |
|-------|-------|
| **Full Name** | Bitext Customer Support Dataset |
| **Modality** | Text only |
| **Task** | Customer support NLU (intent + entities) |
| **Domain** | General customer support |
| **License** | TBD — verify before use |
| **Role** | General customer support text training |

### Purpose
Broad customer-support text data covering multiple domains. Intended to improve generalization of NLU models beyond banking-specific queries.

### Known Limitations
- License must be verified before training use.
- Text-only — no audio.
- Statistics not yet inspected.

---

## 4. GoEmotions *(planned — not yet loaded)*

| Field | Value |
|-------|-------|
| **Full Name** | GoEmotions |
| **Hugging Face ID** | `google-research-datasets/go_emotions` |
| **Modality** | Text only |
| **Task** | Emotion / sentiment classification |
| **Domain** | Reddit comments (general) |
| **License** | Apache 2.0 |
| **Role** | Sentiment analysis training |

### Purpose
Fine-grained emotion classification dataset. Used to train or fine-tune sentiment analysis models that can detect customer emotions during calls.

### Known Limitations
- Reddit domain — may differ from customer support language.
- Multi-label classification (one text can have multiple emotions).
- Text-only — sentiment must be applied to transcribed text, not audio directly.
- Statistics not yet inspected.

---

## 5. AppTek Call-Center *(planned — evaluation only)*

| Field | Value |
|-------|-------|
| **Full Name** | AppTek Call-Center Dataset |
| **Modality** | Audio |
| **Task** | ASR evaluation / benchmarking |
| **Domain** | Call center |
| **License** | TBD — verify before use |
| **Role** | **Evaluation / benchmark only — NOT for training** |

### Purpose
Unseen evaluation dataset for benchmarking ASR and pipeline performance on real call-center audio. Used to measure how well the system generalizes to unseen data.

### Known Limitations
- **Must NOT be used as training data** if dataset documentation specifies evaluation-only use.
- License and access requirements must be verified.
- Statistics not yet inspected.

---

## Intent Taxonomy Decision (Deferred to Phase 5)

> **IMPORTANT — This section documents a known architectural issue.
> It is NOT resolved in Phase 1. It will be addressed in Phase 5 (intent classifier)
> and Phase 7 (escalation-risk scoring).**

### The Problem

Each dataset uses a **different, incompatible intent taxonomy**:

| Dataset | # Intent Classes | Example Intents | Domain |
|---------|-----------------|-----------------|--------|
| **MInDS-14** | 14 | `balance`, `pay_bill`, `freeze`, `abroad`, `joint_account` | E-banking (spoken) |
| **BANKING77** | 77 | `card_arrival`, `exchange_rate`, `lost_or_stolen_card`, `top_up_failed` | Banking (text) |
| **Bitext** | Varies | General customer-support intents (varies by dataset version) | Multi-domain (text) |

These taxonomies **cannot be directly merged** — the label sets are different sizes, use different naming conventions, and cover different granularities.

### No Escalation Labels

**None** of these datasets include escalation/outcome labels (i.e., whether a call actually escalated to a supervisor, was transferred, or resulted in a complaint). This means:

- Escalation-risk prediction (Phase 7) **cannot** be trained in a supervised manner using these datasets alone.
- Phase 7 will use a **documented heuristic/rule-based scoring approach** initially (e.g., based on detected sentiment, repeat-contact signals, explicit escalation keywords).
- If manually labeled escalation data is provided later, a supervised model can be trained to replace the heuristic.

### Decision (Phase 5)

Phase 5 will explicitly decide:
- Which taxonomy powers the production intent classifier.
- Whether to unify/map taxonomies, use a hierarchical approach, or keep them separate.
- How to handle intents that exist in one dataset but not another.

**Until Phase 5, each dataset keeps its own original intent labels unchanged.**

---

## AppTek Call-Center — Access Verification

> **WARNING: Access to AppTek Call-Center data has NOT been verified.**

As of Phase 1, the following is documented:

1. **No public Hugging Face dataset** named "AppTek Call-Center" was found. This may be a proprietary or restricted dataset.
2. Many real call-center audio datasets require:
   - A separate **data-use agreement (DUA)** or license application.
   - **Institutional affiliation** or research agreement.
   - **NDA or commercial license** from the data provider.
3. **Until access is confirmed**, this dataset is treated as **unavailable** and is **not used** in any pipeline stage.
4. If access is later obtained, its license terms must be reviewed before any use (training or evaluation).

**Action required**: Verify whether AppTek Call-Center data is accessible and under what terms before planning any evaluation work that depends on it.

---

## Dataset Pipeline Rules

1. **Keep datasets separated.** Each dataset has its own loader module under `ai_service/datasets/`.
2. **Do not modify original data.** All transformations produce new files in `data/processed/`.
3. **Do not mix datasets** without explicit documentation of why and how.
4. **Do not use evaluation-only datasets for training.**
5. **Verify licenses** before using any dataset for model training.
6. **All statistics must be computed programmatically** from real data — never hardcoded.

---

## Dataset Category Map

| Category | Datasets | Modality |
|----------|----------|----------|
| Audio + transcript + spoken intent | MInDS-14 | Audio |
| Text intent classification | BANKING77 | Text |
| General customer-support text | Bitext | Text |
| Emotion / sentiment text | GoEmotions | Text |
| Evaluation / benchmark | AppTek Call-Center (access unverified) | Audio |

