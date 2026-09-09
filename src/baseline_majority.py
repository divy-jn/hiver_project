"""
Phase 6: Trivial baseline — majority class for intent, always-auto for escalation.

Produces:
  reports/tables/baseline_majority.json
"""

import json
import sys
import pandas as pd
import numpy as np
from collections import Counter
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, classification_report)
from src.config import DATA_GOLDEN, DATA_PROCESSED, TABLES, ensure_dirs


def load_golden():
    path = DATA_GOLDEN / "golden_set.csv"
    if not path.exists():
        print("ERROR: Run create_golden_set first.")
        sys.exit(1)
    return pd.read_csv(path)


def load_threads_for_training():
    """Load threads to determine majority class from training data (NOT golden set)."""
    from src.discover_intents import load_threads, extract_customer_messages, cluster_messages
    from src.config import RANDOM_SEED

    taxonomy_path = DATA_PROCESSED / "intent_taxonomy.json"
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    intent_map = {t["cluster_id"]: t["intent_name"] for t in taxonomy}

    threads = load_threads()
    messages = extract_customer_messages(threads)
    n_clusters = len(taxonomy)
    labels, _, _ = cluster_messages(messages, n_clusters)

    # Get intent distribution from full training data
    intent_counts = Counter()
    for label in labels:
        intent_name = intent_map.get(int(label), f"cluster_{label}")
        intent_counts[intent_name] += 1

    return intent_counts


def evaluate_majority_baseline():
    """Evaluate majority-class baseline on golden set."""
    golden = load_golden()
    intent_counts = load_threads_for_training()

    # Majority class
    majority_intent = intent_counts.most_common(1)[0][0]
    print(f"Majority intent: {majority_intent} ({intent_counts[majority_intent]} examples in training)")

    # Intent predictions: always predict majority class
    y_true = golden["intent"].tolist()
    y_pred = [majority_intent] * len(y_true)

    # Intent metrics
    intent_accuracy = accuracy_score(y_true, y_pred)
    intent_macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    intent_weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    # Escalation: always auto-handle
    # This is the more meaningful trivial baseline because it reveals false-auto rate
    y_esc_true = golden["should_escalate"].astype(bool).tolist()
    y_esc_pred = [False] * len(y_esc_true)  # always auto

    esc_tp = sum(1 for t, p in zip(y_esc_true, y_esc_pred) if t and p)
    esc_fp = sum(1 for t, p in zip(y_esc_true, y_esc_pred) if not t and p)
    esc_fn = sum(1 for t, p in zip(y_esc_true, y_esc_pred) if t and not p)
    esc_tn = sum(1 for t, p in zip(y_esc_true, y_esc_pred) if not t and not p)

    false_auto_rate = esc_fn / max(esc_fn + esc_tp, 1)  # missed escalations

    results = {
        "baseline_type": "majority_class",
        "intent": {
            "majority_class": majority_intent,
            "accuracy": round(intent_accuracy, 4),
            "macro_f1": round(intent_macro_f1, 4),
            "weighted_f1": round(intent_weighted_f1, 4),
            "n_golden": len(y_true),
        },
        "escalation": {
            "strategy": "always_auto_handle",
            "reason": "Reveals false-auto rate — how many escalation-worthy cases are missed",
            "true_positives": esc_tp,
            "false_positives": esc_fp,
            "false_negatives": esc_fn,
            "true_negatives": esc_tn,
            "false_auto_rate": round(false_auto_rate, 4),
            "n_should_escalate": sum(y_esc_true),
            "n_total": len(y_esc_true),
        },
    }

    return results


def main():
    ensure_dirs()
    print("Evaluating majority-class baseline...")
    results = evaluate_majority_baseline()

    out = TABLES / "baseline_majority.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved: {out}")

    print(f"\n{'='*50}")
    print(f"MAJORITY BASELINE RESULTS")
    print(f"{'='*50}")
    print(f"Intent accuracy:  {results['intent']['accuracy']:.1%}")
    print(f"Intent macro F1:  {results['intent']['macro_f1']:.4f}")
    print(f"Intent weighted F1: {results['intent']['weighted_f1']:.4f}")
    print(f"Majority class:   {results['intent']['majority_class']}")
    print(f"")
    print(f"Escalation: always auto-handle")
    print(f"  False-auto rate: {results['escalation']['false_auto_rate']:.1%}")
    print(f"  Missed escalations: {results['escalation']['false_negatives']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
