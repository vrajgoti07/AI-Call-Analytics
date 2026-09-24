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

### Known Limitations
- Relatively small dataset (hundreds of examples per split, not thousands).
- E-banking domain only — may not generalize to other support domains without additional data.
- Class distribution may be imbalanced.
- Audio quality and accent diversity limited to the recording conditions.

### Verified Programmatic Statistics (en-US Subset)

Inspected programmatically via `scripts/inspect_minds14.py`:

- **Split Structure**: Only `train` split provided by Hugging Face (`train`: 563 examples, `test`: none built-in, train/test split must be created programmatically for training/eval).
- **Total Examples**: 563
- **Audio Availability**: 563 / 563 (100%)
- **Audio Format & Sampling Rate**: 8000 Hz (mono WAV), decodable via `soundfile`.
- **Audio Duration Statistics**:
  - Min duration: 1.707 seconds
  - Max duration: 58.453 seconds
  - Mean duration: 8.577 seconds
  - Median duration: 6.400 seconds
  - Total duration: 4,829.067 seconds (80.48 minutes / ~1.34 hours)
- **Transcription Columns**:
  - `transcription`: 563 examples (541 unique, 22 duplicate utterances)
  - `english_transcription`: 563 examples (identical to `transcription` for en-US)
- **Missing Values**: 0 missing across all columns (`path`, `audio`, `transcription`, `english_transcription`, `intent_class`, `lang_id`).
- **Intent Classes (14 total)**:
  - `cash_deposit`: 48 (8.5%)
  - `card_issues`: 46 (8.2%)
  - `freeze`: 45 (8.0%)
  - `joint_account`: 42 (7.5%)
  - `app_error`: 42 (7.5%)
  - `balance`: 41 (7.3%)
  - `pay_bill`: 41 (7.3%)
  - `atm_limit`: 41 (7.3%)
  - `high_value_payment`: 40 (7.1%)
  - `business_loan`: 39 (6.9%)
  - `direct_debit`: 36 (6.4%)
  - `address`: 34 (6.0%)
  - `abroad`: 34 (6.0%)
  - `latest_transactions`: 34 (6.0%)
  - Total: 563 examples (relatively well balanced across the 14 classes, ranging between 34 and 48 per class).

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

