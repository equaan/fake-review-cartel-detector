"""Feature engineering utilities for reviewer-level behavioral signals."""

from __future__ import annotations

import argparse
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
    "account_age_at_first_review",
    "product_overlap_ratio",
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
    parser.add_argument(
        "--overlap-sample-size",
        type=int,
        default=1000,
        help="Number of reviewers to sample when estimating product overlap ratio.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap on rows loaded from the cleaned review CSV for a faster first pass.",
    )
    return parser.parse_args()


def load_reviews(path: Path, max_rows: int | None = None) -> pd.DataFrame:
    """Load the cleaned review dataset and ensure the core columns exist."""
    if not path.exists():
        raise FileNotFoundError(f"Cleaned review file not found: {path}")

    df = pd.read_csv(
        path,
        nrows=max_rows,
        parse_dates=["review_date"],
        usecols=[
            "customer_id",
            "product_id",
            "star_rating",
            "review_date",
            "review_body",
            "verified_purchase",
        ],
    )
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

    df["customer_id"] = df["customer_id"].astype(str)
    df["product_id"] = df["product_id"].astype(str)
    df["review_body"] = df["review_body"].fillna("").astype(str)
    return df


def compute_burst_score(review_dates: pd.Series, window: str = "48h") -> int:
    """Return the maximum number of reviews inside a rolling time window."""
    timestamps = review_dates.dropna().sort_values()
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


def compute_text_similarity(reviews: list[str], max_reviews: int = 20) -> float:
    """Estimate self-similarity across a reviewer's texts using TF-IDF cosine similarity."""
    filtered_reviews = [review for review in reviews if review]
    if len(filtered_reviews) < 3:
        return 0.5

    if len(filtered_reviews) > max_reviews:
        filtered_reviews = filtered_reviews[:max_reviews]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=200)
    try:
        matrix = vectorizer.fit_transform(filtered_reviews)
    except ValueError:
        return 0.5
    similarities = cosine_similarity(matrix)
    upper_triangle = similarities[np.triu_indices_from(similarities, k=1)]
    return float(upper_triangle.mean()) if upper_triangle.size else 0.5


def compute_product_overlap_ratios(
    df: pd.DataFrame,
    sample_size: int = 1000,
    random_state: int = 42,
) -> dict[str, float]:
    """Estimate product overlap ratio for a sampled subset of reviewers."""
    unique_reviewers = pd.Series(df["customer_id"].unique())
    if unique_reviewers.empty:
        return {}

    sampled_reviewers = unique_reviewers.sample(
        n=min(sample_size, len(unique_reviewers)),
        random_state=random_state,
    )
    sampled_df = df[df["customer_id"].isin(set(sampled_reviewers))]
    sampled_sets = (
        sampled_df.groupby("customer_id")["product_id"]
        .agg(lambda values: set(values))
        .to_dict()
    )

    reviewer_ids = list(sampled_sets.keys())
    overlap_ratios = {reviewer_id: 0.0 for reviewer_id in reviewer_ids}

    for index, reviewer_id in enumerate(tqdm(reviewer_ids, desc="Estimating product overlap")):
        source_products = sampled_sets[reviewer_id]
        if not source_products:
            continue

        best_ratio = 0.0
        for other_id in reviewer_ids[index + 1 :]:
            target_products = sampled_sets[other_id]
            if not target_products:
                continue

            shared_products = len(source_products & target_products)
            if shared_products == 0:
                continue

            source_ratio = shared_products / len(source_products)
            target_ratio = shared_products / len(target_products)
            best_ratio = max(best_ratio, source_ratio)
            overlap_ratios[other_id] = max(overlap_ratios[other_id], target_ratio)

        overlap_ratios[reviewer_id] = max(overlap_ratios[reviewer_id], best_ratio)

    return overlap_ratios


def compute_text_similarity_map(df: pd.DataFrame) -> dict[str, float]:
    """Compute text self-similarity only for reviewers with enough reviews to matter."""
    review_counts = df.groupby("customer_id").size()
    eligible_reviewers = review_counts[review_counts >= 3].index
    if len(eligible_reviewers) == 0:
        return {}

    eligible_df = df[df["customer_id"].isin(set(eligible_reviewers))]
    review_lists = eligible_df.groupby("customer_id")["review_body"].agg(list)

    similarities: dict[str, float] = {}
    for customer_id, reviews in tqdm(review_lists.items(), total=len(review_lists), desc="Computing text similarity"):
        similarities[customer_id] = compute_text_similarity(reviews)
    return similarities


def compute_burst_scores(df: pd.DataFrame) -> dict[str, float]:
    """Compute reviewer burst scores with a sliding time window."""
    date_groups = df.groupby("customer_id")["review_date"]
    burst_scores: dict[str, float] = {}
    for customer_id, review_dates in tqdm(date_groups, desc="Computing burst scores"):
        burst_scores[customer_id] = float(compute_burst_score(review_dates))
    return burst_scores


def build_reviewer_features(df: pd.DataFrame, overlap_sample_size: int = 1000) -> pd.DataFrame:
    """Aggregate review-level data into reviewer-level behavioral features."""
    dataset_start = df["review_date"].min()
    grouped = df.groupby("customer_id", sort=False)

    aggregated = grouped.agg(
        avg_rating=("star_rating", "mean"),
        rating_variance=("star_rating", lambda series: float(series.std(ddof=0) or 0.0)),
        verified_purchase_ratio=("verified_purchase", "mean"),
        unique_products_reviewed=("product_id", "nunique"),
        review_text_length_avg=("review_body", lambda series: float(series.str.len().mean())),
        first_review_date=("review_date", "min"),
    )

    aggregated["account_age_at_first_review"] = (
        aggregated["first_review_date"] - dataset_start
    ).dt.days.astype(float)
    aggregated = aggregated.drop(columns=["first_review_date"])

    aggregated["review_burst_score"] = pd.Series(compute_burst_scores(df))
    aggregated["product_overlap_ratio"] = (
        pd.Series(compute_product_overlap_ratios(df, sample_size=overlap_sample_size))
        .reindex(aggregated.index)
        .fillna(0.0)
    )
    aggregated["review_text_similarity"] = (
        pd.Series(compute_text_similarity_map(df))
        .reindex(aggregated.index)
        .fillna(0.5)
    )

    aggregated = aggregated[FEATURE_COLUMNS].fillna(0.0)
    scaler = StandardScaler()
    aggregated[FEATURE_COLUMNS] = scaler.fit_transform(aggregated[FEATURE_COLUMNS])
    return aggregated


def main() -> None:
    """Generate reviewer features and save them as a CSV."""
    args = parse_args()
    reviews_df = load_reviews(args.input, max_rows=args.max_rows)
    features_df = build_reviewer_features(
        reviews_df,
        overlap_sample_size=args.overlap_sample_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(args.output)

    suspicious_preview = (
        features_df.sort_values(
            by=["review_burst_score", "review_text_similarity"],
            ascending=False,
        )
        .head(10)
    )
    print(f"Saved reviewer features to {args.output}")
    if args.max_rows is not None:
        print(f"Rows used: {args.max_rows}")
    print(f"Feature matrix shape: {features_df.shape}")
    print("Top 10 suspicious reviewers by burst score:")
    print(suspicious_preview[["review_burst_score", "review_text_similarity"]].to_string())


if __name__ == "__main__":
    main()
