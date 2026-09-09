"""
Phase 13: Comprehensive evaluation harness.

Single command to run all evaluations:
  python -m src.evaluate

Produces:
  reports/results.json
  reports/evaluation.md
  reports/tables/  (various)
  reports/figures/ (various)
  data/golden/human_review_template.csv
"""

import json
import sys
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, classification_report,
                             confusion_matrix)
from tqdm import tqdm
from src.config import (DATA_GOLDEN, DATA_PROCESSED, REPORTS, TABLES, FIGURES,
                        OPENAI_API_KEY, RANDOM_SEED, ensure_dirs)
from src.agent import SupportAgent
from src.judge_replies import judge_reply, save_judge_prompt
from src.human_judge_agreement import create_human_review_template, compute_agreement


def load_golden():
    path = DATA_GOLDEN / "golden_set.csv"
    if not path.exists():
        print("ERROR: Run create_golden_set first.")
        sys.exit(1)
    return pd.read_csv(path)


def evaluate_intent(y_true, y_pred) -> dict:
    """Compute intent classification metrics."""
    accuracy = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    precision = precision_score(y_true, y_pred, average="macro", zero_division=0)
    recall_val = recall_score(y_true, y_pred, average="macro", zero_division=0)

    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)

    labels = sorted(set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "precision_macro": round(precision, 4),
        "recall_macro": round(recall_val, 4),
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
        "confusion_matrix": {"labels": labels, "matrix": cm.tolist()},
    }


def evaluate_escalation(y_true, y_pred) -> dict:
    """Compute escalation metrics."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)

    precision_val = tp / max(tp + fp, 1)
    recall_val = tp / max(tp + fn, 1)
    f1 = 2 * precision_val * recall_val / max(precision_val + recall_val, 1e-9)
    false_auto_rate = fn / max(fn + tp, 1)
    false_escalation_rate = fp / max(fp + tn, 1)

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision_val, 4),
        "recall": round(recall_val, 4),
        "f1": round(f1, 4),
        "false_auto_rate": round(false_auto_rate, 4),
        "false_escalation_rate": round(false_escalation_rate, 4),
        "n_should_escalate": tp + fn,
        "n_total": tp + fp + fn + tn,
    }


def plot_confusion_matrix(cm_data, title, filename):
    """Plot and save confusion matrix."""
    labels = cm_data["labels"]
    matrix = np.array(cm_data["matrix"])

    plt.figure(figsize=(max(8, len(labels)), max(6, len(labels) * 0.8)))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels, yticklabels=labels)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(FIGURES / filename, dpi=150)
    plt.close()


def run_full_evaluation():
    """Run the complete evaluation pipeline."""
    ensure_dirs()
    save_judge_prompt()

    print("Loading golden set...")
    golden = load_golden()
    print(f"Golden set: {len(golden)} examples")

    # Initialize agent
    print("Initializing agent...")
    agent = SupportAgent()

    # Run agent on all golden examples
    print(f"\nRunning agent on {len(golden)} examples...")
    predictions = []
    judge_results = []
    errors = []

    for idx, row in tqdm(golden.iterrows(), total=len(golden), desc="Evaluating"):
        try:
            result = agent.handle(
                message=str(row["text"]),
                context=[str(row.get("context", ""))] if pd.notna(row.get("context")) else None,
            )

            pred = {
                "example_id": int(row.get("example_id", idx)),
                "message": str(row["text"])[:300],
                "true_intent": str(row["intent"]),
                "pred_intent": result["intent"]["name"],
                "intent_confidence": result["intent"]["confidence"],
                "true_escalate": bool(row.get("should_escalate", False)),
                "pred_escalate": result["escalation"]["decision"] == "ESCALATE",
                "escalation_reason": result["escalation"]["reason"],
                "reply": result["reply"],
                "reply_confidence": result.get("reply_confidence", 0),
                "n_retrieval": len(result["retrieval"]["results"]),
                "intent": result["intent"]["name"],
            }
            predictions.append(pred)

            # Judge the reply
            if OPENAI_API_KEY:
                scores = judge_reply(
                    customer_message=str(row["text"]),
                    generated_reply=result["reply"],
                    intent=result["intent"]["name"],
                    retrieval_evidence=result["retrieval"]["results"][:3],
                    _client=agent._get_client(),
                )
                judge_result = {**pred, **scores}
                judge_results.append(judge_result)

        except Exception as e:
            errors.append({"example_id": int(row.get("example_id", idx)),
                          "error": str(e)})
            print(f"  Error on example {idx}: {e}")

    print(f"\nProcessed: {len(predictions)}, Errors: {len(errors)}")

    # Compute intent metrics
    y_true_intent = [p["true_intent"] for p in predictions]
    y_pred_intent = [p["pred_intent"] for p in predictions]
    intent_metrics = evaluate_intent(y_true_intent, y_pred_intent)

    # Compute escalation metrics
    y_true_esc = [p["true_escalate"] for p in predictions]
    y_pred_esc = [p["pred_escalate"] for p in predictions]
    esc_metrics = evaluate_escalation(y_true_esc, y_pred_esc)

    # Reply quality metrics (from judge)
    reply_metrics = {}
    if judge_results:
        valid_judges = [j for j in judge_results if j.get("overall", -1) >= 0]
        if valid_judges:
            dims = ["groundedness", "correctness", "resolution_match",
                    "relevance", "tone", "completeness", "overall"]
            for dim in dims:
                vals = [j[dim] for j in valid_judges if j.get(dim, -1) >= 0]
                if vals:
                    reply_metrics[dim] = {
                        "mean": round(np.mean(vals), 3),
                        "median": round(float(np.median(vals)), 3),
                        "std": round(np.std(vals), 3),
                        "min": int(np.min(vals)),
                        "max": int(np.max(vals)),
                    }

            # Failure tag frequency
            all_tags = []
            for j in valid_judges:
                all_tags.extend(j.get("failure_tags", []))
            from collections import Counter
            tag_counts = Counter(all_tags)
            reply_metrics["failure_tags"] = dict(tag_counts.most_common(10))

    # Plot confusion matrix
    plot_confusion_matrix(intent_metrics["confusion_matrix"],
                         "AI Classifier — Confusion Matrix",
                         "ai_confusion_matrix.png")

    # Assemble results
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_evaluated": len(predictions),
        "n_errors": len(errors),
        "intent_metrics": intent_metrics,
        "escalation_metrics": esc_metrics,
        "reply_quality": reply_metrics,
        "judge_results": judge_results,
        "errors": errors[:10],
    }

    # Save results
    out_json = REPORTS / "results.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved: {out_json}")

    # Create human review template
    if judge_results:
        template_path = create_human_review_template(judge_results)
        print(f"Saved human review template: {template_path}")

    # Write evaluation markdown
    write_evaluation_md(results)

    # Print summary
    print(f"\n{'='*60}")
    print(f"EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"\nINTENT CLASSIFICATION:")
    print(f"  Accuracy:     {intent_metrics['accuracy']:.1%}")
    print(f"  Macro F1:     {intent_metrics['macro_f1']:.4f}")
    print(f"  Weighted F1:  {intent_metrics['weighted_f1']:.4f}")
    print(f"\nESCALATION:")
    print(f"  Precision:    {esc_metrics['precision']:.1%}")
    print(f"  Recall:       {esc_metrics['recall']:.1%}")
    print(f"  F1:           {esc_metrics['f1']:.4f}")
    print(f"  False-auto:   {esc_metrics['false_auto_rate']:.1%}")
    if reply_metrics and "overall" in reply_metrics:
        print(f"\nREPLY QUALITY (LLM Judge):")
        print(f"  Overall:      {reply_metrics['overall']['mean']:.1f}/12")
        for dim in ["groundedness", "correctness", "relevance", "tone"]:
            if dim in reply_metrics:
                print(f"  {dim:<14}: {reply_metrics[dim]['mean']:.2f}/2")
    print(f"{'='*60}")

    return results


def write_evaluation_md(results):
    """Write human-readable evaluation report."""
    im = results["intent_metrics"]
    em = results["escalation_metrics"]
    rq = results.get("reply_quality", {})

    lines = [
        "# Evaluation Results",
        "",
        f"**Evaluated**: {results['n_evaluated']} examples",
        f"**Errors**: {results['n_errors']}",
        f"**Timestamp**: {results['timestamp']}",
        "",
        "## Intent Classification",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | {im['accuracy']:.1%} |",
        f"| Macro F1 | {im['macro_f1']:.4f} |",
        f"| Weighted F1 | {im['weighted_f1']:.4f} |",
        f"| Precision (macro) | {im['precision_macro']:.4f} |",
        f"| Recall (macro) | {im['recall_macro']:.4f} |",
        "",
        "### Per-Class F1",
        "",
        "| Intent | F1 | Precision | Recall | Support |",
        "|--------|----|-----------|--------|---------|",
    ]
    for intent, metrics in sorted(im["per_class"].items()):
        if "avg" not in intent:
            lines.append(
                f"| {intent} | {metrics['f1']:.3f} | "
                f"{metrics['precision']:.3f} | {metrics['recall']:.3f} | "
                f"{metrics['support']} |"
            )

    lines += [
        "",
        "## Escalation",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Precision | {em['precision']:.1%} |",
        f"| Recall | {em['recall']:.1%} |",
        f"| F1 | {em['f1']:.4f} |",
        f"| False-auto rate | {em['false_auto_rate']:.1%} |",
        f"| False-escalation rate | {em['false_escalation_rate']:.1%} |",
        f"| Should escalate | {em['n_should_escalate']} |",
        f"| Total | {em['n_total']} |",
        "",
    ]

    if rq:
        lines += ["## Reply Quality (LLM Judge)", ""]
        if "overall" in rq:
            lines += [
                "| Dimension | Mean | Median | Std |",
                "|-----------|------|--------|-----|",
            ]
            for dim in ["groundedness", "correctness", "resolution_match",
                        "relevance", "tone", "completeness", "overall"]:
                if dim in rq:
                    d = rq[dim]
                    max_val = 12 if dim == "overall" else 2
                    lines.append(
                        f"| {dim} | {d['mean']:.2f}/{max_val} | "
                        f"{d['median']:.1f} | {d['std']:.2f} |"
                    )

        if "failure_tags" in rq:
            lines += ["", "### Failure Tags", ""]
            for tag, count in rq["failure_tags"].items():
                lines.append(f"- **{tag}**: {count}")

    lines.append("")

    out = REPORTS / "evaluation.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {out}")


def main():
    run_full_evaluation()


if __name__ == "__main__":
    main()
