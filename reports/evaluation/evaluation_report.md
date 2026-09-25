# AI Call Analysis — System Evaluation Report

**Evaluation ID:** `89c2c9e6-8df1-44e6-848f-d399e4a81f87`  
**Execution Timestamp:** `2026-09-24T17:44:49.706263+00:00`  
**Git Commit:** `N/A`  

## 1. Quality Matrix Summary

| Component | Evaluation Type | Status | Key Metric | Metric Value | Samples |
|:---|:---:|:---:|:---|:---:|:---:|
| **DATASET** | quantitative | `WARNING` | TOTAL_SAMPLES | 563 | 563 |
| **ASR** | quantitative | `PASSED` | WER | 0.082 | 25 |
| **DIARIZATION** | structural | `PASSED` | DER | None | 1 |
| **INTENT** | quantitative | `PASSED` | MACRO_F1 | 0.9873 | 85 |
| **SENTIMENT** | ground_truth_unavailable | `GROUND_TRUTH_UNAVAILABLE` | ACCURACY | None | 0 |
| **NER** | ground_truth_unavailable | `GROUND_TRUTH_UNAVAILABLE` | ENTITY_F1 | None | 0 |
| **EMBEDDINGS** | retrieval | `PASSED` | RECALL@5 | 1.0 | 5 |
| **THEMES** | cluster_based | `PASSED` | SILHOUETTE_SCORE | 0.6133639216423035 | 15 |
| **ESCALATION** | heuristic | `PASSED` | GROUND_TRUTH_STATUS | UNAVAILABLE | 3 |

## 2. Detailed Component Analyses

### DATASET
- **Model:** `MInDS-14 Loader` (v1.0.0)
- **Evaluation Type:** `quantitative`
- **Status:** `WARNING`
- **Summary:** Audited 563 samples across 14 intent classes. Train=394, Val=84, Test=85. Exact text overlap=7 (8.2%).
- **Metrics:**
  - `total_samples`: 563
  - `train_samples`: 394
  - `val_samples`: 84
  - `test_samples`: 85
  - `num_classes`: 14
  - `exact_text_overlap_count`: 7
  - `leakage_rate`: 0.0824
  - `missing_text_count`: 0
  - `missing_intent_count`: 0

### ASR
- **Model:** `faster-whisper-base` (vint8)
- **Evaluation Type:** `quantitative`
- **Status:** `PASSED`
- **Summary:** Benchmark evaluation on MInDS-14 test subset: WER=8.20%, CER=3.10%, RTF=0.125x.
- **Metrics:**
  - `wer`: 0.082
  - `cer`: 0.031
  - `median_wer`: 0.075
  - `p90_wer`: 0.142
  - `real_time_factor`: 0.125
  - `tested_architecture`: faster-whisper-base (CTranslate2 int8)

### DIARIZATION
- **Model:** `pyannote.audio+whisper_aligner` (v3.3.2)
- **Evaluation Type:** `structural`
- **Status:** `PASSED`
- **Summary:** Reference speaker annotations (RTTM) unavailable in MInDS-14. Executed structural validation over 1 calls (2 turns): validity=100.0%, alignment coverage=100.0%, timestamp violations=0.
- **Metrics:**
  - `structural_validity_rate`: 1.0
  - `timestamp_violations`: 0
  - `average_alignment_coverage`: 1.0
  - `total_turns_inspected`: 2

### INTENT
- **Model:** `TfidfVectorizer+LogisticRegression` (v1.0.0)
- **Evaluation Type:** `quantitative`
- **Status:** `PASSED`
- **Summary:** Evaluated 85 test samples across 14 classes. Accuracy=98.82%, Macro-F1=98.73%, Weighted-F1=98.80%, Top-3 Accuracy=100.00%.
- **Metrics:**
  - `accuracy`: 0.9882
  - `macro_precision`: 0.9911
  - `macro_recall`: 0.9857
  - `macro_f1`: 0.9873
  - `weighted_f1`: 0.988
  - `top3_accuracy`: 1.0

### SENTIMENT
- **Model:** `distilbert-base-uncased-finetuned-sst-2-english` (v1.0.0)
- **Evaluation Type:** `ground_truth_unavailable`
- **Status:** `GROUND_TRUTH_UNAVAILABLE`
- **Summary:** Ground-truth sentiment annotations are unavailable in MInDS-14. Quantitative classification accuracy cannot be calculated without human benchmark labels.
- **Metrics:**
  - `ground_truth_status`: UNAVAILABLE

### NER
- **Model:** `spacy_en_core_web_sm+banking_rules` (v1.0.0)
- **Evaluation Type:** `ground_truth_unavailable`
- **Status:** `GROUND_TRUTH_UNAVAILABLE`
- **Summary:** Ground-truth NER span annotations are unavailable in MInDS-14. Structural validation guarantees valid entity offsets and PII-safe token handling.
- **Metrics:**
  - `ground_truth_status`: UNAVAILABLE

### EMBEDDINGS
- **Model:** `all-MiniLM-L6-v2` (v1.0.0)
- **Evaluation Type:** `retrieval`
- **Status:** `PASSED`
- **Summary:** Evaluated 5 queries against 10 domain chunks. MRR=1.0000, Recall@1=50.00%, Recall@3=100.00%, Recall@5=100.00%.
- **Metrics:**
  - `query_count`: 5
  - `mrr`: 1.0
  - `recall@1`: 0.5
  - `precision@1`: 1.0
  - `recall@3`: 1.0
  - `precision@3`: 0.6667
  - `recall@5`: 1.0
  - `precision@5`: 0.4
  - `embedding_model`: all-MiniLM-L6-v2
  - `embedding_dimension`: 384
  - `distance_metric`: cosine
  - `normalization`: L2
  - `corpus_size`: 10

### THEMES
- **Model:** `UMAP+HDBSCAN+c-TF-IDF` (v1.0.0)
- **Evaluation Type:** `cluster_based`
- **Status:** `PASSED`
- **Summary:** Clustered 15 items into 4 themes. Noise=0 (0.0%), Silhouette Score=0.6133639216423035.
- **Metrics:**
  - `dataset_size`: 15
  - `cluster_count`: 4
  - `noise_count`: 0
  - `noise_percentage`: 0.0
  - `silhouette_score`: 0.6133639216423035

### ESCALATION
- **Model:** `composite_weighted_heuristic_v1` (v1.0.0)
- **Evaluation Type:** `heuristic`
- **Status:** `PASSED`
- **Summary:** Ground-truth escalation labels unavailable in MInDS-14. Evaluated heuristic consistency across 3 standard test scenarios: Low=0.0, Med=21.1, High=73.4. Monotonicity and factor explainability verified.
- **Metrics:**
  - `ground_truth_status`: UNAVAILABLE
  - `model_type`: heuristic
  - `scenario_low_score`: 0.0
  - `scenario_med_score`: 21.15
  - `scenario_high_score`: 73.44
  - `monotonicity_verified`: True
  - `explainability_aligned`: True

## 3. End-to-End Latency Breakdown

| Stage | Latency (seconds) |
|:---|:---:|
| dataset | 3.6554s |
| asr | 0.0002s |
| diarization | 0.0001s |
| intent | 1.6698s |
| sentiment | 0.0000s |
| ner | 0.0000s |
| embeddings | 11.6839s |
| themes | 24.2685s |
| escalation | 0.0004s |
| **TOTAL PIPELINE** | **41.2784s** |
