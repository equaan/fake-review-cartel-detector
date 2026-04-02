"""SVD and DBSCAN pipeline for reviewer cartel discovery."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.neighbors import NearestNeighbors


DEFAULT_CLEAN_PATH = Path("data/processed/amazon_clean.csv")
DEFAULT_FEATURES_PATH = Path("data/processed/reviewer_features.csv")
DEFAULT_OUTPUT_PATH = Path("data/processed/cluster_labels.csv")
DEFAULT_KDISTANCE_PATH = Path("data/processed/kdistance_plot.png")
DEFAULT_VIZ_PATH = Path("data/processed/clusters_viz.png")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the SVD pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the SVD + DBSCAN cartel detection pipeline."
    )
    parser.add_argument(
        "--clean-data",
        type=Path,
        default=DEFAULT_CLEAN_PATH,
        help="Path to the cleaned Amazon reviews CSV.",
    )
    parser.add_argument(
        "--reviewer-features",
        type=Path,
        default=DEFAULT_FEATURES_PATH,
        help="Path to the reviewer feature matrix CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for the generated cluster labels CSV.",
    )
    parser.add_argument(
        "--kdistance-output",
        type=Path,
        default=DEFAULT_KDISTANCE_PATH,
        help="Path for the saved k-distance plot.",
    )
    parser.add_argument(
        "--viz-output",
        type=Path,
        default=DEFAULT_VIZ_PATH,
        help="Path for the saved PCA cluster visualization.",
    )
    parser.add_argument(
        "--n-components",
        type=int,
        default=50,
        help="Number of latent components to keep for TruncatedSVD.",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=0.5,
        help="DBSCAN epsilon parameter.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="DBSCAN minimum samples parameter.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap on rows loaded from the cleaned review CSV for a faster first pass.",
    )
    return parser.parse_args()


def load_inputs(
    clean_data_path: Path,
    reviewer_features_path: Path,
    max_rows: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load cleaned reviews and reviewer features from disk."""
    if not clean_data_path.exists():
        raise FileNotFoundError(f"Cleaned review file not found: {clean_data_path}")
    if not reviewer_features_path.exists():
        raise FileNotFoundError(f"Reviewer features file not found: {reviewer_features_path}")

    reviews = pd.read_csv(
        clean_data_path,
        nrows=max_rows,
        usecols=["customer_id", "product_id", "star_rating"],
    )
    reviewer_features = pd.read_csv(reviewer_features_path, index_col="customer_id")
    reviews["customer_id"] = reviews["customer_id"].astype(str)
    reviews["product_id"] = reviews["product_id"].astype(str)
    reviewer_features.index = reviewer_features.index.astype(str)
    return reviews, reviewer_features


def build_user_product_matrix(reviews: pd.DataFrame) -> tuple[csr_matrix, pd.Index]:
    """Build a sparse user-by-product rating matrix."""
    required_columns = {"customer_id", "product_id", "star_rating"}
    missing = sorted(required_columns - set(reviews.columns))
    if missing:
        raise ValueError(f"Cleaned reviews missing required columns: {', '.join(missing)}")

    user_codes, user_index = pd.factorize(reviews["customer_id"], sort=True)
    product_codes, _ = pd.factorize(reviews["product_id"], sort=True)
    ratings = pd.to_numeric(reviews["star_rating"], errors="coerce").fillna(0).astype(float)

    matrix = csr_matrix(
        (ratings.to_numpy(), (user_codes, product_codes)),
        shape=(len(user_index), len(pd.unique(product_codes))),
    )
    return matrix, pd.Index(user_index, name="customer_id")


def run_svd(matrix: csr_matrix, customer_index: pd.Index, n_components: int) -> tuple[pd.DataFrame, float]:
    """Apply TruncatedSVD to the sparse rating matrix."""
    max_components = max(2, min(n_components, matrix.shape[0] - 1, matrix.shape[1] - 1))
    svd = TruncatedSVD(n_components=max_components, random_state=42)
    embeddings = svd.fit_transform(matrix)
    explained_variance = float(svd.explained_variance_ratio_.sum())

    columns = [f"svd_component_{index + 1}" for index in range(embeddings.shape[1])]
    embedding_df = pd.DataFrame(embeddings, index=customer_index, columns=columns)
    return embedding_df, explained_variance


def build_combined_features(
    embeddings: pd.DataFrame,
    reviewer_features: pd.DataFrame,
) -> pd.DataFrame:
    """Join latent embeddings with reviewer behavioral features."""
    combined = embeddings.join(reviewer_features, how="inner")
    if combined.empty:
        raise ValueError("No overlapping customer_ids were found between embeddings and reviewer features.")
    return combined


def save_kdistance_plot(features: pd.DataFrame, output_path: Path, k: int = 5) -> None:
    """Create and save the k-distance elbow plot used for DBSCAN tuning."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    neighbors = NearestNeighbors(n_neighbors=k)
    neighbors.fit(features)
    distances, _ = neighbors.kneighbors(features)
    kth_distances = np.sort(distances[:, -1])

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(kth_distances, color="#ff6b35", linewidth=1.5)
    ax.set_title("K-Distance Plot")
    ax.set_xlabel("Sorted samples")
    ax.set_ylabel(f"Distance to {k}th nearest neighbor")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def run_dbscan(features: pd.DataFrame, eps: float, min_samples: int) -> pd.Series:
    """Run DBSCAN over the combined feature matrix."""
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(features)
    return pd.Series(labels, index=features.index, name="cluster_label")


def print_cluster_summary(labels: pd.Series) -> None:
    """Print a concise summary of detected clusters."""
    unique_clusters = sorted(label for label in labels.unique() if label != -1)
    noise_points = int((labels == -1).sum())
    cluster_sizes = labels[labels != -1].value_counts().sort_index()

    print(f"Clusters found: {len(unique_clusters)}")
    print(f"Noise points: {noise_points}")
    if cluster_sizes.empty:
        print("Cluster sizes: none")
    else:
        print("Cluster sizes:")
        for cluster_id, size in cluster_sizes.items():
            print(f"  Cluster {cluster_id}: {int(size)} reviewers")


def save_cluster_viz(features: pd.DataFrame, labels: pd.Series, output_path: Path) -> None:
    """Create and save a 2D PCA visualization of the cluster assignments."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(features)

    fig, ax = plt.subplots(figsize=(10, 7))
    scatter = ax.scatter(
        coords[:, 0],
        coords[:, 1],
        c=labels.to_numpy(),
        cmap="tab20",
        alpha=0.75,
        s=18,
    )
    ax.set_title("Reviewer Clusters (PCA Projection)")
    ax.set_xlabel("PC 1")
    ax.set_ylabel("PC 2")
    legend = ax.legend(*scatter.legend_elements(), title="Cluster", loc="best")
    ax.add_artist(legend)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_cluster_labels(labels: pd.Series, output_path: Path) -> None:
    """Save customer-to-cluster assignments to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels.reset_index().rename(columns={"index": "customer_id"}).to_csv(output_path, index=False)


def main() -> None:
    """Run the SVD + DBSCAN cartel detection workflow."""
    args = parse_args()
    reviews, reviewer_features = load_inputs(
        args.clean_data,
        args.reviewer_features,
        max_rows=args.max_rows,
    )
    matrix, customer_index = build_user_product_matrix(reviews)
    embeddings, explained_variance = run_svd(matrix, customer_index, args.n_components)
    combined_features = build_combined_features(embeddings, reviewer_features)

    save_kdistance_plot(combined_features, args.kdistance_output, k=args.min_samples)
    labels = run_dbscan(combined_features, eps=args.eps, min_samples=args.min_samples)
    save_cluster_labels(labels, args.output)
    save_cluster_viz(combined_features, labels, args.viz_output)

    print(f"Explained variance ratio: {explained_variance:.4f}")
    if args.max_rows is not None:
        print(f"Rows used: {args.max_rows}")
    print(f"Combined feature matrix shape: {combined_features.shape}")
    print_cluster_summary(labels)
    print(f"Saved cluster labels to {args.output}")
    print(f"Saved k-distance plot to {args.kdistance_output}")
    print(f"Saved cluster visualization to {args.viz_output}")


if __name__ == "__main__":
    main()
