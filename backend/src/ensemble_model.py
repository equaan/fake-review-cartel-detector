"""Train the XGBoost + AdaBoost ensemble for fake review classification."""

from __future__ import annotations

import argparse
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


DEFAULT_DATASET_CSV = Path("data/raw/fake reviews dataset.csv")
DEFAULT_AMAZON_CLEAN_CSV = Path("data/processed/amazon_clean.csv")
DEFAULT_MODEL_DIR = Path("models")
DEFAULT_PROCESSED_DIR = Path("data/processed")
LABEL_MAP = {
    "CG": 1,
    "OR": 0,
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for ensemble model training."""
    parser = argparse.ArgumentParser(
        description="Train the review-level fake/genuine ensemble classifier."
    )
    parser.add_argument(
        "--dataset-csv",
        type=Path,
        default=DEFAULT_DATASET_CSV,
        help="Path to the labeled fake review CSV dataset.",
    )
    parser.add_argument(
        "--amazon-clean-csv",
        type=Path,
        default=DEFAULT_AMAZON_CLEAN_CSV,
        help="Optional cleaned Amazon review CSV used for inference after training.",
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


def load_labeled_dataset(dataset_csv: Path) -> pd.DataFrame:
    """Load the project's labeled fake review CSV into a normalized dataframe."""
    if not dataset_csv.exists():
        raise FileNotFoundError(f"Labeled dataset CSV not found: {dataset_csv}")

    dataset = pd.read_csv(dataset_csv)
    required_columns = {"label", "text_"}
    missing = sorted(required_columns - set(dataset.columns))
    if missing:
        raise ValueError(f"Labeled dataset is missing required columns: {', '.join(missing)}")

    dataset = dataset.copy()
    dataset["text"] = dataset["text_"].fillna("").astype(str).str.strip()
    dataset["label_name"] = dataset["label"].astype(str).str.strip().str.upper()
    unknown_labels = sorted(set(dataset["label_name"].unique()) - set(LABEL_MAP))
    if unknown_labels:
        raise ValueError(f"Unsupported labels found in dataset: {', '.join(unknown_labels)}")

    dataset["label"] = dataset["label_name"].map(LABEL_MAP).astype(int)
    dataset = dataset.loc[dataset["text"] != ""].reset_index(drop=True)
    if dataset.empty:
        raise ValueError("Labeled dataset load produced no usable review texts.")
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
            "exclamation_count": cleaned.str.count("!"),
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


def transform_feature_matrix(texts: pd.Series, vectorizer: TfidfVectorizer) -> csr_matrix:
    """Transform new review texts using the trained feature pipeline."""
    tfidf = vectorizer.transform(texts.fillna("").astype(str))
    handcrafted = csr_matrix(build_text_features(texts).to_numpy())
    return hstack([tfidf, handcrafted]).tocsr()


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


def save_labeled_feature_export(
    dataset: pd.DataFrame,
    vectorizer: TfidfVectorizer,
    output_path: Path,
) -> None:
    """Persist a compact labeled feature export for the rest of the project."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tfidf = vectorizer.transform(dataset["text"])
    tfidf_feature_names = vectorizer.get_feature_names_out()
    top_feature_count = min(50, len(tfidf_feature_names))
    top_features = tfidf[:, :top_feature_count].toarray()

    feature_export = pd.DataFrame(
        top_features,
        columns=[f"tfidf_{name}" for name in tfidf_feature_names[:top_feature_count]],
    )
    feature_export = pd.concat(
        [
            dataset[["category", "rating", "label_name", "text"]].reset_index(drop=True),
            build_text_features(dataset["text"]).reset_index(drop=True),
            feature_export,
        ],
        axis=1,
    )
    feature_export.to_csv(output_path, index=False)


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


def run_amazon_inference(
    amazon_clean_csv: Path,
    vectorizer: TfidfVectorizer,
    ensemble_model: VotingClassifier,
    output_path: Path,
) -> Path | None:
    """Run inference on cleaned Amazon reviews and save review-level predictions."""
    if not amazon_clean_csv.exists():
        print(f"Skipping Amazon inference because cleaned review file was not found: {amazon_clean_csv}")
        return None

    amazon_reviews = pd.read_csv(
        amazon_clean_csv,
        usecols=[
            "customer_id",
            "product_id",
            "review_date",
            "star_rating",
            "review_body",
            "verified_purchase",
        ],
    )
    amazon_reviews["review_body"] = amazon_reviews["review_body"].fillna("").astype(str)
    X_amazon = transform_feature_matrix(amazon_reviews["review_body"], vectorizer)
    probabilities = ensemble_model.predict_proba(X_amazon)[:, 1]
    predictions = ensemble_model.predict(X_amazon)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_df = amazon_reviews.copy()
    export_df["fake_probability"] = np.round(probabilities, 6)
    export_df["predicted_label"] = predictions.astype(int)
    export_df.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    """Train and evaluate the ensemble classification pipeline."""
    args = parse_args()
    dataset = load_labeled_dataset(args.dataset_csv)
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
    labeled_features_path = args.processed_dir / "cornell_features.csv"
    predictions_path = args.processed_dir / "predictions.csv"
    save_confusion_matrix(y_test, y_pred, confusion_matrix_path)
    save_roc_curve(y_test, y_prob, roc_curve_path)
    save_labeled_feature_export(dataset, vectorizer, labeled_features_path)
    save_models(args.model_dir, xgb_model, ada_model, ensemble_model, vectorizer)
    amazon_predictions_path = run_amazon_inference(
        args.amazon_clean_csv,
        vectorizer,
        ensemble_model,
        predictions_path,
    )

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1: {f1:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    print(f"Saved labeled feature export to {labeled_features_path}")
    print(f"Saved confusion matrix to {confusion_matrix_path}")
    print(f"Saved ROC curve to {roc_curve_path}")
    print(f"Saved models to {args.model_dir}")
    if amazon_predictions_path is not None:
        print(f"Saved Amazon predictions to {amazon_predictions_path}")


if __name__ == "__main__":
    main()
