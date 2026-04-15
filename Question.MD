Direct Answer (Short Version)
Companies can use this by plugging in their own review export in the same schema, running our preprocessing + feature + clustering pipeline, optionally retraining the classifier on their labeled fraud data (or using the current model), and then launching the API/dashboard to inspect suspicious reviewer networks and review-level risk scores.

If Examiner Asks “How exactly will a company use this?”

Data input:
Company exports review table as CSV.
Required columns are like:
customer_id, product_id, star_rating, review_date, review_body, verified_purchase
Put file in backend raw data folder and run preprocess script.
Pipeline run:
preprocess.py cleans and standardizes raw reviews.
feature_engineering.py builds reviewer behavior signals.
svd_pipeline.py creates embeddings + DBSCAN cluster labels (cartel detection).
ensemble_model.py gives fake/genuine probabilities (review-level model).
Training options:
Option A (quick deployment): use existing trained model and run inference.
Option B (best production): retrain on company’s own labeled fraud data to adapt to their platform behavior, then redeploy model artifacts.
Output for company:
API endpoints:
platform stats
suspicious network graph
reviewer drill-down
product drill-down
search
Frontend shows:
suspicious reviewer clusters
risk/suspicion score
connected behavior patterns
detailed reviewer/product evidence
Answer to “Right now whose output are we seeing?”
You are primarily seeing Amazon dataset output in the dashboard/network:

Nodes/edges/clusters/stats come from Amazon processed reviews + clustering artifacts.
The classifier itself was trained using the labeled fake-review dataset (your current project file replacing Cornell folder flow), then used to score review suspiciousness.

So:

Amazon data = unsupervised network/cartel discovery + live graph output.
Labeled dataset = supervised fake/genuine learning for probability scoring.
Clear Role of the Two Datasets

Amazon dataset role:
Large-scale real-world behavior graph.
Used for:
reviewer features
SVD latent structure
DBSCAN cluster/cartel detection
API graph and reviewer/product exploration
Labeled dataset role:
Ground truth for supervised learning.
Used for:
training XGBoost/AdaBoost/Voting model
generating fake probability scores
model metrics (accuracy/precision/recall/F1/ROC-AUC)
This is why you call it a hybrid / semi-supervised practical system:

Unsupervised for cartel structure discovery
Supervised for review fraud probability
One-line production architecture answer
“Company data goes through our unsupervised cartel miner and supervised fraud scorer; results are served by FastAPI and visualized as an evidence graph for trust/risk teams.”