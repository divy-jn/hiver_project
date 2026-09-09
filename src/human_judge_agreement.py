"""
Phase 15: Human-judge agreement analysis.

Creates template for human review, computes agreement metrics
when human labels are provided.

Produces:
  data/golden/human_review_template.csv
  reports/tables/judge_agreement.json  (when human labels exist)
"""

import json
import sys
import numpy as np
import pandas as pd
from scipy import stats
from src.config import DATA_GOLDEN, TABLES, REPORTS, ensure_dirs


DIMENSIONS = [
    "groundedness", "correctness", "resolution_match",
    "relevance", "tone", "completeness", "overall",
]


def create_human_review_template(judge_results: list[dict], n_sample: int = 40):
    """
    Create a CSV template for human review of LLM judge scores.

    Args:
        judge_results: list of dicts with example_id, message, reply, and judge scores
        n_sample: number of examples to include (target 30-50)
    """
    if len(judge_results) < n_sample:
        n_sample = len(judge_results)

    # Stratified sample: mix of high/low judge scores
    rng = np.random.RandomState(42)
    indices = list(range(len(judge_results)))

    # Sort by overall score, pick from different quartiles
    sorted_idx = sorted(indices, key=lambda i: judge_results[i].get("overall", 0))
    quartile_size = len(sorted_idx) // 4
    sampled = []
    for q in range(4):
        start = q * quartile_size
        end = start + quartile_size if q < 3 else len(sorted_idx)
        q_indices = sorted_idx[start:end]
        n_from_q = n_sample // 4
        if q == 3:
            n_from_q = n_sample - len(sampled)
        chosen = rng.choice(q_indices, size=min(n_from_q, len(q_indices)), replace=False)
        sampled.extend(chosen)

    rows = []
    for idx in sampled[:n_sample]:
        r = judge_results[idx]
        row = {
            "example_id": r.get("example_id", idx),
            "customer_message": r.get("message", "")[:300],
            "generated_reply": r.get("reply", "")[:500],
            "intent": r.get("intent", ""),
            # LLM judge scores (for reference, can be hidden)
            "llm_groundedness": r.get("groundedness", -1),
            "llm_correctness": r.get("correctness", -1),
            "llm_resolution_match": r.get("resolution_match", -1),
            "llm_relevance": r.get("relevance", -1),
            "llm_tone": r.get("tone", -1),
            "llm_completeness": r.get("completeness", -1),
            "llm_overall": r.get("overall", -1),
            # Human scores (TO BE FILLED)
            "human_groundedness": "",
            "human_correctness": "",
            "human_resolution_match": "",
            "human_relevance": "",
            "human_tone": "",
            "human_completeness": "",
            "human_overall": "",
            "human_notes": "",
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    out = DATA_GOLDEN / "human_review_template.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    return out


def compute_agreement(human_review_path=None):
    """
    Compute agreement between human and LLM judge.

    Returns metrics dict or None if human labels not yet provided.
    """
    path = human_review_path or DATA_GOLDEN / "human_review_template.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)

    # Check if human labels are filled
    human_cols = [f"human_{d}" for d in DIMENSIONS]
    filled = df[human_cols].notna().all(axis=1) & (df[human_cols] != "").all(axis=1)
    n_filled = filled.sum()

    if n_filled < 10:
        return {
            "status": "pending",
            "message": f"Only {n_filled} of {len(df)} examples have human labels. "
                       f"Need at least 10 for meaningful agreement analysis.",
            "n_filled": int(n_filled),
            "n_total": len(df),
        }

    # Filter to filled rows
    df_filled = df[filled].copy()
    for col in human_cols:
        df_filled[col] = pd.to_numeric(df_filled[col], errors="coerce")

    results = {"status": "computed", "n_examples": int(n_filled)}
    dimension_results = {}

    for dim in DIMENSIONS:
        human_col = f"human_{dim}"
        llm_col = f"llm_{dim}"

        if human_col not in df_filled.columns or llm_col not in df_filled.columns:
            continue

        human_scores = df_filled[human_col].dropna().values
        llm_scores = df_filled[llm_col].dropna().values

        if len(human_scores) == 0 or len(llm_scores) == 0:
            continue

        n = min(len(human_scores), len(llm_scores))
        human_scores = human_scores[:n]
        llm_scores = llm_scores[:n]

        # Exact agreement
        exact = np.mean(human_scores == llm_scores)

        # Adjacent agreement (within ±1)
        adjacent = np.mean(np.abs(human_scores - llm_scores) <= 1)

        # Correlation
        if np.std(human_scores) > 0 and np.std(llm_scores) > 0:
            corr, p_value = stats.pearsonr(human_scores, llm_scores)
        else:
            corr, p_value = 0.0, 1.0

        # Mean absolute error
        mae = np.mean(np.abs(human_scores - llm_scores))

        # Major disagreements (differ by 2)
        major_disagree = np.sum(np.abs(human_scores - llm_scores) >= 2)

        dimension_results[dim] = {
            "exact_agreement": round(float(exact), 4),
            "adjacent_agreement": round(float(adjacent), 4),
            "correlation": round(float(corr), 4),
            "correlation_p_value": round(float(p_value), 4),
            "mean_absolute_error": round(float(mae), 4),
            "major_disagreements": int(major_disagree),
            "n_examples": int(n),
        }

    results["dimensions"] = dimension_results

    # Overall summary
    if "overall" in dimension_results:
        overall = dimension_results["overall"]
        results["summary"] = {
            "overall_exact_agreement": overall["exact_agreement"],
            "overall_adjacent_agreement": overall["adjacent_agreement"],
            "overall_correlation": overall["correlation"],
            "judge_reliability": (
                "high" if overall["adjacent_agreement"] > 0.8
                else "moderate" if overall["adjacent_agreement"] > 0.6
                else "low"
            ),
        }

    return results


def main():
    ensure_dirs()

    # Check if judge results exist
    results_path = REPORTS / "results.json"
    if results_path.exists():
        all_results = json.loads(results_path.read_text(encoding="utf-8"))
        judge_results = all_results.get("judge_results", [])
        if judge_results:
            template_path = create_human_review_template(judge_results)
            print(f"Created human review template: {template_path}")
            print(f"Contains {len(judge_results)} examples for review")
    else:
        print("No evaluation results found. Run evaluate.py first.")

    # Try to compute agreement
    agreement = compute_agreement()
    if agreement:
        out = TABLES / "judge_agreement.json"
        out.write_text(json.dumps(agreement, indent=2), encoding="utf-8")
        print(f"\nSaved agreement results: {out}")

        if agreement["status"] == "pending":
            print(f"\n⚠ {agreement['message']}")
        else:
            print(f"\nAgreement computed on {agreement['n_examples']} examples")
            if "summary" in agreement:
                s = agreement["summary"]
                print(f"  Overall exact agreement: {s['overall_exact_agreement']:.1%}")
                print(f"  Overall adjacent agreement: {s['overall_adjacent_agreement']:.1%}")
                print(f"  Overall correlation: {s['overall_correlation']:.3f}")
                print(f"  Judge reliability: {s['judge_reliability']}")
    else:
        print("\nHuman review template not yet created. Run evaluation first.")


if __name__ == "__main__":
    main()
