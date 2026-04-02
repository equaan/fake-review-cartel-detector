# Product Requirements Document (PRD)
## Fake Review Cartel Detector
**Version:** 1.0  
**Author:** Equaan  
**Subject:** Machine Learning — College Submission  

---

## 1. Problem Statement

Online platforms like Amazon, Zomato, and Flipkart are flooded with fake reviews. Most existing detection systems flag **individual reviews** using sentiment analysis or text classification. These systems are blind to the real threat — **organized review cartels**: coordinated networks of fake accounts that post reviews together in synchronized bursts.

A cartel of 20 accounts, each posting 5-star reviews for the same 10 products in the same 48-hour window, is far more damaging than 20 random fake reviews. The pattern only becomes visible when you analyze the **network**, not individual reviews.

This project builds a system that detects those cartels.

---

## 2. Objective

Build an end-to-end ML system that:
1. Ingests raw Amazon/Yelp review data
2. Engineers behavioral features per reviewer
3. Uses SVD to extract latent user-product patterns
4. Uses DBSCAN to detect coordinated reviewer clusters (cartels)
5. Uses an XGBoost + AdaBoost ensemble to classify reviews as fake or genuine
6. Displays results in an interactive React network graph dashboard

---

## 3. Scope

### In Scope
- Batch processing of Amazon product review datasets
- Behavioral feature engineering per reviewer account
- SVD-based dimensionality reduction on user-product matrix
- DBSCAN-based unsupervised cartel cluster detection
- XGBoost + AdaBoost ensemble classification
- FastAPI backend exposing ML predictions
- React frontend with D3.js network graph visualization
- Product-level fake review percentage stats
- Reviewer-level suspicion scoring

### Out of Scope
- Real-time streaming ingestion (future work)
- Browser extension (future work)
- Multi-language review support (English only for v1)
- Deep learning models (out of syllabus scope)

---

## 4. Dataset

### Primary Dataset — Amazon US Customer Reviews
- **Source:** Kaggle — `cynthiarempel/amazon-us-customer-reviews-dataset`
- **Size:** 130+ million reviews across multiple categories
- **Fields used:** `customer_id`, `product_id`, `star_rating`, `review_date`, `review_body`, `verified_purchase`
- **Usage:** Feature engineering + DBSCAN cartel detection
- **Note:** No ground truth fake/genuine labels — treated as unsupervised discovery

### Ground Truth Dataset — Cornell Yelp Deception Dataset
- **Source:** `myleott.com/op_spam.html`
- **Size:** 1,600 reviews (800 fake, 800 genuine) — labeled by humans
- **Usage:** Train and evaluate XGBoost + AdaBoost ensemble classifier
- **Why this:** One of the only academically validated fake review datasets with verified labels

### Strategy
Train the classifier on Cornell labeled data. Apply it to Amazon data with DBSCAN cluster membership as an additional feature. This is a **semi-supervised approach** — academically valid and actually more realistic than pure supervised learning.

---

## 5. Feature Engineering

For each reviewer account, calculate the following signals:

| Feature | Description | Suspicion Signal |
|---|---|---|
| `avg_rating` | Mean star rating given | Always 5.0 = suspicious |
| `rating_variance` | How much ratings vary | Zero variance = suspicious |
| `review_burst_score` | Reviews per day in peak window | High bursts = suspicious |
| `account_age_at_first_review` | Days since account created | Very new = suspicious |
| `product_overlap_ratio` | % of products reviewed same as cluster | High overlap = suspicious |
| `review_text_length_avg` | Average characters per review | Very short/generic = suspicious |
| `verified_purchase_ratio` | % of reviews marked verified | Low verified % = suspicious |
| `unique_products_reviewed` | Total distinct products reviewed | Very low diversity = suspicious |
| `review_text_similarity` | Cosine similarity between own reviews | High self-similarity = suspicious |

---

## 6. ML Pipeline

### Stage 1 — SVD (Singular Value Decomposition)
- Build a sparse user × product rating matrix
- Apply Truncated SVD (TruncatedSVD from scikit-learn) with n_components = 50
- Output: Dense user embeddings capturing latent behavioral patterns
- **Why SVD:** Same technique Netflix uses. Finds hidden similarities between users that aren't obvious from raw data.

### Stage 2 — DBSCAN Clustering
- Input: SVD user embeddings + behavioral feature vectors
- Parameters: eps tuned via k-distance elbow plot, min_samples = 5
- Output: Cluster labels per user (-1 = genuine/noise, 0,1,2... = cartel clusters)
- **Why DBSCAN:** Finds clusters of arbitrary shape without needing to specify count upfront. Marks isolated genuine users as noise naturally. Perfect for geographic/behavioral density clustering.

### Stage 3 — XGBoost Classifier
- Input: Behavioral features + DBSCAN cluster label + text features (TF-IDF top 50)
- Training data: Cornell Yelp Deception Dataset (labeled)
- Output: Fake probability score (0.0 to 1.0) per review
- Hyperparameter tuning: GridSearchCV on n_estimators, max_depth, learning_rate

### Stage 4 — AdaBoost Classifier
- Same input as XGBoost
- Focuses on misclassified edge cases from XGBoost
- Particularly good at catching sophisticated fakes (older accounts, longer reviews)

### Stage 5 — Voting Ensemble
- Hard voting: majority of XGBoost + AdaBoost predictions wins
- Final output: `fake` or `genuine` + combined confidence score

---

## 7. API Design (FastAPI)

| Endpoint | Method | Description |
|---|---|---|
| `/analyze/product/{product_id}` | GET | Get all reviews + fake scores for a product |
| `/analyze/reviewer/{reviewer_id}` | GET | Get suspicion profile for one reviewer |
| `/cartels` | GET | Return all detected cartel clusters |
| `/stats` | GET | Platform-level fake review percentage |
| `/search` | POST | Search by product name or reviewer ID |

---

## 8. Frontend Design (React + D3.js)

### Main View — Network Graph
- Nodes = reviewer accounts
- Edges = shared product reviews
- Red glowing nodes = flagged cartel members
- Grey nodes = genuine reviewers
- Click node → opens reviewer profile panel
- Zoom, pan, drag supported

### Side Panel — Stats
- Total reviews analyzed
- Fake review percentage
- Number of cartels detected
- Largest cartel size
- Top targeted products

### Review Card
- Product name
- Review text
- Star rating
- Fake probability bar (0–100%)
- Cartel membership badge (if applicable)

### Search Bar
- Input a product ID or reviewer ID
- Instantly highlights that node in the network graph

---

## 9. Success Metrics

| Metric | Target |
|---|---|
| Ensemble Classification Accuracy | > 85% on Cornell dataset |
| Precision (fake class) | > 80% |
| Recall (fake class) | > 75% |
| DBSCAN cartel detection | Visually coherent clusters on graph |
| API response time | < 2 seconds per product query |
| Frontend load time | < 3 seconds |

---

## 10. Tech Stack Summary

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| ML Libraries | scikit-learn, xgboost, scipy, numpy, pandas |
| Text Processing | scikit-learn TF-IDF, NLTK |
| API | FastAPI + uvicorn |
| Frontend | React 18 + D3.js v7 |
| Data Storage | CSV files (no database needed for v1) |
| Notebooks | Jupyter |

---

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| No ground truth labels in Amazon data | Use Cornell dataset for supervised training, Amazon for cartel discovery |
| Large dataset size (RAM constraint) | Use pandas chunksize=10000 when loading CSVs |
| DBSCAN eps parameter sensitivity | Tune using k-distance elbow plot |
| Sparse user-product matrix | Use SciPy sparse matrices before SVD |
| D3.js network graph performance with large graphs | Limit to top 500 most suspicious nodes for visualization |
