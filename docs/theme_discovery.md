# Theme Discovery Pipeline (Phase 7)

## Overview

The **Theme Discovery** pipeline automatically identifies recurring topics, discussion themes, and conversation patterns across customer call recordings. By leveraging dense vector representations generated in Phase 6, non-linear dimensionality reduction, and density-based clustering, it extracts meaningful conversational structures without requiring predefined taxonomies or manual supervision.

```text
Call Transcript Chunks
         ↓
Sentence Transformer Embeddings (384-d)
         ↓
PostgreSQL / pgvector Storage
         ↓
──────────────────────────────────────
      PHASE 7 THEME DISCOVERY
──────────────────────────────────────
         ↓
Embedding Validation & Deduplication
         ↓
UMAP Dimensionality Reduction (384-d → 5-d)
         ↓
HDBSCAN Density Clustering (with Noise Detection)
         ↓
Cluster Statistics & Centroid Proximity
         ↓
Class-based TF-IDF (c-TF-IDF) Keyword Extraction
         ↓
Descriptive Theme Label Synthesis
         ↓
Database Persistence (Runs, Themes, Memberships)
```

---

## 1. Dimensionality Reduction with UMAP

### Why Dimensionality Reduction?
Dense sentence transformer embeddings typically live in high-dimensional vector spaces (e.g., 384 dimensions for `all-MiniLM-L6-v2`). In high-dimensional spaces:
- **The Curse of Dimensionality**: Distance metrics (Euclidean, Cosine) suffer from distance concentration, where the ratio of distances between the nearest and farthest data points approaches 1 as dimensionality increases.
- **Density Estimation Breakdown**: Density-based clustering algorithms like HDBSCAN rely on local density estimation via mutual reachability distance, which becomes ineffective in very high dimensions.

### Why UMAP?
**Uniform Manifold Approximation and Projection (UMAP)** is a non-linear manifold learning technique that models the Riemannian manifold structure of high-dimensional data and projects it onto a lower-dimensional Riemannian space (typically 5 to 10 dimensions for clustering):
1. **Preserves Both Local and Global Structure**: Unlike t-SNE, which focuses primarily on local neighborhoods, UMAP maintains meaningful global relationships between separated clusters.
2. **Metric Flexibility**: Operates directly with `cosine` similarity, matching the geometric characteristics of normalized transformer embeddings.
3. **Computational Scalability**: Scales linearly with sample size $O(N)$ when using approximate nearest neighbor graphs (PyNNDescent), making it suitable for large call transcripts.

---

## 2. Density-Based Clustering with HDBSCAN

### Why HDBSCAN?
**Hierarchical Density-Based Spatial Clustering of Applications with Noise (HDBSCAN)** was selected over $k$-Means and standard DBSCAN for critical structural reasons:
1. **No Fixed $k$**: In call analytics, the true number of recurring customer issues is unknown and dynamic. HDBSCAN automatically discovers the optimal number of clusters based on density persistence.
2. **Variable Density Handling**: Customer issues vary in frequency. High-frequency queries (e.g., balance inquiries) form dense clusters, while rare technical problems form sparser clusters. HDBSCAN traverses the cluster hierarchy to extract clusters of varying densities.
3. **Explicit Noise & Outlier Detection**: HDBSCAN assigns label `-1` to data points situated in sparse regions, preventing anomalous or conversational chatter from contaminating core theme clusters.
4. **Non-Spherical Clusters**: Unlike $k$-Means, which assumes convex, isotropic spherical clusters, HDBSCAN accurately models arbitrary, non-linear cluster topologies.

---

## 3. Noise and Outliers (`-1`)

A central principle of our theme discovery pipeline is:
> **Noise is valid, first-class output.**

Conversational call data contains small talk, greetings, disclaimers, unintelligible fragments, and one-off customer inquiries. Forcing every chunk into a theme leads to noisy, incoherent topics.
- **Label `-1`**: Chunks designated as noise are tracked with their `outlier_score` (GLOSH - Global-Local Outlier Score from Hierarchies).
- **Separation from Themes**: Noise is explicitly accounted for in run statistics (e.g., `noise_count`, `noise_percentage`) but is never persisted as a valid theme record unless explicitly requested as a catch-all category.

---

## 4. Class-Based TF-IDF (c-TF-IDF) Keyword Extraction

Rather than using generic dataset-level TF-IDF or prompting external LLMs, the pipeline uses **Class-based TF-IDF (c-TF-IDF)** to extract distinctive cluster keywords locally and deterministically:

$$W_{t, c} = \text{TF}_{t, c} \times \log\left(1 + \frac{A}{f_t}\right)$$

Where:
- $\text{TF}_{t, c}$ is the frequency of word $t$ across all chunks belonging to cluster $c$.
- $f_t$ is the total frequency of word $t$ across all clusters combined.
- $A$ is the average number of words per cluster.

### Conversational Stopword Filtering
Customer service dialogue contains high-frequency conversational tokens (e.g., *"hello"*, *"thank you"*, *"okay"*, *"yeah"*, *"please"*). The keyword extractor filters these out using a domain-tuned stopword list, ensuring that extracted keywords represent the semantic subject matter rather than conversational filler.

---

## 5. Descriptive Theme Labeling

Theme labels are synthesized from the top extracted unigrams and bigrams:
- **Format**: `KEYWORD_1 / KEYWORD_2 / BIGRAM_PHRASE` (e.g., `LOAN / COMMERCIAL / BUSINESS LOAN`)
- **Nature of Labels**: Machine-generated descriptive summaries, **not** ground-truth business categories.
- **Traceability**: The source of each label is tracked as `label_source = "tfidf"` in the database.

---

## 6. Representative Chunk Selection

To allow analysts and supervisors to audit and understand each discovered theme, the pipeline selects the most representative transcript chunks using **Embedding Space Centroid Proximity**:
1. Compute the high-dimensional centroid $\mathbf{c}_k$ of cluster $k$ from original 384-dimensional embeddings:
   $$\mathbf{c}_k = \frac{1}{|C_k|} \sum_{i \in C_k} \mathbf{e}_i$$
2. Rank members of cluster $k$ by cosine similarity to $\mathbf{c}_k$:
   $$\text{similarity}(\mathbf{e}_i, \mathbf{c}_k) = \frac{\mathbf{e}_i \cdot \mathbf{c}_k}{\|\mathbf{e}_i\| \|\mathbf{c}_k\|}$$
3. Store the top $N$ closest chunks (default: 3) preserving `chunk_id`, `call_id`, `speaker_id`, `start_time`, `end_time`, and full `text`.

---

## 7. Metadata Distribution Integration (Intent & Sentiment)

If transcript chunks possess NLP metadata from Phase 5, the theme discovery service aggregates:
- **Dominant Intents**: Frequency distribution of customer intents (e.g., `card_payment: 52%`, `balance_inquiry: 30%`).
- **Sentiment Distribution**: Breakdown of customer sentiment across the theme (e.g., `negative: 61%`, `neutral: 29%`, `positive: 10%`).
- **Speaker Attribution**: Distribution of speech across diarized speaker roles.
- **Call Breadth**: Distinct call count vs. total chunk count, distinguishing widespread cross-call issues from single-call conversational rants.

---

## 8. Configuration & Reproducibility

Clustering behavior is fully parameterizable via environment variables or the `ThemeDiscoveryConfig` class:

| Parameter | Environment Variable | Default | Description |
|:---|:---|:---:|:---|
| `n_neighbors` | `THEME_UMAP_N_NEIGHBORS` | `15` | Balance between local manifold detail and global topological structure |
| `n_components` | `THEME_UMAP_N_COMPONENTS` | `5` | Target dimensions for HDBSCAN clustering input |
| `min_dist` | `THEME_UMAP_MIN_DIST` | `0.0` | Minimum distance between points in low-dimensional space (0.0 packs clusters tightly) |
| `metric` | `THEME_UMAP_METRIC` | `"cosine"` | Distance metric matching transformer embedding geometry |
| `random_state` | `THEME_UMAP_RANDOM_STATE` | `42` | Random seed for UMAP initialization |
| `min_cluster_size` | `THEME_HDBSCAN_MIN_CLUSTER_SIZE` | `5` | Smallest grouping that can be considered a distinct theme |
| `min_samples` | `THEME_HDBSCAN_MIN_SAMPLES` | `3` | Conservative density threshold (higher values produce more noise points) |
| `min_embeddings` | `THEME_MIN_EMBEDDINGS` | `20` | Minimum sample threshold required before clustering can execute |
| `top_keywords` | `THEME_TOP_KEYWORDS` | `5` | Number of c-TF-IDF keywords per theme |
| `representative_chunks`| `THEME_REPRESENTATIVE_CHUNKS` | `3` | Number of representative chunks to store per theme |

### Configuration Hashing & Idempotency
Every run generates a deterministic SHA-256 hash (`config_hash`) of all clustering and extraction hyperparameters. Re-running the pipeline on identical data with identical parameters allows:
1. Identifying duplicate runs to prevent database bloating.
2. Comparing clustering variations across different parameter iterations.

---

## 9. Database Architecture

Three tables in PostgreSQL persist discovered themes:

```sql
-- 1. Metadata and configuration of a discovery execution
CREATE TABLE theme_discovery_runs (
    id VARCHAR(36) PRIMARY KEY,
    embedding_model VARCHAR(100) NOT NULL,
    embedding_model_version VARCHAR(50) NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    umap_config JSONB NOT NULL,
    hdbscan_config JSONB NOT NULL,
    config_hash VARCHAR(64) NOT NULL,
    dataset_size INTEGER NOT NULL,
    cluster_count INTEGER NOT NULL,
    noise_count INTEGER NOT NULL,
    noise_percentage FLOAT NOT NULL,
    silhouette_score FLOAT,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Discovered themes
CREATE TABLE themes (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) REFERENCES theme_discovery_runs(id) ON DELETE CASCADE,
    cluster_id INTEGER NOT NULL,
    label VARCHAR(255) NOT NULL,
    label_source VARCHAR(50) NOT NULL DEFAULT 'tfidf',
    keywords JSONB NOT NULL,
    size INTEGER NOT NULL,
    percentage FLOAT NOT NULL,
    call_count INTEGER NOT NULL,
    speaker_count INTEGER NOT NULL,
    avg_chunk_duration FLOAT,
    dominant_intents JSONB,
    sentiment_distribution JSONB,
    representative_chunks JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Point-to-theme memberships
CREATE TABLE theme_memberships (
    id VARCHAR(36) PRIMARY KEY,
    theme_id VARCHAR(36) REFERENCES themes(id) ON DELETE CASCADE,
    embedding_id VARCHAR(36) NOT NULL,
    chunk_id VARCHAR(36) NOT NULL,
    call_id VARCHAR(36) NOT NULL,
    membership_probability FLOAT NOT NULL DEFAULT 1.0,
    outlier_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 10. Known Limitations

1. **Unsupervised Nature**: Density-based clusters reflect geometric proximities in the embedding space; they are not certified ground-truth business categories.
2. **UMAP Manifold Distortion**: UMAP alters distance relationships in non-linear ways. While it groups similar items effectively, distances between distant clusters in low dimensions cannot be directly translated into linear semantic distances.
3. **Domain Vocabulary**: c-TF-IDF keyword extraction relies on lexical token frequency. Technical acronyms or customer colloquialisms not in the stopword list may occasionally appear as top terms.
4. **Sensitivity to Data Volume**: With small sample sizes (< 50 chunks), HDBSCAN may classify many points as noise. Meaningful theme discovery thrives on larger corpora (> 200 chunks).
