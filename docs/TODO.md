# TODO - Fake Review Cartel Detector
> Work through this top to bottom. Don't skip steps.

---

## Phase 1 - Setup (Day 1)

- [x] Create GitHub repo named `fake-review-cartel-detector`
- [x] Create folder structure as per README
- [x] Set up Python virtual environment
  ```bash
  python -m venv venv
  source venv/bin/activate  # Mac/Linux
  venv\Scripts\activate     # Windows
  ```
- [x] Install backend dependencies
  ```bash
  pip install pandas numpy scipy scikit-learn xgboost fastapi uvicorn jupyter nltk matplotlib seaborn
  ```
- [x] Download Amazon Reviews dataset from Kaggle (Electronics category CSV)
- [x] Download labeled fake review dataset (`fake reviews dataset.csv`)
- [x] Place both datasets in `backend/data/raw/`
- [x] Create React app
  ```bash
  npx create-react-app frontend
  cd frontend
  npm install d3 axios react-router-dom
  ```

---

## Phase 2 - Exploratory Data Analysis (Day 1-2)

- [x] Open `notebooks/01_eda.ipynb`
- [x] Load Amazon CSV with chunksize=10000 to avoid RAM issues
- [x] Check basic stats: shape, dtypes, nulls, rating distribution
- [x] Plot: rating distribution histogram
- [x] Plot: reviews per user distribution (log scale)
- [x] Plot: reviews per day time series
- [x] Identify top 100 most prolific reviewers
- [x] Check verified vs unverified purchase ratio
- [x] Save cleaned dataframe to `data/processed/amazon_clean.csv`
- [x] Load labeled fake review dataset, check label distribution
- [x] Write EDA summary as markdown cell at bottom of notebook

---

## Phase 3 - Feature Engineering (Day 2-3)

- [x] Open `notebooks/02_feature_eng.ipynb`
- [ ] Group Amazon data by `customer_id`
- [ ] Calculate per-reviewer features:
  - [ ] `avg_rating` - mean star rating
  - [ ] `rating_variance` - std of star ratings
  - [ ] `review_burst_score` - max reviews in any 48-hour window
  - [ ] `account_age_at_first_review` - days from join to first review
  - [ ] `product_overlap_ratio` - % shared products with other users (sample 1000 users)
  - [ ] `review_text_length_avg` - mean character count
  - [ ] `verified_purchase_ratio` - % marked verified
  - [ ] `unique_products_reviewed` - count distinct products
- [ ] Normalize all features using StandardScaler
- [ ] Save feature matrix to `data/processed/reviewer_features.csv`
- [ ] For the labeled fake review dataset: extract same text features using TF-IDF (top 50 features)
- [ ] Save labeled review feature matrix + labels to `data/processed/cornell_features.csv`

---

## Phase 4 - SVD Pipeline (Day 3-4)

- [ ] Open `notebooks/03_svd.ipynb`
- [ ] Build user x product sparse rating matrix using `scipy.sparse.csr_matrix`
- [ ] Apply `TruncatedSVD(n_components=50)` from scikit-learn
- [ ] Check explained variance ratio - aim for > 70% total
- [ ] Visualize top 2 SVD components in a scatter plot (color by rating avg)
- [ ] Concatenate SVD embeddings + behavioral features into one matrix
- [ ] Apply DBSCAN:
  - [ ] Plot k-distance graph to find optimal eps
  - [ ] Start with `eps=0.5, min_samples=5`
  - [ ] Check number of clusters found and noise ratio
  - [ ] Tune until clusters are meaningful (5-30 clusters typical)
- [ ] Visualize clusters using PCA 2D projection (color by cluster label)
- [ ] Print top 10 most suspicious clusters with their reviewer stats
- [ ] Save cluster labels to `data/processed/cluster_labels.csv`

---

## Phase 5 - Ensemble Model (Day 4-5)

- [ ] Open `notebooks/04_ensemble.ipynb`
- [ ] Load Cornell features + labels
- [ ] Split 80/20 train/test
- [ ] Train XGBoost classifier:
  - [ ] Start: `n_estimators=100, max_depth=4, learning_rate=0.1`
  - [ ] Run GridSearchCV on those 3 params
  - [ ] Print best params + test accuracy
- [ ] Train AdaBoost classifier:
  - [ ] Start: `n_estimators=100, learning_rate=0.5`
  - [ ] Evaluate on test set
- [ ] Build VotingClassifier combining both
- [ ] Evaluate ensemble:
  - [ ] Accuracy score
  - [ ] Classification report (precision, recall, F1)
  - [ ] Confusion matrix heatmap
  - [ ] ROC-AUC curve
- [ ] Apply trained ensemble to Amazon data (with DBSCAN cluster as extra feature)
- [ ] Save final predictions to `data/processed/predictions.csv`
- [ ] Save trained models using joblib:
  ```python
  import joblib
  joblib.dump(ensemble_model, 'models/ensemble.pkl')
  ```

---

## Phase 6 - FastAPI Backend (Day 5-6)

- [x] Create `backend/src/api.py`
- [ ] Load trained models + processed data on startup
- [ ] Implement endpoints:
  - [x] `GET /stats` - platform level summary
  - [x] `GET /cartels` - all detected clusters with member list
  - [x] `GET /analyze/product/{product_id}` - reviews + fake scores
  - [x] `GET /analyze/reviewer/{reviewer_id}` - reviewer profile
  - [x] `POST /search` - search by product or reviewer
- [x] Add CORS middleware (React needs this)
- [x] Test all endpoints with FastAPI's auto docs at `localhost:8000/docs`
- [x] Return network graph data structure from `/cartels`:
  ```json
  {
    "nodes": [{"id": "user123", "cluster": 2, "suspicion_score": 0.87}],
    "edges": [{"source": "user123", "target": "user456", "shared_products": 5}]
  }
  ```

---

## Phase 7 - React Frontend (Day 6-8)

- [x] Set up API service file (`src/services/api.js`) with axios base URL
- [x] Build `StatsPanel` component - top-level platform stats cards
- [x] Build `NetworkGraph` component using D3.js:
  - [x] Force-directed graph layout
  - [x] Red glowing nodes for cartel members
  - [x] Grey nodes for genuine reviewers
  - [x] Edge thickness = number of shared products
  - [x] Zoom and pan enabled
  - [x] Click node -> fires event to show reviewer panel
- [x] Build `ReviewCard` component - fake probability bar, badge, text
- [x] Build `SearchBar` component - debounced search, highlights node on graph
- [x] Connect all components in `App.jsx`
- [x] Add dark theme CSS (background #0a0a0a, accent #ff4444 for cartels)
- [x] Test full flow: load graph -> click node -> see reviewer details

---

## Phase 8 - Polish and Documentation (Day 8-9)

- [ ] Write `README.md` (already done - review and update if needed)
- [ ] Record a 2-minute screen demo video
- [x] Add model performance metrics to a `RESULTS.md` file
- [ ] Push all code to GitHub with meaningful commit messages
- [ ] Create a `requirements.txt`:
  ```bash
  pip freeze > requirements.txt
  ```
- [ ] Test full pipeline on fresh environment (run all notebooks from scratch)
- [ ] Prepare 5-minute explanation for teacher viva:
  - Why SVD?
  - Why DBSCAN over K-Means?
  - Why ensemble over single model?
  - What does the network graph show?
  - What is the semi-supervised approach?

---

## Quick Reference - Common Commands

```bash
# Start backend
cd backend && uvicorn src.api:app --reload --port 8000

# Start frontend
cd frontend && npm start

# Run notebooks
cd backend && jupyter notebook

# Activate venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```
