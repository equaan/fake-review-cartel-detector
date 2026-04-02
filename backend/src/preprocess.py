"""Data loading and preprocessing for Amazon review datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = [
    "customer_id",
    "product_id",
    "star_rating",
    "review_date",
    "review_body",
    "verified_purchase",
]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the preprocessing script."""
    parser = argparse.ArgumentParser(
        description="Clean a raw Amazon reviews CSV into a processed dataset."
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        help="Path to the raw Amazon reviews CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/amazon_clean.csv"),
        help="Where to save the cleaned CSV.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=10_000,
        help="Number of rows to load per chunk.",
    )
    return parser.parse_args()


def validate_columns(columns: Iterable[str]) -> None:
    """Ensure the input CSV contains the columns required by the pipeline."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(columns))
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Input file is missing required columns: {missing_str}")


def clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Apply the project's cleaning rules to a single data chunk."""
    cleaned = chunk.loc[:, [col for col in REQUIRED_COLUMNS if col in chunk.columns]].copy()
    cleaned = cleaned.dropna(subset=["customer_id", "product_id", "star_rating"])

    cleaned["star_rating"] = pd.to_numeric(cleaned["star_rating"], errors="coerce")
    cleaned = cleaned.dropna(subset=["star_rating"])
    cleaned["star_rating"] = cleaned["star_rating"].astype(int)

    cleaned["review_date"] = pd.to_datetime(cleaned["review_date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["review_date"])

    cleaned["verified_purchase"] = (
        cleaned["verified_purchase"]
        .astype(str)
        .str.strip()
        .str.upper()
        .map({"Y": 1, "N": 0})
        .fillna(0)
        .astype(int)
    )

    cleaned["review_body"] = (
        cleaned["review_body"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    )
    return cleaned


def preprocess_reviews(input_csv: Path, output_csv: Path, chunksize: int = 10_000) -> pd.DataFrame:
    """Load, clean, and save the Amazon review dataset."""
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    cleaned_chunks: list[pd.DataFrame] = []
    reader = pd.read_csv(input_csv, chunksize=chunksize)

    for index, chunk in enumerate(reader):
        if index == 0:
            validate_columns(chunk.columns)
        cleaned_chunks.append(clean_chunk(chunk))

    if not cleaned_chunks:
        raise ValueError("No rows were loaded from the input CSV.")

    cleaned_df = pd.concat(cleaned_chunks, ignore_index=True)
    cleaned_df.to_csv(output_csv, index=False)
    return cleaned_df


def print_summary(df: pd.DataFrame) -> None:
    """Print a compact summary of the cleaned dataset."""
    total_reviews = len(df)
    unique_reviewers = df["customer_id"].nunique()
    unique_products = df["product_id"].nunique()
    start_date = df["review_date"].min().date()
    end_date = df["review_date"].max().date()

    print(f"Total reviews: {total_reviews}")
    print(f"Unique reviewers: {unique_reviewers}")
    print(f"Unique products: {unique_products}")
    print(f"Date range: {start_date} -> {end_date}")


def main() -> None:
    """Run the preprocessing pipeline from the command line."""
    args = parse_args()
    cleaned_df = preprocess_reviews(args.input_csv, args.output, args.chunksize)
    print_summary(cleaned_df)


if __name__ == "__main__":
    main()
