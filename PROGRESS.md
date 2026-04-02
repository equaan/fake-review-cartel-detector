# Progress - Fake Review Cartel Detector

This file is a handoff note so the project can be moved to another machine without losing context.

## Current Status

The project has moved beyond planning docs and now has a working code scaffold for:

- backend preprocessing
- reviewer feature engineering
- SVD + DBSCAN pipeline
- ensemble model training scaffold
- FastAPI API scaffold
- React frontend scaffold

The codebase is not finished end-to-end yet, but it is on track.

## What Has Been Completed

### Phase 1

Completed:

- Git repo exists locally
- project folder structure created
- Python virtual environment created
- backend dependencies installed
- React frontend scaffold created
- datasets placed in `backend/data/raw/`

Datasets currently used:

- Amazon reviews: `backend/data/raw/amazon_reviews_us_Electronics_v1_00.csv`
- labeled fake review dataset: `backend/data/raw/fake reviews dataset.csv`

Important note:

- The original plan mentioned the Cornell dataset, but the actual labeled file being used is `fake reviews dataset.csv`
- `TODO.md` was updated to reflect that substitution in Phase 1 and Phase 2

### Phase 2

Completed:

- cleaned Amazon dataset generated
- EDA notebook created and filled with relevant steps
- EDA summary written
- rating distribution plot created
- reviews-per-user log plot created
- reviews-per-day plot created
- top 100 reviewers CSV created
- label distribution for the downloaded labeled dataset checked

Generated files:

- `backend/data/processed/amazon_clean.csv`
- `backend/data/processed/eda_summary.txt`
- `backend/data/processed/rating_distribution.png`
- `backend/data/processed/reviews_per_user_log.png`
- `backend/data/processed/reviews_per_day.png`
- `backend/data/processed/top_100_reviewers.csv`
- `backend/notebooks/01_eda.ipynb`

Key Amazon EDA stats:

- cleaned reviews: 3,089,972
- unique reviewers: 2,152,195
- unique products: 185,715
- date range: 1999-06-09 to 2015-08-31
- verified purchase ratio: about 84.04%

Key labeled dataset stats:

- file shape: 40,432 rows x 4 columns
- labels: `CG = 20,216`, `OR = 20,216`
- categories: 10

### Phase 3

Started, but not fully completed on the full Amazon dataset.

Completed so far:

- `backend/src/feature_engineering.py` upgraded to compute:
  - `avg_rating`
  - `rating_variance`
  - `review_burst_score`
  - `account_age_at_first_review` (proxy based on first observed review date)
  - `product_overlap_ratio` (sample-based estimate)
  - `verified_purchase_ratio`
  - `unique_products_reviewed`
  - `review_text_length_avg`
  - `review_text_similarity`
- support added for `--max-rows` so Phase 3 can run on a subset first
- a fast first-pass subset run completed successfully
- labeled feature matrix created from `fake reviews dataset.csv`
- feature engineering notebook created

Generated files:

- `backend/data/processed/reviewer_features.csv`
- `backend/data/processed/cornell_features.csv`
- `backend/notebooks/02_feature_eng.ipynb`

Important caveat:

- `reviewer_features.csv` is currently based on the first **250,000 cleaned Amazon rows**, not the full 3,089,972-row dataset
- the generated matrix contains **207,498 reviewers** and 9 normalized reviewer features plus `customer_id`
- this was done intentionally to keep progress moving on a weaker laptop

## What Was Being Attempted When the Laptop Struggled

The machine slowdown/crash was **not** from ensemble model training.

The expensive operation was the Amazon-side unsupervised pipeline:

1. build reviewer features from a large subset/full dataset
2. run SVD on the user-product sparse matrix
3. build k-distance plot
4. prepare DBSCAN clustering inputs

This is heavy because:

- Amazon file is very large
- reviewer count is huge
- sparse matrix + SVD + nearest-neighbor distance computation are CPU and memory intensive

What happened specifically:

- a Phase 4 subset run was attempted using `svd_pipeline.py`
- `kdistance_plot.png` was created, which means the run got partway through
- the process was interrupted before cluster labels were successfully finished and saved
- there is currently **no confirmed completed `cluster_labels.csv`**

## Files That Exist Right Now

### Backend source

- `backend/src/preprocess.py`
- `backend/src/feature_engineering.py`
- `backend/src/svd_pipeline.py`
- `backend/src/ensemble_model.py`
- `backend/src/api.py`

### Backend notebooks

- `backend/notebooks/01_eda.ipynb`
- `backend/notebooks/02_feature_eng.ipynb`
- `backend/notebooks/03_svd.ipynb`
- `backend/notebooks/04_ensemble.ipynb`

### Processed outputs

- `backend/data/processed/amazon_clean.csv`
- `backend/data/processed/reviewer_features.csv`
- `backend/data/processed/cornell_features.csv`
- `backend/data/processed/eda_summary.txt`
- `backend/data/processed/rating_distribution.png`
- `backend/data/processed/reviews_per_user_log.png`
- `backend/data/processed/reviews_per_day.png`
- `backend/data/processed/top_100_reviewers.csv`
- `backend/data/processed/kdistance_plot.png`

Missing or not yet confirmed:

- `backend/data/processed/cluster_labels.csv`
- `backend/data/processed/predictions.csv`
- trained model `.pkl` files in `backend/models/`

## Important Notes Before Moving To Another PC

If you push this repo to GitHub and clone it on another machine:

- push the code
- do **not** rely on pushing large processed data files unless you intentionally want them in the repo
- the repo already ignores raw and processed data by default, which is good
- after cloning on the stronger PC, download or copy the raw datasets again into `backend/data/raw/`

Recommended raw files to place on the new machine:

- `backend/data/raw/amazon_reviews_us_Electronics_v1_00.csv`
- `backend/data/raw/fake reviews dataset.csv`

## How To Resume On A Stronger PC

### 1. Clone and set up

From the repo root:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

### 2. Put datasets back into `backend/data/raw/`

Make sure these exist:

```text
backend/data/raw/amazon_reviews_us_Electronics_v1_00.csv
backend/data/raw/fake reviews dataset.csv
```

### 3. Rebuild Phase 2 clean data if needed

```powershell
cd backend
..\venv\Scripts\python.exe src\preprocess.py data\raw\amazon_reviews_us_Electronics_v1_00.csv
```

### 4. Continue Phase 3

First-pass subset version:

```powershell
cd backend
..\venv\Scripts\python.exe src\feature_engineering.py --max-rows 250000 --overlap-sample-size 1000
```

Bigger run on a stronger PC:

```powershell
cd backend
..\venv\Scripts\python.exe src\feature_engineering.py --max-rows 1000000 --overlap-sample-size 1000
```

Eventually, full run:

```powershell
cd backend
..\venv\Scripts\python.exe src\feature_engineering.py --overlap-sample-size 1000
```

Recommendation:

- do not jump straight to the full run unless the machine is clearly strong enough
- validate success on 250k, then 1M, then full

### 5. Finish the Phase 3 notebook

Open:

- `backend/notebooks/02_feature_eng.ipynb`

Use it to document:

- generated feature columns
- subset vs full-run caveat
- suspicious reviewer examples
- summary observations

## How To Proceed Further After Phase 3

### Phase 4

Run subset SVD first:

```powershell
cd backend
..\venv\Scripts\python.exe src\svd_pipeline.py --max-rows 250000 --eps 0.7 --min-samples 5
```

Then increase scale gradually:

```powershell
cd backend
..\venv\Scripts\python.exe src\svd_pipeline.py --max-rows 1000000 --eps 0.7 --min-samples 5
```

What to verify:

- `cluster_labels.csv` created
- `kdistance_plot.png` updated
- `clusters_viz.png` created
- terminal output shows:
  - explained variance ratio
  - cluster count
  - noise count

### Phase 5

Current status:

- `backend/src/ensemble_model.py` still follows the original Cornell-style folder assumption
- since the actual labeled dataset is now `fake reviews dataset.csv`, this script should be adapted before running Phase 5

What to do next on the stronger PC:

- update `ensemble_model.py` to train from `fake reviews dataset.csv`
- or create a second training script specifically for that file
- then train XGBoost + AdaBoost + VotingClassifier
- save:
  - `xgb_model.pkl`
  - `ada_model.pkl`
  - `ensemble_model.pkl`
  - `tfidf_vectorizer.pkl`

### Phase 6

Current API status:

- FastAPI file exists
- routes exist
- CORS exists
- it still needs real processed data and trained models to fully behave as intended

Once Phase 4 and 5 outputs exist, test:

```powershell
cd backend
..\venv\Scripts\uvicorn.exe src.api:app --reload --port 8000
```

Then open:

- `http://localhost:8000/docs`

### Phase 7

Frontend scaffold exists, but it still needs:

- real D3 `NetworkGraph`
- `ReviewCard`
- better `SearchBar`
- live API wiring to finished backend outputs

## Recommended Safe Resume Strategy

On the stronger PC, use this order:

1. confirm raw datasets exist
2. run `preprocess.py`
3. run `feature_engineering.py` on 250k
4. run `svd_pipeline.py` on 250k
5. if stable, scale both to 1M
6. adapt and run `ensemble_model.py` using `fake reviews dataset.csv`
7. finish API data loading
8. finish frontend integration

This staged approach is much safer than trying the full Amazon pipeline immediately.

## Summary

You are **not starting from scratch**.

You already have:

- Phase 1 complete
- Phase 2 complete
- Phase 3 started with real generated outputs
- backend pipeline scripts written
- API scaffold written
- frontend scaffold written

The main unfinished work is:

- complete Phase 3 on a larger/full Amazon run
- complete Phase 4 clustering outputs
- adapt Phase 5 training to the actual labeled dataset file
- finish backend + frontend integration
