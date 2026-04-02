"""Feature engineering utilities for reviewer-level behavioral signals."""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm


FEATURE_COLUMNS = [
    "avg_rating",
    "rating_variance",
    "review_burst_score",
    "verified_purchase_ratio",
    "unique_products_reviewed",
    "review_text_length_avg",
    "review_text_similarity",
]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for feature generation."""
    parser = argparse.ArgumentParser(
        description="Create reviewer-level behavioral features from cleaned Amazon reviews."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/amazon_clean.csv"),
        help="Path to the cleaned Amazon reviews CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/reviewer_features.csv"),
        help="Path for the generated reviewer feature CSV.",
    )
    return parser.parse_args()


def load_reviews(path: Path) -> pd.DataFrame:
    """Load the cleaned review dataset and ensure the core columns exist."""
    if not path.exists():
        raise FileNotFoundError(f"Cleaned review file not found: {path}")

    df = pd.read_csv(path, parse_dates=["review_date"])
    required_columns = {
        "customer_id",
        "product_id",
        "star_rating",
        "review_date",
        "review_body",
        "verified_purchase",
    }
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"Input file is missing required columns: {', '.join(missing)}")
    return df


def compute_burst_score(review_dates: pd.Series, window: str = "48h") -> int:
    """Return the maximum number of reviews inside a rolling time window."""
    timestamps = review_dates.sort_values()
    if timestamps.empty:
        return 0

    max_reviews = 0
    left = 0
    window_delta = pd.Timedelta(window)
    values = timestamps.to_list()

    for right, current_time in enumerate(values):
        while current_time - values[left] > window_delta:
            left += 1
        max_reviews = max(max_reviews, right - left + 1)

    return max_reviews


def compute_text_similarity(reviews: list[str]) -> float:
    """Estimate self-similarity across a reviewer's texts using TF-IDF cosine similarity."""
    if len(reviews) < 3:
        return 0.5

    vectorizer = TfidfVectorizer(stop_words="english", max_features=200)
    matrix = vectorizer.fit_transform(reviews)
    similarities = cosine_similarity(matrix)
    upper_triangle = similarities[np.triu_indices_from(similarities, k=1)]
    return float(upper_triangle.mean()) if upper_triangle.size else 0.5


def build_reviewer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate review-level data into reviewer-level behavioral features."""
    grouped = df.groupby("customer_id", sort=False)
    rows: list[dict[str, float | str]] = []

    for customer_id, group in tqdm(grouped, desc="Building reviewer features"):
        review_bodies = group["review_body"].fillna("").astype(str).tolist()
        rows.append(
            {
                "customer_id": customer_id,
                "avg_rating": float(group["star_rating"].mean()),
                "rating_variance": float(group["star_rating"].std(ddof=0) or 0.0),
                "review_burst_score": float(compute_burst_score(group["review_date"])),
                "verified_purchase_ratio": float(group["verified_purchase"].mean()),
                "unique_products_reviewed": float(group["product_id"].nunique()),
                "review_text_length_avg": float(group["review_body"].fillna("").str.len().mean()),
                "review_text_similarity": compute_text_similarity(review_bodies),
            }
        )

    features = pd.DataFrame(rows).set_index("customer_id")
    scaler = StandardScaler()
    features[FEATURE_COLUMNS] = scaler.fit_transform(features[FEATURE_COLUMNS])
    return features


def main() -> None:
    """Generate reviewer features and save them as a CSV."""
    args = parse_args()
    reviews_df = load_reviews(args.input)
    features_df = build_reviewer_features(reviews_df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(args.output)
    print(f"Saved reviewer features to {args.output}")


if __name__ == "__main__":
    main()
