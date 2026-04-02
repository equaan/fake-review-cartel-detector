# AI Code Generation Prompts
## Fake Review Cartel Detector
> Copy each prompt into your AI tool (Cursor, ChatGPT, Claude) exactly as written. Each prompt is self-contained.

---

## PROMPT 1 — Data Loading & Preprocessing

```
I am building a Fake Review Cartel Detector ML project in Python. 

Create a Python script called `preprocess.py` in a folder called `src/`.

It should:
1. Load an Amazon product reviews CSV file using pandas with chunksize=10000 to handle large files
2. The CSV has these columns: customer_id, product_id, star_rating, review_date, review_body, verified_purchase, product_title
3. Clean the data:
   - Drop rows where customer_id, product_id, or star_rating is null
   - Convert star_rating to integer
   - Convert review_date to datetime
   - Convert verified_purchase: 'Y' → 1, 'N' → 0
   - Strip whitespace from review_body
4. Save the cleaned dataframe to data/processed/amazon_clean.csv
5. Print a summary: total reviews, unique reviewers, unique products, date range

Use pandas, numpy. Add docstrings to every function. Handle file not found errors gracefully.
```

---

## PROMPT 2 — Feature Engineering

```
I am building a Fake Review Cartel Detector. I have a cleaned Amazon reviews CSV at data/processed/amazon_clean.csv with columns: customer_id, product_id, star_rating, review_date, review_body, verified_purchase.

Create a Python script called `feature_engineering.py` in src/.

For each unique customer_id, calculate these behavioral features:
1. avg_rating — mean of star_rating
2. rating_variance — standard deviation of star_rating (0 = always same rating = suspicious)
3. review_burst_score — maximum number of reviews posted within any 48-hour window
4. verified_purchase_ratio — proportion of reviews where verified_purchase == 1
5. unique_products_reviewed — count of distinct product_ids reviewed
6. review_text_length_avg — mean character length of review_body
7. review_text_similarity — mean pairwise cosine similarity between TF-IDF vectors of own reviews (use sklearn TfidfVectorizer, limit to reviewers with 3+ reviews, set similarity=0.5 for those with fewer)

After computing all features:
- Normalize all numeric features using StandardScaler
- Save the feature matrix to data/processed/reviewer_features.csv with customer_id as index

Use pandas, numpy, sklearn. Add progress bars using tqdm. Add docstrings.
```

---

## PROMPT 3 — SVD Pipeline

```
I am building a Fake Review Cartel Detector. I have:
- data/processed/amazon_clean.csv — cleaned Amazon reviews (customer_id, product_id, star_rating)
- data/processed/reviewer_features.csv — behavioral features per reviewer (normalized)

Create a Python script called `svd_pipeline.py` in src/.

Do the following:
1. Build a sparse user × product matrix using scipy.sparse.csr_matrix where rows are customer_ids, columns are product_ids, values are star_ratings. Use integer indices mapped from IDs.
2. Apply TruncatedSVD with n_components=50 from sklearn.decomposition. Print explained variance ratio.
3. Create a combined feature matrix by concatenating the SVD user embeddings with the reviewer behavioral features (align by customer_id index).
4. Apply DBSCAN from sklearn.cluster:
   - First plot a k-distance graph (k=5) to help find optimal eps. Save the plot as data/processed/kdistance_plot.png
   - Use eps=0.5, min_samples=5 as starting values
   - Fit DBSCAN and get cluster labels
5. Print cluster summary: number of clusters found, number of noise points, size of each cluster
6. Save a dataframe with customer_id and cluster_label to data/processed/cluster_labels.csv
7. Create a 2D visualization using PCA (n_components=2), color points by cluster label, save as data/processed/clusters_viz.png

Use scipy, sklearn, pandas, numpy, matplotlib. Add docstrings.
```

---

## PROMPT 4 — XGBoost + AdaBoost Ensemble

```
I am building a Fake Review Cartel Detector. For the classifier I have the Cornell Yelp Deception Dataset — a folder of .txt files organized as:
- op_spam_v1.4/positive_polarity/deceptive_from_MTurk/ (fake positive reviews, 8 fold subfolders)
- op_spam_v1.4/positive_polarity/truthful_from_Web/ (genuine positive reviews, 8 fold subfolders)

Create a Python script called `ensemble_model.py` in src/.

Do the following:
1. Load all .txt files. Label fake=1, genuine=0. Build a dataframe with columns: text, label
2. Create TF-IDF features using TfidfVectorizer(max_features=500, ngram_range=(1,2))
3. Add these hand-crafted features per review:
   - text_length (character count)
   - word_count
   - avg_word_length
   - exclamation_count
   - uppercase_ratio
4. Combine TF-IDF + hand-crafted features into one feature matrix
5. Split 80/20 train/test with stratify=label, random_state=42
6. Train XGBoostClassifier: n_estimators=200, max_depth=4, learning_rate=0.1, use_label_encoder=False, eval_metric='logloss'
7. Train AdaBoostClassifier: n_estimators=200, learning_rate=0.5
8. Create VotingClassifier(estimators=[('xgb', xgb_model), ('ada', ada_model)], voting='soft')
9. Evaluate ensemble on test set:
   - Print accuracy, precision, recall, F1 score
   - Plot confusion matrix heatmap (save as data/processed/confusion_matrix.png)
   - Plot ROC-AUC curve (save as data/processed/roc_curve.png)
10. Save trained models using joblib:
    - models/xgb_model.pkl
    - models/ada_model.pkl
    - models/ensemble_model.pkl
    - models/tfidf_vectorizer.pkl

Use xgboost, sklearn, pandas, numpy, matplotlib, seaborn, joblib. Add docstrings.
```

---

## PROMPT 5 — FastAPI Backend

```
I am building a Fake Review Cartel Detector. I have these processed files:
- data/processed/amazon_clean.csv — cleaned reviews (customer_id, product_id, star_rating, review_body, review_date)
- data/processed/reviewer_features.csv — behavioral features per reviewer
- data/processed/cluster_labels.csv — DBSCAN cluster label per customer_id
- models/ensemble_model.pkl — trained VotingClassifier
- models/tfidf_vectorizer.pkl — fitted TF-IDF vectorizer

Create a FastAPI application in src/api.py.

On startup, load all CSVs and models into memory.

Implement these endpoints:

1. GET /stats
   Returns: total_reviews, unique_reviewers, fake_percentage (estimate from cluster labels where cluster != -1), num_cartels_detected, largest_cartel_size

2. GET /cartels
   Returns a network graph structure:
   {
     "nodes": [{"id": customer_id, "cluster": int, "suspicion_score": float, "avg_rating": float, "review_count": int}],
     "edges": [{"source": customer_id, "target": customer_id, "shared_products": int}]
   }
   Only include reviewers in non-noise clusters (cluster != -1) and edges where shared_products >= 2.
   Limit to top 500 nodes by suspicion_score to keep response size manageable.

3. GET /analyze/product/{product_id}
   Returns: product_id, total_reviews, fake_count, genuine_count, fake_percentage, reviews list with fake_probability per review

4. GET /analyze/reviewer/{reviewer_id}
   Returns: reviewer_id, cluster_label, suspicion_score, all behavioral features, their reviews

5. POST /search with body {"query": str}
   Search reviewer IDs and product IDs containing the query string. Return matching ids.

Add CORS middleware allowing all origins.
Add error handling for missing IDs (return 404).
Add response time logging.

Use fastapi, uvicorn, joblib, pandas, numpy. Add docstrings to all functions.
```

---

## PROMPT 6 — React Network Graph Component

```
I am building a Fake Review Cartel Detector web app in React. Create a component called NetworkGraph.jsx in src/components/.

This component:
1. Accepts props: { nodes, edges } where:
   - nodes: array of {id, cluster, suspicion_score, avg_rating, review_count}
   - edges: array of {source, target, shared_products}
   - onNodeClick: callback function called with node data when a node is clicked

2. Uses D3.js v7 to render a force-directed network graph inside a div with full viewport height
3. Node styling:
   - Cartel nodes (cluster >= 0): red (#ff4444) with a glowing drop-shadow filter, radius proportional to review_count (min 5, max 20)
   - Genuine nodes (cluster == -1): grey (#555555), radius 4
   - On hover: show tooltip with id, suspicion_score, cluster
4. Edge styling:
   - Stroke color: #333333
   - Stroke width proportional to shared_products (min 0.5, max 3)
   - Opacity: 0.4
5. Enable zoom and pan using d3.zoom()
6. On click of a node, call onNodeClick(nodeData)
7. Add a legend in the top-right corner: red circle = cartel member, grey circle = genuine reviewer
8. Background color: #0a0a0a (dark)
9. Use useRef for the SVG element and useEffect for D3 initialization
10. Clean up D3 simulation on component unmount

Import d3 as: import * as d3 from 'd3'
Use functional component with hooks. Do not use class components.
```

---

## PROMPT 7 — React Stats Panel Component

```
I am building a Fake Review Cartel Detector React app. Create a component called StatsPanel.jsx in src/components/.

This component:
1. Fetches stats from GET http://localhost:8000/stats on mount using axios
2. Displays 5 stat cards in a horizontal row:
   - Total Reviews Analyzed
   - Fake Review Percentage (shown as a colored percentage — red if >30%, yellow if >15%, green otherwise)
   - Cartels Detected
   - Largest Cartel Size
   - Unique Reviewers
3. Each card has:
   - Dark background (#111111)
   - White bold number (large, 2rem)
   - Grey label below (small, 0.8rem)
   - Subtle border (#222222)
   - Rounded corners
4. Show a loading skeleton while data is fetching
5. Show an error message if the API call fails

Use axios, React hooks (useState, useEffect). Style with inline styles or CSS modules (no external UI library). Dark theme throughout (#0a0a0a background).
```

---

## PROMPT 8 — React Main App Integration

```
I am building a Fake Review Cartel Detector React app. I have these components already built:
- src/components/NetworkGraph.jsx — D3 force-directed network graph
- src/components/StatsPanel.jsx — platform stats cards
- src/components/ReviewCard.jsx — shows review details with fake probability
- src/components/SearchBar.jsx — search input

Create App.jsx that:
1. On load, fetches cartel network data from GET http://localhost:8000/cartels
2. Renders:
   - Top bar: app title "🕵️ Fake Review Cartel Detector" in white on dark background
   - StatsPanel below the top bar
   - SearchBar below stats
   - Full-width NetworkGraph taking remaining height
   - A side drawer (300px wide) on the right that slides in when a node is clicked
3. When a node is clicked on the graph:
   - Fetch reviewer details from GET http://localhost:8000/analyze/reviewer/{reviewer_id}
   - Show results in the side drawer: reviewer ID, cluster, suspicion score, behavioral features as a list, their reviews as ReviewCards
4. SearchBar: on submit, calls POST http://localhost:8000/search, then highlights matching nodes in the graph by updating a highlightedIds state passed as prop to NetworkGraph
5. Overall dark theme: background #0a0a0a, text white, accent red #ff4444

Use React hooks, axios. Responsive layout using flexbox. No external UI library — plain CSS or inline styles only.
```

---

## PROMPT 9 — Requirements & Project Config Files

```
I am building a Fake Review Cartel Detector project with a Python backend and React frontend.

Create the following files:

1. backend/requirements.txt with exact versions for:
pandas, numpy, scipy, scikit-learn, xgboost, fastapi, uvicorn, joblib, nltk, tqdm, matplotlib, seaborn, jupyter

2. backend/.gitignore that ignores:
__pycache__, .ipynb_checkpoints, venv/, *.pkl, data/raw/, data/processed/, *.pyc, .env

3. frontend/.gitignore that ignores:
node_modules/, build/, .env

4. A root-level .gitignore combining both

5. backend/src/__init__.py (empty file with a module docstring)

6. A Makefile at root level with these commands:
- make setup: creates venv, installs requirements, installs frontend dependencies
- make backend: starts FastAPI server
- make frontend: starts React dev server
- make notebooks: starts Jupyter in backend folder
- make clean: removes __pycache__ and build artifacts

Use Python 3.10+ syntax for all Python files.
```

---

## VIVA PREPARATION — Questions & Answers

Use these when your teacher asks questions:

**Q: Why SVD instead of just using raw features?**
A: The raw user-product matrix is huge and sparse — most users only review a tiny fraction of products. SVD compresses this into dense embeddings that capture latent behavioral similarities between users who review similar product categories, even if they've never reviewed the exact same item. It's the same technique Netflix uses for recommendation.

**Q: Why DBSCAN over K-Means?**
A: K-Means requires you to specify the number of clusters upfront, which we don't know. More importantly, K-Means forces every point into a cluster — so genuine reviewers would be incorrectly assigned to fake clusters. DBSCAN identifies dense regions naturally and marks isolated genuine users as noise (-1), which is exactly what we want.

**Q: Why ensemble instead of just XGBoost?**
A: XGBoost is very strong but struggles with sophisticated fakes — accounts that post slowly, write longer reviews, are older. AdaBoost focuses specifically on misclassified cases and corrects them iteratively. The ensemble combines both perspectives and consistently outperforms either alone.

**Q: How do you handle the lack of labels in Amazon data?**
A: We use a semi-supervised approach. The XGBoost+AdaBoost ensemble is trained on the Cornell Yelp Deception Dataset which has verified human labels. We then apply this trained classifier to Amazon data, using the DBSCAN cluster membership as an additional feature. This is academically valid and actually more realistic than assuming we have labeled Amazon data.

**Q: What does the network graph actually show?**
A: Each node is a reviewer. Edges connect reviewers who reviewed the same products. Cartel clusters are groups of reviewers who are densely connected — same products, same timing, same rating patterns — highlighted in red. You can visually see the difference between scattered genuine reviewers and tight suspicious clusters.
```
