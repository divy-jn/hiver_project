"""
Phase 7: TF-IDF + Logistic Regression baseline.

Trains on clustered training data, evaluates on golden set.

Produces:
  reports/tables/tfidf_results.json
  reports/figures/confusion_matrix.png
"""

import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.model_selection import cross_val_score
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, classification_report,
                             confusion_matrix)
from sklearn.pipeline import Pipeline
import joblib
from src.config import DATA_PROCESSED, DATA_GOLDEN, TABLES, FIGURES, RANDOM_SEED, ensure_dirs


def load_training_data():
    """Load training data from the explicit training set."""
    path = DATA_PROCESSED / "training_set.csv"
    if not path.exists():
        print("ERROR: Run create_training_set first.")
        sys.exit(1)
        
    df = pd.read_csv(path)
    
    # Optional sanity check: ensure no golden threads leaked here
    golden_path = DATA_GOLDEN / "golden_set.csv"
    if golden_path.exists():
        golden = pd.read_csv(golden_path)
        golden_threads = set(golden["thread_id"].dropna().astype(str))
        train_threads = set(df["thread_id"].dropna().astype(str))
        leak = train_threads.intersection(golden_threads)
        if leak:
            print(f"CRITICAL ERROR: {len(leak)} golden threads found in training set!")
            sys.exit(1)
            
    return df["text"].tolist(), df["intent"].tolist()


def load_golden():
    path = DATA_GOLDEN / "golden_set.csv"
    return pd.read_csv(path)


def train_and_evaluate():
    """Train TF-IDF + LR, evaluate on golden set."""
    print("Loading training data...")
    train_texts, train_intents = load_training_data()
    print(f"Training samples: {len(train_texts)}")

    golden = load_golden()
    test_texts = golden["text"].tolist()
    test_intents = golden["intent"].tolist()
    print(f"Golden test samples: {len(test_texts)}")

    # Ensure test labels are in training labels
    train_labels_set = set(train_intents)
    unknown_labels = set(test_intents) - train_labels_set
    if unknown_labels:
        print(f"WARNING: {len(unknown_labels)} test labels not in training: {unknown_labels}")

    # Train TF-IDF + Logistic Regression
    pipeline_lr = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words="english",
            min_df=2,
            max_df=0.9,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            random_state=RANDOM_SEED,
            class_weight="balanced",
            C=1.0,
        )),
    ])

    # Also try LinearSVC
    pipeline_svc = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words="english",
            min_df=2,
            max_df=0.9,
        )),
        ("clf", LinearSVC(
            random_state=RANDOM_SEED,
            class_weight="balanced",
            max_iter=2000,
        )),
    ])

    # Cross-val on training data to pick best
    print("Cross-validating LR...")
    lr_scores = cross_val_score(pipeline_lr, train_texts, train_intents,
                                cv=5, scoring="f1_macro")
    print(f"  LR CV macro-F1: {lr_scores.mean():.4f} ± {lr_scores.std():.4f}")

    print("Cross-validating SVC...")
    svc_scores = cross_val_score(pipeline_svc, train_texts, train_intents,
                                 cv=5, scoring="f1_macro")
    print(f"  SVC CV macro-F1: {svc_scores.mean():.4f} ± {svc_scores.std():.4f}")

    # Pick best
    if svc_scores.mean() > lr_scores.mean():
        best_pipeline = pipeline_svc
        best_name = "LinearSVC"
        best_cv = svc_scores.mean()
    else:
        best_pipeline = pipeline_lr
        best_name = "LogisticRegression"
        best_cv = lr_scores.mean()
    print(f"\nBest model: {best_name} (CV macro-F1: {best_cv:.4f})")

    # Train on full training data
    best_pipeline.fit(train_texts, train_intents)

    # Save model
    model_path = DATA_PROCESSED / "tfidf_classifier.pkl"
    joblib.dump(best_pipeline, model_path)
    print(f"Saved model: {model_path}")

    # Evaluate on golden set
    y_pred = best_pipeline.predict(test_texts)
    y_true = test_intents

    # Metrics
    accuracy = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    precision = precision_score(y_true, y_pred, average="macro", zero_division=0)
    recall_val = recall_score(y_true, y_pred, average="macro", zero_division=0)

    # Per-class report
    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)

    # Confusion matrix
    labels_sorted = sorted(set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels_sorted)

    results = {
        "model": best_name,
        "cv_macro_f1": round(best_cv, 4),
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "precision_macro": round(precision, 4),
        "recall_macro": round(recall_val, 4),
        "n_train": len(train_texts),
        "n_test": len(test_texts),
        "per_class": {
            k: {
                "precision": round(v["precision"], 4),
                "recall": round(v["recall"], 4),
                "f1": round(v["f1-score"], 4),
                "support": v["support"],
            }
            for k, v in report.items()
            if k not in ["accuracy", "macro avg", "weighted avg"]
        },
        "confusion_matrix": {
            "labels": labels_sorted,
            "matrix": cm.tolist(),
        },
    }

    # Plot confusion matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels_sorted, yticklabels=labels_sorted)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title(f"Confusion Matrix — {best_name}")
    plt.tight_layout()
    cm_path = FIGURES / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=150)
    plt.close()
    print(f"Saved confusion matrix: {cm_path}")

    return results


def main():
    ensure_dirs()
    results = train_and_evaluate()

    out = TABLES / "tfidf_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved: {out}")

    print(f"\n{'='*50}")
    print(f"TF-IDF BASELINE RESULTS ({results['model']})")
    print(f"{'='*50}")
    print(f"Accuracy:        {results['accuracy']:.1%}")
    print(f"Macro F1:        {results['macro_f1']:.4f}")
    print(f"Weighted F1:     {results['weighted_f1']:.4f}")
    print(f"Precision (macro): {results['precision_macro']:.4f}")
    print(f"Recall (macro):  {results['recall_macro']:.4f}")
    print(f"{'='*50}")
    print(f"\nPer-class F1:")
    for intent, metrics in results["per_class"].items():
        if "avg" not in intent:
            print(f"  {intent:<25} F1={metrics['f1']:.3f}  (n={metrics['support']})")


if __name__ == "__main__":
    main()
