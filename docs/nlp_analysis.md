# AI Call Analytics — Conversational NLP Analysis (Phase 5)

## Overview

Phase 5 introduces a modular, production-grade NLP analysis layer that consumes structured speaker-attributed transcripts from Phase 4 and produces:

1. **Multilevel Sentiment Analysis** (turn-level, speaker-level, call-level, and chronological timeline)
2. **14-Class Intent Classification** using the official MInDS-14 banking taxonomy
3. **Named Entity Recognition (NER)** attributing entities to specific speakers and turns with exact character offsets
4. **Unified NLP Analysis Orchestrator** with error isolation, language validation, and PII-safe logging

---

## Architectural Data Flow

```text
SpeakerAttributedTranscript (from Phase 4)
             │
             ▼
     ┌────────────────┐
     │  NLPAnalyzer   │ ── Language Check ('en')
     └───────┬────────┘
             │
   ┌─────────┼─────────┐
   ▼         ▼         ▼
┌───────┐ ┌──────┐ ┌──────┐
│Senti- │ │Intent│ │ NER  │   (Independent Error Isolation)
│ment   │ │      │ │      │
└───┬───┘ └──┬───┘ └──┬───┘
    │        │        │
    └────────┼────────┘
             ▼
     CallNLPAnalysis
     ├── sentiment (CallSentiment)
     ├── intent (IntentPrediction)
     ├── entities (NERResult)
     ├── speaker_analysis (dict[str, SpeakerAnalysisSummary])
     └── metadata (NLPAnalysisMetadata)
```

---

## Component A: Sentiment Analysis

### Model Details
* **Primary Transformer Model:** `distilbert/distilbert-base-uncased-finetuned-sst-2-english`
* **Source:** Hugging Face Hub
* **Language:** English (`en`)
* **Normalized Labels:** `POSITIVE`, `NEUTRAL`, `NEGATIVE`
* **Fallback Engine:** Lexicon keyword rule-based classifier (ensuring high availability in zero-network environments)

### Multilevel Hierarchy
* **Turn-Level:** Evaluated per speaker turn with normalized label and confidence score.
* **Timeline:** Ordered series of `(timestamp, turn_id, speaker, label, score)` points ready for frontend visualizers.
* **Speaker-Level:** Computes positive, neutral, and negative turn counts, polarity ratios, and average sentiment score for each speaker (`SPEAKER_00`, `SPEAKER_01`, etc.) without premature role assumptions.
* **Call-Level Summary:** Uses a mathematically defensible negative-ratio threshold ($\ge 35\%$ negative turns triggers overall `NEGATIVE` call classification, while positive dominance with low negativity produces `POSITIVE`).

### Limitations
* The model is an SST-2 fine-tuned model for English sentiment. While effective for polarity, customer-service sarcasm or polite frustration requires conversational context. Non-English transcripts are flagged as unsupported.

---

## Component B: Intent Classification

### Taxonomy & Dataset
Adheres strictly to the official 14-class e-banking taxonomy of the **MInDS-14** dataset:
1. `abroad`
2. `address`
3. `app_error`
4. `atm_limit`
5. `balance`
6. `business_loan`
7. `card_issues`
8. `cash_deposit`
9. `direct_debit`
10. `freeze`
11. `high_value_payment`
12. `joint_account`
13. `latest_transactions`
14. `pay_bill`

### Model Strategy & Pipeline
* **Architecture:** TF-IDF n-gram vectorizer (unigrams + bigrams, sublinear TF scaling) + multi-class Logistic Regression with class-weight balancing (`class_weight='balanced'`).
* **Training / Inference Separation:**
  * Model trained offline via `scripts/train_intent_classifier.py` using stratified splits (70% train, 15% val, 15% test).
  * Serialized artifact saved to `models/intent/minds14_intent_model.joblib`.
  * Inference service (`IntentClassifier`) loads the model once and performs memory-cached predictions with top-$k$ posterior confidence probabilities.

### Measured Evaluation (Held-out Test Split)
Evaluated on 85 held-out test samples across all 14 banking intent classes:
* **Accuracy:** 98.82%
* **Macro Precision:** 0.9911
* **Macro Recall:** 0.9857
* **Macro F1-Score:** 0.9873
* **Weighted F1-Score:** 0.9880

### Limitations
* Scoped to the e-banking domain represented in MInDS-14. Out-of-domain queries produce low maximum posterior probabilities across classes.

---

## Component C: Named Entity Recognition (NER)

### Model & Pattern Matchers
* **Statistical Model:** `en_core_web_sm` (spaCy 3.8+)
* **Domain Regex Rules:** High-precision rule matchers for e-banking and customer contact entities:
  * `EMAIL`: Standard RFC-compliant email pattern
  * `PHONE`: Separated North American / international phone patterns
  * `ACCOUNT_NUMBER`: 8–16 digit account identifiers preceded by banking keywords

### Supported Entity Labels
`PERSON`, `ORG`, `DATE`, `TIME`, `MONEY`, `PRODUCT`, `GPE`, `LOC`, `CARDINAL`, `PERCENT`, `EMAIL`, `PHONE`, `ACCOUNT_NUMBER`.

### Attribution & Offset Validation
* Entities are matched against each conversational turn, retaining `speaker` attribution and `turn_id`.
* Exact `start` and `end` character offsets match the source transcript slice (`text[start:end] == entity.text`).

### Privacy & PII Handling
* In compliance with security standards, application logs **never print raw PII text** (e.g. actual account numbers or emails). Logging is restricted to category counts (e.g. `{'ACCOUNT_NUMBER': 1, 'EMAIL': 1}`). Terminal CLI output masks sensitive digits.

---

## Usage Example

```python
from ai_service.pipeline import NLPAnalyzer
from ai_service.diarization.schema import SpeakerAttributedTranscript

# Load or receive Phase 4 transcript
analyzer = NLPAnalyzer()
result = analyzer.analyze(transcript)

print("Status:", result.metadata.status)
print("Intent:", result.intent.predicted_intent, result.intent.confidence)
print("Call Sentiment:", result.sentiment.label, result.sentiment.score)
print("Entities Found:", len(result.entities.entities))
```

### CLI Tool
```bash
# Run on built-in realistic multi-turn banking call demo
python scripts/analyze_call_nlp.py --demo

# Analyze an existing Phase 4 transcript JSON
python scripts/analyze_call_nlp.py --transcript output/aligned_call.json --output output/nlp_result.json
```
