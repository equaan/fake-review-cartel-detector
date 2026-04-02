# 🕵️ Fake Review Cartel Detector

> Detects organized fake review networks (cartels) using SVD, DBSCAN, XGBoost, AdaBoost, and Ensemble Learning.

---

## What This Project Does

Most fake review detectors flag **individual fake reviews**.  
This system detects **organized cartels** — coordinated groups of fake accounts working together.

Think of it like this: police don't just arrest one drug dealer, they take down the whole operation. This system does the same for fake review networks.

---

## Tech Stack

| Layer | Technology |
|---|---|
| ML Backend | Python, Scikit-learn, XGBoost, SciPy |
| API | FastAPI |
| Frontend | React + D3.js (network graph) |
| Dataset | Amazon US Customer Reviews (Kaggle) |
| Labeled Ground Truth | Cornell Yelp Deception Dataset |

---

## Project Structure

```
fake-review-cartel-detector/
│
├── backend/
│   ├── data/
│   │   └── raw/                  # Put downloaded datasets here
│   ├── notebooks/
│   │   ├── 01_eda.ipynb          # Exploratory Data Analysis
│   │   ├── 02_feature_eng.ipynb  # Feature Engineering
│   │   ├── 03_svd.ipynb          # SVD + DBSCAN pipeline
│   │   └── 04_ensemble.ipynb     # XGBoost + AdaBoost ensemble
│   ├── src/
│   │   ├── preprocess.py         # Data cleaning + feature creation
│   │   ├── svd_pipeline.py       # SVD decomposition
│   │   ├── dbscan_cluster.py     # Cartel detection via DBSCAN
│   │   ├── ensemble_model.py     # XGBoost + AdaBoost ensemble
│   │   └── api.py                # FastAPI routes
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── NetworkGraph.jsx   # D3.js cartel web visualization
│   │   │   ├── ReviewCard.jsx     # Individual review analysis card
│   │   │   ├── StatsPanel.jsx     # Platform-level fake review stats
│   │   │   └── SearchBar.jsx      # Product/reviewer search
│   │   ├── App.jsx
│   │   └── index.js
│   └── package.json
│
├── docs/
│   ├── PRD.md                    # Product Requirements Document
│   ├── TODO.md                   # Development checklist
│   └── AI_PROMPTS.md             # Prompts for code generation
│
└── README.md                     # This file
```

---

## How to Run (Step by Step)

### Step 1 — Download Dataset
1. Go to: `https://www.kaggle.com/datasets/cynthiarempel/amazon-us-customer-reviews-dataset`
2. Download any 1-2 product category CSV files (Electronics or Books work best)
3. Place them in `backend/data/raw/`
4. Also download Cornell Yelp Deception dataset from: `https://myleott.com/op_spam.html`

### Step 2 — Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

### Step 3 — Run Notebooks in Order
```bash
jupyter notebook
# Run 01 → 02 → 03 → 04 in sequence
```

### Step 4 — Start API
```bash
uvicorn src.api:app --reload --port 8000
```

### Step 5 — Frontend Setup
```bash
cd frontend
npm install
npm start
```

### Step 6 — Open App
Go to `http://localhost:3000` in your browser.

---

## ML Pipeline Overview

```
Raw Review Data (user, product, rating, timestamp, text)
        ↓
Feature Engineering
(rating patterns, burst speed, account age, product overlap, text features)
        ↓
SVD — Singular Value Decomposition
(compress user-product matrix, find hidden behavioral similarities)
        ↓
DBSCAN — Density Based Clustering
(find tight suspicious clusters = cartels, mark genuine users as noise)
        ↓
XGBoost ──┐
           ├──► Voting Ensemble → Fake / Genuine + Confidence Score
AdaBoost ──┘
        ↓
React Network Graph Dashboard
(visualize cartel web, click nodes, explore suspects)
```

---

## Syllabus Coverage

| Algorithm | Role in Project |
|---|---|
| SVD | Latent user-product pattern extraction |
| DBSCAN | Unsupervised cartel cluster detection |
| XGBoost | Main fake/genuine classifier |
| AdaBoost | Handles sneaky edge-case fake reviews |
| Ensemble Learning | Combines XGBoost + AdaBoost via voting |

**5 out of 8 syllabus topics covered — all with genuine logical purpose.**

---

## Hardware Requirements

| Spec | Minimum | Recommended |
|---|---|---|
| RAM | 8GB | 16GB |
| CPU | Any modern i5/i7 | i5-12500H or better |
| GPU | Not needed | Not needed |
| Storage | 10GB free | 20GB free |

> ✅ Works perfectly on i5-12500H with 16GB RAM. Use pandas `chunksize` when loading large CSVs.
