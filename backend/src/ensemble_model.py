"""Train the XGBoost + AdaBoost ensemble for fake review classification."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import AdaBoostClassifier, VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


DEFAULT_DATASET_DIR = Path("data/raw/op_spam_v1.4")
DEFAULT_MODEL_DIR = Path("models")
DEFAULT_PROCESSED_DIR = Path("data/processed")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for ensemble model training."""
    parser = argparse.ArgumentParser(
        description="Train the review-level fake/genuine ensemble classifier."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Root path of the Cornell Yelp deception dataset.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help="Directory for evaluation artifacts.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Directory where trained models should be saved.",
    )
    return parser.parse_args()


def load_cornell_dataset(dataset_dir: Path) -> pd.DataFrame:
    """Load Cornell deceptive and truthful reviews into a dataframe."""
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Cornell dataset directory not found: {dataset_dir}")

    subsets = [
        (dataset_dir / "positive_polarity" / "deceptive_from_MTurk", 1),
        (dataset_dir / "positive_polarity" / "truthful_from_Web", 0),
    ]

    records: list[dict[str, int | str]] = []
    for directory, label in subsets:
        if not directory.exists():
            raise FileNotFoundError(f"Expected dataset subdirectory not found: {directory}")
        for path in sorted(directory.rglob("*.txt")):
            records.append(
                {
                    "text": path.read_text(encoding="utf-8", errors="ignore").strip(),
                    "label": label,
                }
            )

    dataset = pd.DataFrame(records)
    if dataset.empty:
        raise ValueError("Cornell dataset load produced no review texts.")
    return dataset


def build_text_features(texts: pd.Series) -> pd.DataFrame:
    """Create hand-crafted text signals for each review."""
    cleaned = texts.fillna("").astype(str)
    word_counts = cleaned.str.split().str.len().clip(lower=1)
    uppercase_counts = cleaned.apply(lambda text: sum(character.isupper() for character in text))
    alphabetic_counts = cleaned.apply(lambda text: sum(character.isalpha() for character in text))

    features = pd.DataFrame(
        {
            "text_length": cleaned.str.len(),
            "word_count": word_counts,
            "avg_word_length": cleaned.apply(
                lambda text: np.mean([len(token) for token in text.split()]) if text.split() else 0.0
            ),
            "exclamation_count": cleaned.str.count(re.escape("!")),
            "uppercase_ratio": uppercase_counts / alphabetic_counts.replace(0, 1),
        }
    )
    return features.astype(float)


def build_feature_matrix(texts: pd.Series) -> tuple[csr_matrix, TfidfVectorizer]:
    """Create the combined TF-IDF and hand-crafted sparse feature matrix."""
    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2), stop_words="english")
    tfidf = vectorizer.fit_transform(texts.fillna("").astype(str))
    handcrafted = csr_matrix(build_text_features(texts).to_numpy())
    return hstack([tfidf, handcrafted]).tocsr(), vectorizer


def save_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, output_path: Path) -> None:
    """Save a confusion matrix heatmap."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Reds", cbar=False, ax=ax)
    ax.set_title("Confusion Matrix")
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_roc_curve(y_true: np.ndarray, y_prob: np.ndarray, output_path: Path) -> None:
    """Save the ROC curve for the ensemble model."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fpr, tpr, _ = roc_curve(y_true, y_prob)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#ff6b35", linewidth=2, label=f"AUC = {roc_auc_score(y_true, y_prob):.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="#888888")
    ax.set_title("ROC Curve")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def train_models(X_train: csr_matrix, y_train: np.ndarray) -> tuple[XGBClassifier, AdaBoostClassifier, VotingClassifier]:
    """Train the XGBoost, AdaBoost, and ensemble classifiers."""
    xgb_model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    ada_model = AdaBoostClassifier(
        n_estimators=200,
        learning_rate=0.5,
        random_state=42,
    )
    ensemble_model = VotingClassifier(
        estimators=[("xgb", xgb_model), ("ada", ada_model)],
        voting="soft",
    )

    xgb_model.fit(X_train, y_train)
    ada_model.fit(X_train, y_train)
    ensemble_model.fit(X_train, y_train)
    return xgb_model, ada_model, ensemble_model


def save_models(
    model_dir: Path,
    xgb_model: XGBClassifier,
    ada_model: AdaBoostClassifier,
    ensemble_model: VotingClassifier,
    vectorizer: TfidfVectorizer,
) -> None:
    """Persist trained models to disk."""
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(xgb_model, model_dir / "xgb_model.pkl")
    joblib.dump(ada_model, model_dir / "ada_model.pkl")
    joblib.dump(ensemble_model, model_dir / "ensemble_model.pkl")
    joblib.dump(vectorizer, model_dir / "tfidf_vectorizer.pkl")


def main() -> None:
    """Train and evaluate the ensemble classification pipeline."""
    args = parse_args()
    dataset = load_cornell_dataset(args.dataset_dir)
    X, vectorizer = build_feature_matrix(dataset["text"])
    y = dataset["label"].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=42,
    )

    xgb_model, ada_model, ensemble_model = train_models(X_train, y_train)

    y_pred = ensemble_model.predict(X_test)
    y_prob = ensemble_model.predict_proba(X_test)[:, 1]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", zero_division=0
    )
    accuracy = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)

    confusion_matrix_path = args.processed_dir / "confusion_matrix.png"
    roc_curve_path = args.processed_dir / "roc_curve.png"
    save_confusion_matrix(y_test, y_pred, confusion_matrix_path)
    save_roc_curve(y_test, y_prob, roc_curve_path)
    save_models(args.model_dir, xgb_model, ada_model, ensemble_model, vectorizer)

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1: {f1:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    print(f"Saved confusion matrix to {confusion_matrix_path}")
    print(f"Saved ROC curve to {roc_curve_path}")
    print(f"Saved models to {args.model_dir}")


if __name__ == "__main__":
    main()
