# CLAUDE.md — Project Context for Cursor AI
> This file gives you full context about this project. Read this before generating or editing any code.

---

## What This Project Is

A **Fake Review Cartel Detector** — an ML system that detects organized networks of fake reviewer accounts (cartels) on platforms like Amazon/Yelp.

The key distinction: this does NOT just flag individual fake reviews. It detects **coordinated groups** of fake accounts working together — same products, same timing, same rating patterns.

---

## Project Owner

- **Name:** Equaan
- **Context:** College ML submission
- **Syllabus constraint:** Must use at least 3 of: AdaBoost, XGBoost, SVD, LDA, PCA, DBSCAN, Logistic Regression, Ensemble Learning
- **Algorithms chosen:** SVD + DBSCAN + XGBoost + AdaBoost + Ensemble (5 total)

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| ML Backend | Python 3.10+ | |
| ML Libraries | scikit-learn, xgboost, scipy, numpy, pandas | All CPU-based, no GPU needed |
| API | FastAPI + uvicorn | Port 8000 |
| Frontend | React 18 + D3.js v7 | Port 3000 |
| Notebooks | Jupyter | For EDA and pipeline development |
| Model persistence | joblib | .pkl files saved in backend/models/ |
| Text features | scikit-learn TfidfVectorizer | |

---

## Folder Structure

```
fake-review-cartel-detector/
│
├── backend/
│   ├── data/
│   │   ├── raw/                        # Original downloaded datasets (gitignored)
│   │   │   ├── amazon_electronics.csv  # Amazon US Customer Reviews (Kaggle)
│   │   │   └── op_spam_v1.4/          # Cornell Yelp Deception Dataset
│   │   └── processed/                  # Output CSVs from pipeline scripts
│   │       ├── amazon_clean.csv
│   │       ├── reviewer_features.csv
│   │       ├── cluster_labels.csv
│   │       └── predictions.csv
│   ├── models/                         # Saved .pkl model files
│   │   ├── xgb_model.pkl
│   │   ├── ada_model.pkl
│   │   ├── ensemble_model.pkl
│   │   └── tfidf_vectorizer.pkl
│   ├── notebooks/                      # Jupyter notebooks for exploration
│   │   ├── 01_eda.ipynb
│   │   ├── 02_feature_eng.ipynb
│   │   ├── 03_svd.ipynb
│   │   └── 04_ensemble.ipynb
│   ├── src/
│   │   ├── __init__.py
│   │   ├── preprocess.py               # Step 1: Load + clean Amazon data
│   │   ├── feature_engineering.py      # Step 2: Build reviewer behavioral features
│   │   ├── svd_pipeline.py             # Step 3: SVD + DBSCAN cartel detection
│   │   ├── ensemble_model.py           # Step 4: XGBoost + AdaBoost classifier
│   │   └── api.py                      # Step 5: FastAPI endpoints
│   ├── requirements.txt
│   └── venv/                           # Python virtual environment (gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── NetworkGraph.jsx        # D3.js force-directed cartel web
│   │   │   ├── StatsPanel.jsx          # Platform-level stats cards
│   │   │   ├── ReviewCard.jsx          # Individual review with fake probability
│   │   │   └── SearchBar.jsx           # Search by product or reviewer ID
│   │   ├── services/
│   │   │   └── api.js                  # Axios API calls to FastAPI
│   │   ├── App.jsx                     # Main layout + state management
│   │   └── index.js
│   └── package.json
│
├── docs/
│   ├── AI_PROMPTS.md
│   ├── PRD.md
│   ├── PROGRESS.md
│   ├── RESULTS.md
│   ├── TODO.md
│   └── claude.md
│
└── README.md
```

---

## ML Pipeline — The Full Flow

```
Raw Amazon Reviews CSV
        ↓
preprocess.py
→ Clean nulls, fix dtypes, parse dates
→ Output: data/processed/amazon_clean.csv
        ↓
feature_engineering.py
→ Group by customer_id
→ Compute 8 behavioral features per reviewer
→ Normalize with StandardScaler
→ Output: data/processed/reviewer_features.csv
        ↓
svd_pipeline.py
→ Build sparse user × product rating matrix (scipy.sparse.csr_matrix)
→ Apply TruncatedSVD (n_components=50) to get user embeddings
→ Concatenate SVD embeddings + behavioral features
→ Apply DBSCAN (eps tuned via k-distance elbow plot, min_samples=5)
→ Output: data/processed/cluster_labels.csv
        ↓
ensemble_model.py
→ Load Cornell Yelp Deception dataset (labeled fake/genuine .txt files)
→ Extract TF-IDF + hand-crafted text features
→ Train XGBoostClassifier + AdaBoostClassifier
→ Combine into VotingClassifier (soft voting)
→ Evaluate: accuracy, precision, recall, F1, ROC-AUC
→ Save: models/*.pkl
        ↓
api.py (FastAPI)
→ Load all processed data + models on startup
→ Serve predictions via REST endpoints
        ↓
React Frontend
→ NetworkGraph.jsx: D3 force-directed graph of reviewer network
→ StatsPanel.jsx: platform-level fake review stats
→ Click node → fetch reviewer details → show in side drawer
```

---

## Data Schemas

### amazon_clean.csv
```
customer_id     : str   — unique reviewer ID
product_id      : str   — unique product ID
star_rating     : int   — 1 to 5
review_date     : date  — parsed datetime
review_body     : str   — review text
verified_purchase: int  — 1 = verified, 0 = not
product_title   : str   — product name
```

### reviewer_features.csv
```
customer_id              : str   — index
avg_rating               : float — mean star rating given
rating_variance          : float — std of ratings (low = suspicious)
review_burst_score       : float — max reviews in any 48hr window
verified_purchase_ratio  : float — % verified purchases
unique_products_reviewed : int   — distinct products reviewed
review_text_length_avg   : float — mean character count per review
review_text_similarity   : float — mean cosine similarity between own reviews
```

### cluster_labels.csv
```
customer_id   : str — reviewer ID
cluster_label : int — DBSCAN cluster (-1 = genuine/noise, 0+ = cartel)
```

### API /cartels response shape
```json
{
  "nodes": [
    {
      "id": "customer_id_string",
      "cluster": 2,
      "suspicion_score": 0.87,
      "avg_rating": 5.0,
      "review_count": 23
    }
  ],
  "edges": [
    {
      "source": "customer_id_A",
      "target": "customer_id_B",
      "shared_products": 7
    }
  ]
}
```

---

## API Endpoints (FastAPI on port 8000)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/stats` | Platform summary: total reviews, fake %, cartel count |
| GET | `/cartels` | Network graph nodes + edges for D3 visualization |
| GET | `/analyze/product/{product_id}` | All reviews for a product with fake scores |
| GET | `/analyze/reviewer/{reviewer_id}` | Full profile + behavioral features for one reviewer |
| POST | `/search` | Body: `{"query": str}` — search reviewer/product IDs |

All endpoints return JSON. CORS is enabled for all origins.

---

## Frontend Details

### NetworkGraph.jsx
- D3.js v7 force-directed graph
- Import as: `import * as d3 from 'd3'`
- Use `useRef` for SVG, `useEffect` for D3 init
- Cartel nodes: red `#ff4444`, glowing drop-shadow, radius ∝ review_count
- Genuine nodes: grey `#555555`, radius 4
- Edges: `#333333`, opacity 0.4, width ∝ shared_products
- Background: `#0a0a0a`
- Enable zoom/pan via `d3.zoom()`
- On node click: call `onNodeClick(nodeData)` prop
- Cleanup simulation on unmount

### Color Palette (Dark Theme)
```
Background:     #0a0a0a
Card bg:        #111111
Border:         #222222
Text primary:   #ffffff
Text secondary: #888888
Accent red:     #ff4444   (cartels, alerts, fake)
Accent green:   #44ff88   (genuine, safe)
Accent yellow:  #ffcc44   (medium risk)
```

### State Management
- All state in App.jsx via useState/useEffect
- No Redux needed — project is not that complex
- API calls via axios in `src/services/api.js`

---

## Key Constraints and Rules

1. **No deep learning** — this is a classical ML project. Do not suggest neural networks, transformers, or anything requiring GPU.
2. **No external databases** — everything reads from CSV files. No PostgreSQL, MongoDB, etc.
3. **No authentication** — this is a demo/college project. No login system needed.
4. **RAM-safe data loading** — always use `pandas chunksize=10000` when loading raw Amazon CSV. The file can be several GB.
5. **No WidthType.PERCENTAGE** — if generating docx files, always use DXA units.
6. **Sparse matrices** — always use `scipy.sparse.csr_matrix` for the user-product matrix. Never build a dense matrix — it will crash with 16GB RAM.
7. **Frontend only uses functional components** — no class components in React.
8. **No external UI libraries** — no Material UI, Chakra, Ant Design. Plain CSS or inline styles only.
9. **D3.js version** — use D3 v7. Import as `import * as d3 from 'd3'`.

---

## Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `MemoryError` when loading CSV | File too large | Add `chunksize=10000` to `pd.read_csv()` |
| `KeyError: customer_id` | Column name mismatch | Print `df.columns` and check exact column names in your CSV |
| CORS error in browser | FastAPI missing CORS middleware | Add `CORSMiddleware` to FastAPI app |
| D3 graph not rendering | SVG ref not ready | Wrap D3 init in `useEffect` with empty dependency array |
| `ModuleNotFoundError: xgboost` | Not installed in venv | Run `pip install xgboost` with venv activated |
| DBSCAN finds 0 clusters | eps too large or too small | Re-run k-distance plot and pick eps at the elbow |

---

## What Good Output Looks Like

- `preprocess.py` prints: total rows, unique reviewers, unique products, date range
- `feature_engineering.py` prints: feature matrix shape, sample of top 10 suspicious reviewers by burst score
- `svd_pipeline.py` prints: explained variance ratio, number of clusters found, noise ratio
- `ensemble_model.py` prints: accuracy > 85%, classification report, saves 4 .pkl files
- `api.py` starts without errors, `/docs` page shows all 5 endpoints
- React app loads at localhost:3000 with dark background, network graph visible, stats panel showing numbers