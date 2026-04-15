"""FastAPI application for the fake review cartel detector."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"


class SearchRequest(BaseModel):
    """Payload used by the search endpoint."""

    query: str


class AppState:
    """In-memory container for processed datasets used by the API."""

    def __init__(self) -> None:
        self.reviews = self._load_csv(
            DATA_DIR / "amazon_clean.csv",
            parse_dates=["review_date"],
        )
        self.reviewer_features = self._load_csv(
            DATA_DIR / "reviewer_features.csv",
            index_col="customer_id",
        )
        self.cluster_labels = self._load_csv(DATA_DIR / "cluster_labels.csv")
        self.predictions = self._load_csv(DATA_DIR / "predictions.csv")

        if not self.cluster_labels.empty and "customer_id" in self.cluster_labels.columns:
            self.cluster_labels = self.cluster_labels.set_index("customer_id")

        self._enrich_reviews()

    @staticmethod
    def _load_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
        """Load a CSV if present, otherwise return an empty dataframe."""
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path, **kwargs)

    def _enrich_reviews(self) -> None:
        """Attach cluster and feature-derived fields onto the review dataframe."""
        if self.reviews.empty:
            return

        reviews = self.reviews.copy()

        if not self.cluster_labels.empty and "cluster_label" in self.cluster_labels.columns:
            reviews = reviews.merge(
                self.cluster_labels[["cluster_label"]],
                left_on="customer_id",
                right_index=True,
                how="left",
            )
        else:
            reviews["cluster_label"] = -1

        if not self.reviewer_features.empty:
            selected_columns = [
                col
                for col in ("avg_rating", "review_burst_score", "review_text_similarity")
                if col in self.reviewer_features.columns
            ]
            if selected_columns:
                reviews = reviews.merge(
                    self.reviewer_features[selected_columns],
                    left_on="customer_id",
                    right_index=True,
                    how="left",
                )

        reviews = self._merge_predictions(reviews)
        if "fake_probability" not in reviews.columns:
            reviews["fake_probability"] = reviews.apply(self._estimate_fake_probability, axis=1)

        self.reviews = reviews

    def _merge_predictions(self, reviews: pd.DataFrame) -> pd.DataFrame:
        """Prefer saved model predictions when they are available."""
        if self.predictions.empty:
            return reviews

        prediction_frame = self.predictions.copy()
        if "fake_probability" not in prediction_frame.columns:
            return reviews

        # The prediction export is generated from the same cleaned CSV in row order,
        # so positional alignment is the safest merge when natural keys are not unique.
        if len(prediction_frame) == len(reviews):
            aligned = reviews.copy().reset_index(drop=True)
            aligned["fake_probability"] = pd.to_numeric(
                prediction_frame["fake_probability"],
                errors="coerce",
            )
            fallback_mask = aligned["fake_probability"].isna()
            if fallback_mask.any():
                aligned.loc[fallback_mask, "fake_probability"] = aligned.loc[fallback_mask].apply(
                    self._estimate_fake_probability,
                    axis=1,
                )
            return aligned

        required_columns = {"customer_id", "product_id", "review_date"}
        if not required_columns.issubset(set(prediction_frame.columns)):
            return reviews

        reviews = reviews.copy()
        prediction_frame["customer_id"] = prediction_frame["customer_id"].astype(str)
        prediction_frame["product_id"] = prediction_frame["product_id"].astype(str)
        prediction_frame["review_date"] = pd.to_datetime(prediction_frame["review_date"], errors="coerce")
        reviews["customer_id"] = reviews["customer_id"].astype(str)
        reviews["product_id"] = reviews["product_id"].astype(str)
        reviews["review_date"] = pd.to_datetime(reviews["review_date"], errors="coerce")

        prediction_frame = (
            prediction_frame.dropna(subset=["review_date"])
            .groupby(["customer_id", "product_id", "review_date"], as_index=False)["fake_probability"]
            .mean()
        )
        merged = reviews.merge(
            prediction_frame,
            on=["customer_id", "product_id", "review_date"],
            how="left",
        )
        fallback_mask = merged["fake_probability"].isna()
        if fallback_mask.any():
            merged.loc[fallback_mask, "fake_probability"] = merged.loc[fallback_mask].apply(
                self._estimate_fake_probability,
                axis=1,
            )
        return merged

    @staticmethod
    def _estimate_fake_probability(row: pd.Series) -> float:
        """Create a fallback suspicion estimate before the real model is wired in."""
        score = 0.15
        if row.get("cluster_label", -1) != -1:
            score += 0.4
        if float(row.get("review_burst_score", 0) or 0) > 1.5:
            score += 0.2
        if float(row.get("review_text_similarity", 0) or 0) > 0.5:
            score += 0.15
        if float(row.get("star_rating", 0) or 0) >= 5:
            score += 0.1
        return round(min(score, 0.99), 3)


state = AppState()

app = FastAPI(title="Fake Review Cartel Detector API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_response_time(request, call_next):  # type: ignore[no-untyped-def]
    """Attach simple request timing information to each response."""
    start = perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{perf_counter() - start:.4f}"
    return response


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Return a simple health response."""
    return {"status": "ok"}


@app.get("/stats")
def get_stats() -> dict[str, Any]:
    """Return platform-level summary stats from the loaded processed files."""
    if state.reviews.empty:
        return {
            "total_reviews": 0,
            "unique_reviewers": 0,
            "fake_percentage": 0.0,
            "num_cartels_detected": 0,
            "largest_cartel_size": 0,
        }

    cluster_series = state.reviews["cluster_label"].fillna(-1)
    cartel_reviews = state.reviews.loc[cluster_series != -1]
    cluster_counts = cartel_reviews.groupby("cluster_label")["customer_id"].nunique()

    return {
        "total_reviews": int(len(state.reviews)),
        "unique_reviewers": int(state.reviews["customer_id"].nunique()),
        "fake_percentage": round(float((cluster_series != -1).mean() * 100), 2),
        "num_cartels_detected": int(cluster_counts.index.nunique()),
        "largest_cartel_size": int(cluster_counts.max()) if not cluster_counts.empty else 0,
    }


@app.get("/cartels")
def get_cartels() -> dict[str, list[dict[str, Any]]]:
    """Return graph-ready cartel node and edge data."""
    if state.reviews.empty:
        return {"nodes": [], "edges": []}

    cartel_reviews = state.reviews.loc[state.reviews["cluster_label"].fillna(-1) != -1].copy()
    if cartel_reviews.empty:
        return {"nodes": [], "edges": []}

    reviewer_summary = (
        cartel_reviews.groupby(["customer_id", "cluster_label"], as_index=False)
        .agg(
            suspicion_score=("fake_probability", "mean"),
            avg_rating=("star_rating", "mean"),
            review_count=("product_id", "count"),
        )
        .sort_values("suspicion_score", ascending=False)
        .head(500)
    )

    allowed_reviewers = set(reviewer_summary["customer_id"])
    filtered_reviews = cartel_reviews[cartel_reviews["customer_id"].isin(allowed_reviewers)]
    product_groups = filtered_reviews.groupby("product_id")["customer_id"].apply(lambda s: sorted(set(s)))

    edge_weights: dict[tuple[str, str], int] = {}
    for reviewers in product_groups:
        for index, source in enumerate(reviewers):
            for target in reviewers[index + 1 :]:
                key = (source, target)
                edge_weights[key] = edge_weights.get(key, 0) + 1

    edges = [
        {"source": str(source), "target": str(target), "shared_products": weight}
        for (source, target), weight in edge_weights.items()
        if weight >= 1
    ]

    nodes = [
        {
            "id": str(row.customer_id),
            "cluster": int(row.cluster_label),
            "suspicion_score": round(float(row.suspicion_score), 3),
            "avg_rating": round(float(row.avg_rating), 2),
            "review_count": int(row.review_count),
        }
        for row in reviewer_summary.itertuples(index=False)
    ]
    return {"nodes": nodes, "edges": edges}


@app.get("/analyze/product/{product_id}")
def analyze_product(product_id: str) -> dict[str, Any]:
    """Return all reviews and summary metrics for a product."""
    if state.reviews.empty:
        raise HTTPException(status_code=404, detail="Processed review data is not loaded yet.")

    product_reviews = state.reviews.loc[state.reviews["product_id"].astype(str) == str(product_id)].copy()
    if product_reviews.empty:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")

    fake_mask = product_reviews["fake_probability"] >= 0.5
    reviews = []
    for _, review in product_reviews.sort_values("review_date", ascending=False).iterrows():
        star_rating = int(review["star_rating"]) if pd.notna(review.get("star_rating")) else 0
        verified_purchase = (
            int(review.get("verified_purchase", 0))
            if pd.notna(review.get("verified_purchase", 0))
            else 0
        )
        cluster_label = int(review.get("cluster_label", -1)) if pd.notna(review.get("cluster_label")) else -1
        reviews.append(
            {
                "customer_id": review["customer_id"],
                "star_rating": star_rating,
                "review_date": str(review["review_date"]),
                "review_body": review.get("review_body", ""),
                "verified_purchase": verified_purchase,
                "cluster_label": cluster_label,
                "fake_probability": round(float(review["fake_probability"]), 3),
            }
        )

    return {
        "product_id": product_id,
        "total_reviews": int(len(product_reviews)),
        "fake_count": int(fake_mask.sum()),
        "genuine_count": int((~fake_mask).sum()),
        "fake_percentage": round(float(fake_mask.mean() * 100), 2),
        "reviews": reviews,
    }


@app.get("/analyze/reviewer/{reviewer_id}")
def analyze_reviewer(reviewer_id: str) -> dict[str, Any]:
    """Return reviewer-level features and all matching reviews."""
    if state.reviews.empty:
        raise HTTPException(status_code=404, detail="Processed review data is not loaded yet.")

    reviewer_reviews = state.reviews.loc[state.reviews["customer_id"].astype(str) == str(reviewer_id)].copy()
    if reviewer_reviews.empty:
        raise HTTPException(status_code=404, detail=f"Reviewer '{reviewer_id}' not found.")

    feature_payload: dict[str, Any] = {}
    if not state.reviewer_features.empty and reviewer_id in state.reviewer_features.index:
        feature_row = state.reviewer_features.loc[reviewer_id]
        feature_payload = {
            key: round(float(value), 4)
            for key, value in feature_row.to_dict().items()
            if pd.notna(value)
        }

    cluster_label = int(reviewer_reviews["cluster_label"].fillna(-1).iloc[0])
    suspicion_score = round(float(reviewer_reviews["fake_probability"].mean()), 3)

    reviews = [
        {
            "product_id": row["product_id"],
            "star_rating": int(row["star_rating"]),
            "review_date": str(row["review_date"]),
            "review_body": row.get("review_body", ""),
            "fake_probability": round(float(row["fake_probability"]), 3),
        }
        for _, row in reviewer_reviews.sort_values("review_date", ascending=False).iterrows()
    ]

    return {
        "reviewer_id": reviewer_id,
        "cluster_label": cluster_label,
        "suspicion_score": suspicion_score,
        "features": feature_payload,
        "reviews": reviews,
    }


@app.post("/search")
def search_entities(payload: SearchRequest) -> dict[str, list[str]]:
    """Search product IDs and reviewer IDs that contain the query string."""
    query = payload.query.strip().lower()
    if not query:
        return {"products": [], "reviewers": []}

    if state.reviews.empty:
        return {"products": [], "reviewers": []}

    product_ids = sorted(
        {
            str(product_id)
            for product_id in state.reviews["product_id"].dropna().astype(str).unique()
            if query in product_id.lower()
        }
    )[:20]
    reviewer_ids = sorted(
        {
            str(customer_id)
            for customer_id in state.reviews["customer_id"].dropna().astype(str).unique()
            if query in customer_id.lower()
        }
    )[:20]

    return {"products": product_ids, "reviewers": reviewer_ids}
