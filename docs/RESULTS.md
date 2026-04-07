# Results - Fake Review Cartel Detector

## Model Metrics (Current Saved Ensemble)

Dataset used for evaluation:
- Source: backend/data/raw/fake reviews dataset.csv
- Rows evaluated: 40,432
- Label mapping: CG = fake (1), OR = genuine (0)

Measured with current saved artifacts:
- Model: backend/models/ensemble_model.pkl
- Vectorizer: backend/models/tfidf_vectorizer.pkl

Metrics:
- Accuracy: 0.8652
- Precision (fake class): 0.8688
- Recall (fake class): 0.8602
- F1 (fake class): 0.8645
- ROC-AUC: 0.9444

Notes:
- These values are computed against the currently available labeled dataset using the saved model artifacts.
- This is a practical checkpoint metric for demo/submission tracking.

## Runtime and Integration Validation (Stable 250k Baseline)

System validation summary:
- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:3000
- Data baseline: 250k reviewer feature/cluster workflow (stable on this machine)

Core endpoint checks:
- GET /health -> 200
- GET /docs -> 200
- GET /stats -> 200
- GET /cartels -> 200

Live backend values observed:
- total_reviews: 3,089,972
- unique_reviewers: 2,152,195
- fake_percentage: 10.69
- graph payload: 500 nodes, 73 edges
- sample API process times: /stats ~0.2265s, /cartels ~0.1749s

Deeper flow checks:
- Reviewer drill-down for sample node IDs -> 200,200,200
- Product drill-down from real reviewer review (example: B00GJVF766) -> 200
- Product analyzed reviews (example): 229
- Search endpoint reviewer query -> working (example hits: 11)
- Search endpoint product query -> working (example hits: 13)
- /cartels node ID formatting check -> no float-like IDs (count = 0)
- Missing reviewer path -> 404 (expected)
- Missing product path -> 404 (expected)
- Frontend root response -> 200

## Bug Fix Verified During Validation

Issue found during expanded test:
- GET /analyze/product/{product_id} could return 500 for rows with NaN cluster_label values.

Fix applied:
- backend/src/api.py now safely handles NaN values when serializing star_rating, verified_purchase, and cluster_label in analyze_product.

Post-fix result:
- The same product drill-down request that failed now returns 200.
