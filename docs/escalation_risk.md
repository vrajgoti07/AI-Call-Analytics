# Escalation Risk Detection (Phase 8)

## Overview

The **Escalation Risk Detection** pipeline evaluates customer service calls to identify conversational, acoustic, and thematic friction indicators associated with supervisory escalation, customer dispute, or dissatisfaction.

```text
Audio
  ↓
Whisper ASR (Phase 3)
  ↓
Speaker Diarization & Word Alignment (Phase 4)
  ↓
Conversational NLP: Sentiment, Intent, NER (Phase 5)
  ↓
Sentence Transformer Embeddings (Phase 6)
  ↓
Theme Discovery (Phase 7)
  ↓
────────────────────────────────────────────────────────
       PHASE 8 — ESCALATION RISK DETECTION
────────────────────────────────────────────────────────
  ↓
Multi-Modal Signal Extraction
  ↓
Feature Engineering (Sentiment Trajectory, Overlap, Keywords, Repetition)
  ↓
Model Scoring (Heuristic Composite Baseline / Supervised Classifier)
  ↓
Risk Score (0–100) & Categorical Tier (LOW, MEDIUM, HIGH)
  ↓
Evidence-Based Explainability (Top Factors + Observational Narrative)
  ↓
Database Persistence (PostgreSQL / `escalation_risks`)
```

---

## 1. Upstream Data Consumed

Phase 8 consumes structured outputs produced by earlier phases:
* **Phase 4 (Speaker Diarization & Alignment):** Conversational turn structure, speech duration, overlap/interruption duration, speaker turn count, turn duration statistics, and speaker switch frequency.
* **Phase 5 (Sentiment Analysis):** Turn-level sentiment labels (`POSITIVE`, `NEUTRAL`, `NEGATIVE`), confidence scores, negative/positive ratios, and timeline polarity tracking.
* **Phase 5 (Intent Classification):** Primary customer intent from the official MInDS-14 14-class taxonomy (`freeze`, `card_issues`, `app_error`, etc.) and posterior confidence scores.
* **Phase 5 (Named Entity Recognition):** PII-neutral counts of financial entity mentions (`ACCOUNT_NUMBER`, `MONEY`, `DATE`).
* **Phase 7 (Theme Discovery):** Thematic cluster assignments and problem topic indicators (`has_problem_theme`).

---

## 2. Feature Engineering & Catalog

All features adhere to the strict `v1` schema contract (`EscalationFeatures`):

| Feature Name | Type | Source | Definition & Calculation |
|:---|:---:|:---:|:---|
| `call_duration` | float | Phase 4 | Total audio duration in seconds |
| `turn_count` | int | Phase 4 | Number of distinct conversational turns |
| `speaker_count` | int | Phase 4 | Number of distinct speakers detected |
| `speech_duration` | float | Phase 4 | Active acoustic speech duration in seconds |
| `overlap_duration` | float | Phase 4 | Cross-talk / simultaneous speech duration in seconds |
| `overlap_ratio` | float | Phase 4 | `overlap_duration / speech_duration` |
| `avg_turn_duration` | float | Phase 4 | Mean length of conversational turns in seconds |
| `max_turn_duration` | float | Phase 4 | Longest single speaker turn (venting or monologue) |
| `speaker_switch_count` | int | Phase 4 | Number of conversational turn transitions |
| `negative_sentiment_ratio` | float | Phase 5 | Negative turns / total turns |
| `strong_negative_ratio` | float | Phase 5 | Proportion of turns with NEGATIVE sentiment and score $\ge 0.75$ |
| `positive_sentiment_ratio` | float | Phase 5 | Positive turns / total turns |
| `sentiment_volatility` | float | Phase 5 | Standard deviation of turn polarity scores |
| `min_sentiment_score` | float | Phase 5 | Minimum signed polarity across all turns ($-1.0$ to $+1.0$) |
| `final_turn_sentiment` | float | Phase 5 | Signed polarity of the call's concluding turn |
| `early_sentiment_score` | float | Phase 5 | Mean polarity of early turns (first 33% of conversation) |
| `middle_sentiment_score`| float | Phase 5 | Mean polarity of middle turns (middle 33% of conversation) |
| `late_sentiment_score` | float | Phase 5 | Mean polarity of late turns (final 33% of conversation) |
| `sentiment_slope` | float | Phase 5 | Linear regression slope across turn polarities $\times N$ |
| `is_problem_intent` | int | Phase 5 | `1` if intent is `freeze`, `card_issues`, `app_error`, or `direct_debit`; `0` otherwise |
| `intent_confidence` | float | Phase 5 | Posterior confidence of predicted primary intent |
| `escalation_keyword_count` | int | Phase 4 | Count of explicit trigger phrases (*"speak to a manager"*, *"supervisor"*, *"complaint"*, etc.) |
| `repetition_score` | float | Phase 4 | Mean lexical overlap (Jaccard) between consecutive turns |
| `theme_count` | int | Phase 7 | Number of distinct thematic topics in call |
| `has_problem_theme` | int | Phase 7 | `1` if discovered theme keywords include error/freeze terms |
| `entity_count` | int | Phase 5 | Total named entities extracted |
| `account_number_count` | int | Phase 5 | PII-safe count of account/card mentions |
| `money_entity_count` | int | Phase 5 | Count of financial currency mentions |

---

## 3. Critical Decision Tree: Supervised vs. Heuristic

```text
Do reliable escalation labels exist in dataset?
                      │
           ┌──────────┴──────────┐
           │                     │
          YES                   NO
           │                     │
           ▼                     ▼
  Supervised ML Model    Transparent Heuristic
  (GroupKFold, No Leak)   Composite Scoring Engine
           │                     │
           └──────────┬──────────┘
                      │
                      ▼
               Risk Prediction
                      │
                      ▼
            Evidence Explanation
                      │
                      ▼
            PostgreSQL Persistence
```

### Absence of Ground-Truth Labels in MInDS-14
Inspection of MInDS-14 confirms that the public benchmark contains intent categories (`freeze`, `balance`, etc.) and dialect variations, but **does not contain supervisory escalation, complaint, or call-transfer outcome labels**.

Per project engineering principles:
1. **Default Production Model:** The system operates using a **transparent, configurable weighted heuristic model** (`model_type = "heuristic"`). It does **not** claim to be a trained supervised classifier without valid labels.
2. **Supervised Capability:** A full **supervised pipeline** (`SupervisedEscalationModel`) is implemented using `GroupKFold` cross-validation, guaranteeing that when enterprise labeled escalation data is ingested, models can be trained without data leakage.

---

## 4. Heuristic Risk Scoring Formula

The heuristic model evaluates 6 normalized risk dimensions:

$$\text{Risk Probability} = \sum_{k} w_k \cdot S_k$$

Where:
* $S_{\text{neg}}$: Negative sentiment volume ($0.6 \times \text{neg\_ratio} + 0.4 \times \text{strong\_neg\_ratio}$)
* $S_{\text{traj}}$: Trajectory deterioration ($0.6 \times \max(0, -\text{slope}) + 0.4 \times \max(0, -\text{late\_sentiment})$)
* $S_{\text{kw}}$: Explicit escalation keywords ($\min(1.0, \text{keyword\_count} / 2.0)$)
* $S_{\text{intent}}$: Friction intent presence ($\text{is\_problem\_intent} \times \text{confidence}$)
* $S_{\text{acoustic}}$: Conversational overlap and long turn monologue friction
* $S_{\text{rep}}$: Lexical repetition indicating unaddressed inquiries

### Default Weights (Configurable)
* `weight_escalation_keywords`: `0.25`
* `weight_negative_sentiment`: `0.20`
* `weight_sentiment_trajectory`: `0.20`
* `weight_problem_intent`: `0.15`
* `weight_acoustic_friction`: `0.10`
* `weight_repetition`: `0.10`

### Risk Tiers
* `LOW`: Score $< 35.0$
* `MEDIUM`: Score $35.0 \le \text{Score} < 65.0$
* `HIGH`: Score $\ge 65.0$

---

## 5. Supervised Model & Data Leakage Prevention

When labeled data is available, `SupervisedEscalationModel` prevents data leakage across calls:
* **Group-Aware Splitting:** Uses `GroupKFold(n_splits=5, groups=call_ids)`.
* **Zero Leakage Rule:** Every chunk, turn, and feature vector belonging to a specific `call_id` is assigned exclusively to the training set or validation set—never split across both.
* **Evaluation Metrics:** Accuracy, Precision, Recall, F1 Score, ROC-AUC, PR-AUC, and Confusion Matrix.

---

## 6. Explainability & Evidence-Based Reporting

Explanations are strictly observational and evidence-based:
* **Top Contributing Factors:** The top 5 features with the highest weighted impact are extracted and serialized.
* **Human-Readable Narrative:**
  ```text
  Escalation risk is HIGH (score 72.0/100). Concrete friction signals were observed:
  - Detected 2 explicit escalation phrase(s) (e.g., manager, supervisor, dispute).
  - Worsening conversational trajectory: sentiment slope of -1.72 indicates deteriorating customer tone across turns.
  - Problem-related banking topic: inquiry classified as 'freeze' (associated with account friction or transaction blocks).
  - Elevated speech overlap: 12.8% of speech duration involved simultaneous speaking/interruption.
  ```
* **No Subjective Judgments:** The system never generates subjective statements about customer personality (e.g., no *"customer is an angry person"*).

---

## 7. Database Persistence

Persisted in PostgreSQL table `escalation_risks`:

```sql
CREATE TABLE escalation_risks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id VARCHAR(128) NOT NULL,
    model_type VARCHAR(32) NOT NULL DEFAULT 'heuristic',
    model_name VARCHAR(128) NOT NULL,
    model_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    feature_version VARCHAR(32) NOT NULL DEFAULT 'v1',
    threshold_version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    risk_score DOUBLE PRECISION NOT NULL,
    risk_probability DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(32) NOT NULL,
    top_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation TEXT NOT NULL DEFAULT '',
    feature_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    temporal_risk JSONB NOT NULL DEFAULT '[]'::jsonb,
    processing_time_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    metadata_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. Known Limitations

1. **Absence of Longitudinal Ground Truth:** The heuristic model estimates risk from observational indicators. It does not predict future post-call actions unless validated against real enterprise transfer/complaint logs.
2. **Contextual Politeness:** Customers may politely request a supervisor without exhibiting acoustic or negative sentiment friction; the trigger keyword feature mitigates this but depends on transcript quality.
3. **Noisy Speech Diarization:** Diarization boundary misalignments may slightly alter overlap calculations or turn duration measurements.
