# Fake Review Cartel Detector

Detects coordinated fake-review groups (cartels), not just isolated fake reviews, using a classical ML pipeline with SVD, DBSCAN, XGBoost, AdaBoost, and ensemble voting.

## 1. Project Summary (For Presentation)

Problem:
- Typical fake-review systems classify single reviews.
- Real abuse often happens through coordinated reviewer groups.

This project:
- engineers reviewer behavior features,
- learns latent reviewer-product structure with SVD,
- finds dense suspicious groups with DBSCAN,
- classifies fake vs genuine review text with XGBoost + AdaBoost ensemble,
- exposes results through FastAPI,
- visualizes suspicious reviewer networks in a React + D3 dashboard.

## 2. Current Stable Status

Validated on this machine:
- backend API routes are running and tested,
- frontend compiles and serves successfully,
- end-to-end flow works with the stable 250k reviewer clustering baseline.

Latest measured runtime snapshot:
- total reviews: 3,089,972
- unique reviewers: 2,152,195
- graph payload: 500 nodes, 73 edges

Latest measured model snapshot:
- accuracy: 0.8652
- precision: 0.8688
- recall: 0.8602
- f1: 0.8645
- roc-auc: 0.9444

See full details in docs/RESULTS.md.

## 3. Quick Start (Windows)

From repository root:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

Place datasets in:
- backend/data/raw/amazon_reviews_us_Electronics_v1_00.csv
- backend/data/raw/fake reviews dataset.csv

Run backend:

```powershell
cd backend
..\venv\Scripts\uvicorn.exe src.api:app --reload --port 8000
```

Run frontend (new terminal):

```powershell
cd frontend
npm start
```

Open:
- http://localhost:3000
- http://localhost:8000/docs

## 4. Presentation Demo Flow (2-3 Minutes)

1. Start with problem statement: coordinated cartels are more harmful than isolated fake reviews.
2. Show stats cards in UI (volume and suspicious ratio).
3. Open network graph and explain nodes/edges meaning.
4. Click a suspicious node and show reviewer profile + reviews.
5. Use search to find reviewer/product and show highlight/drill-down.
6. Close with model metrics and explain why ensemble + clustering together is stronger.

## 5. Viva Q&A Cheat Sheet

Why SVD?
- The user-product matrix is huge and sparse. SVD compresses it into dense latent structure capturing hidden behavior similarities.

Why DBSCAN instead of K-Means?
- No need to predefine cluster count and it naturally marks isolated users as noise (-1), which fits this problem.

Why ensemble instead of a single model?
- XGBoost is strong, AdaBoost helps hard edge cases, and soft voting improves stability.

How do you handle missing Amazon labels?
- Semi-supervised strategy: supervised text model trained on labeled fake review data plus unsupervised cartel discovery from Amazon behavior/network patterns.

What does the graph represent?
- Nodes are reviewers, edges are shared reviewed products, dense connected suspicious clusters indicate potential cartels.

## 6. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, scikit-learn, xgboost, scipy, pandas |
| Frontend | React 18, D3.js v7 |
| Storage | CSV artifacts (no database for v1) |
| Model persistence | joblib |

## 7. Syllabus Coverage

| Algorithm | Usage |
|---|---|
| SVD | latent reviewer-product embeddings |
| DBSCAN | cartel cluster detection |
| XGBoost | supervised fake/genuine classifier |
| AdaBoost | complementary classifier in ensemble |
| Ensemble Learning | voting classifier for final score |

## 8. Repository Layout

```text
fake-review-cartel-detector-main/
  backend/
  frontend/
  docs/
    AI_PROMPTS.md
    PRD.md
    PROGRESS.md
    RESULTS.md
    TODO.md
    claude.md
  README.md
```

## 9. Documentation Index

- docs/PRD.md: full product requirements and scope
- docs/TODO.md: implementation checklist
- docs/PROGRESS.md: handoff and timeline progress
- docs/RESULTS.md: metrics and runtime validation
- docs/AI_PROMPTS.md: generation prompts and viva notes
- docs/claude.md: detailed project context and constraints

## 10. Important Operational Note

This machine is stable with the 250k reviewer-feature/cluster pipeline.

Avoid running the 1M SVD/DBSCAN step here due to memory and responsiveness limits. For larger clustering quality upgrades, run that step on a stronger PC and then bring artifacts back.
