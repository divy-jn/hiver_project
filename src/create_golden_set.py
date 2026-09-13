"""
Phase 4 (execution order): Create golden evaluation set.

Stratified sampling across intents, metadata, thread depth, and resolution status.
Labels are auto-assigned from heuristics, clearly marked for review.

Produces:
  data/golden/golden_set.csv
  data/golden/labeling_guidelines.md
"""

import json
import sys
import pandas as pd
import numpy as np
from collections import defaultdict
from src.config import (DATA_PROCESSED, DATA_GOLDEN, GOLDEN_SET_SIZE,
                        RANDOM_SEED, ensure_dirs)
from src.discover_intents import categorize_message, extract_metadata


def load_threads():
    path = DATA_PROCESSED / "threads.jsonl"
    if not path.exists():
        print("ERROR: Run build_threads first.")
        sys.exit(1)
    threads = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            threads.append(json.loads(line))
    return threads


def load_taxonomy():
    path = DATA_PROCESSED / "intent_taxonomy.json"
    if not path.exists():
        print("ERROR: Run discover_intents first.")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_candidate_records(threads):
    """Process all threads and extract the first customer message with rich metadata."""
    records = []
    for t in threads:
        customer_msg = None
        for msg in t["messages"]:
            if msg["author_type"] == "customer":
                customer_msg = msg
                break
        
        if not customer_msg:
            continue
            
        text = customer_msg["text"]
        intent = categorize_message(text)
        meta = extract_metadata(text)
        
        thread_msgs = t["messages"]
        thread_depth = len(thread_msgs)
        
        # Context
        context_parts = []
        for m in thread_msgs:
            if m["text"] == text:
                break
            context_parts.append(f"[{m['author_type']}]: {m['text'][:100]}")
        context = " | ".join(context_parts[-3:])
        
        res_heuristic = t.get("resolution_heuristic", {})
        
        records.append({
            "text": text,
            "thread_id": t["thread_id"],
            "intent": intent,
            "thread_depth": thread_depth,
            "text_length": len(text),
            "is_resolved_heuristic": res_heuristic.get("is_resolved_heuristic", False),
            "historical_precedent_quality": res_heuristic.get("historical_precedent_quality", "none"),
            "should_escalate_auto": meta["high_frustration_angry"] or meta["repeated_unresolved_issue"] or meta["security_account_sensitive"],
            "escalation_reason_auto": "angry/frustrated" if meta["high_frustration_angry"] else ("security" if meta["security_account_sensitive"] else ("repeated" if meta["repeated_unresolved_issue"] else "")),
            "high_frustration_angry": meta["high_frustration_angry"],
            "requires_private_dm": meta["requires_private_dm_handling"],
            "context": context,
        })
    return pd.DataFrame(records)


def stratified_sample(df, target_size=200):
    """Stratified sampling across required dimensions."""
    rng = np.random.RandomState(RANDOM_SEED)
    sampled_indices = set()
    
    def add_samples(subset_df, n):
        remaining = subset_df[~subset_df.index.isin(sampled_indices)]
        if len(remaining) > 0:
            idx = remaining.sample(n=min(n, len(remaining)), random_state=RANDOM_SEED).index
            sampled_indices.update(idx)

    # 1. All 8 intents (minimum 10 per intent = ~80)
    for intent in df["intent"].unique():
        add_samples(df[df["intent"] == intent], max(10, target_size // 15))
        
    # 2. Message length (short < 50, long > 250)
    add_samples(df[df["text_length"] < 50], 10)
    add_samples(df[df["text_length"] > 250], 10)
    
    # 3. Thread depth (deep > 5)
    add_samples(df[df["thread_depth"] > 5], 15)
    
    # 4. High-frustration cases
    add_samples(df[df["high_frustration_angry"] == True], 15)
    
    # 5. Private-DM/escalation cases
    add_samples(df[df["requires_private_dm"] == True], 10)
    
    # 6. Actionable vs non-actionable historical precedent
    add_samples(df[df["historical_precedent_quality"] == "actionable"], 15)
    add_samples(df[df["historical_precedent_quality"] == "low_quality"], 15)
    
    # Fill remaining to hit target
    remaining_target = target_size - len(sampled_indices)
    if remaining_target > 0:
        add_samples(df, remaining_target)
        
    # Trim if over target
    sampled_list = list(sampled_indices)
    if len(sampled_list) > target_size:
        rng.shuffle(sampled_list)
        sampled_list = sampled_list[:target_size]
        
    golden_df = df.loc[sampled_list].copy()
    golden_df = golden_df.reset_index(drop=True)
    
    return golden_df


def create_golden_csv(golden_df: pd.DataFrame):
    # Required columns
    golden_df["example_id"] = [f"gold_{i:04d}" for i in range(len(golden_df))]
    golden_df["label_status"] = "auto_labeled"
    golden_df["human_editable_intent"] = golden_df["intent"]
    golden_df["human_editable_escalation"] = golden_df["should_escalate_auto"]
    golden_df["escalation_reason"] = golden_df["escalation_reason_auto"]
    
    cols = [
        "example_id",
        "thread_id",
        "text",
        "context",
        "label_status",
        "human_editable_intent",
        "human_editable_escalation",
        "escalation_reason",
        "intent",  # auto intent
        "should_escalate_auto",
        "text_length",
        "thread_depth",
        "historical_precedent_quality",
    ]
    
    out = DATA_GOLDEN / "golden_set.csv"
    golden_df[cols].to_csv(out, index=False, encoding="utf-8")
    return out


def create_labeling_guidelines(taxonomy):
    lines = [
        "# Golden Set Labeling Guidelines",
        "",
        "## Purpose",
        "These guidelines help human reviewers validate and correct the auto-generated labels",
        "in the golden evaluation set.",
        "",
        "## Intent Labels",
        "",
        "Each message should be assigned exactly ONE intent from the taxonomy below.",
        "",
    ]

    for intent in taxonomy:
        lines += [
            f"### {intent['intent_name']}",
            f"**Definition**: {intent['definition']}",
            f"**Inclusion**: {intent['inclusion_criteria']}",
            f"**Exclusion**: {intent['exclusion_criteria']}",
            "",
            "**Positive examples:**",
        ]
        for ex in intent.get("positive_examples", [])[:3]:
            lines.append(f"- {ex[:150]}...")
        lines += [""]

    lines += [
        "## Escalation Criteria",
        "",
        "Mark `human_editable_escalation = True` if ANY of the following apply:",
        "",
        "1. **Security concern**: Account compromise, unauthorized access, data breach",
        "2. **Legal/regulatory**: Mentions of lawyers, lawsuits, regulatory complaints",
        "3. **Repeated unresolved**: Customer indicates prior failed resolution attempts",
        "4. **Extreme anger**: Hostile, threatening, or deeply dissatisfied customer",
        "5. **Complex multi-issue**: Multiple intertwined problems requiring investigation",
        "6. **High-impact financial**: Large disputed amounts, billing errors",
        "7. **Safety concern**: Any threat or safety-related situation",
        "",
        "Mark `human_editable_escalation = False` for routine inquiries, standard requests,",
        "and issues with clear resolution paths.",
        "",
        "## Labeling Process",
        "",
        "1. Read the `text` and `context`.",
        "2. Review `human_editable_intent` (initially auto-filled). Correct it if needed.",
        "3. Review `human_editable_escalation` (initially auto-filled). Correct it if needed.",
        "4. If escalating, provide an `escalation_reason`.",
        "5. Change `label_status` to `human_reviewed` when done.",
    ]

    out = DATA_GOLDEN / "labeling_guidelines.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def validate_golden_set(path):
    df = pd.read_csv(path)
    issues = []

    if len(df) < 150 or len(df) > 250:
        issues.append(f"Size issue: {len(df)} rows (expected 150-250)")

    req_cols = ["example_id", "text", "human_editable_intent", "human_editable_escalation", "label_status"]
    for col in req_cols:
        if col not in df.columns:
            issues.append(f"Missing column: {col}")

    if df["example_id"].duplicated().any():
        issues.append("Duplicate example_ids found.")

    if df["text"].duplicated().any():
        n_dup = df["text"].duplicated().sum()
        issues.append(f"Duplicate messages found: {n_dup}")

    taxonomy = load_taxonomy()
    valid_intents = set([t["intent_name"] for t in taxonomy])
    invalid_intents = set(df["human_editable_intent"].dropna().unique()) - valid_intents
    if invalid_intents:
        issues.append(f"Invalid intent values found: {invalid_intents}")

    print("\n--- Validation Report ---")
    
    print("\nLabel Status Distribution:")
    for status, count in df["label_status"].value_counts().items():
        print(f"  {status}: {count}")
        
    print("\nIntent Distribution:")
    for intent, count in df["human_editable_intent"].value_counts().items():
        print(f"  {intent}: {count} ({count/len(df):.1%})")

    # Leakage checks
    train_path = DATA_PROCESSED / "training_set.csv"
    retrieval_path = DATA_PROCESSED / "retrieval_index.pkl"
    
    golden_threads = set(df["thread_id"].astype(str))
    
    if train_path.exists():
        train_df = pd.read_csv(train_path)
        train_threads = set(train_df["thread_id"].dropna().astype(str))
        leak = train_threads.intersection(golden_threads)
        print(f"\nTraining Set Leakage: {len(leak)} threads overlapped.")
        if len(leak) > 0:
            issues.append("Leakage detected in training set!")

    if retrieval_path.exists():
        import pickle
        with open(retrieval_path, "rb") as f:
            records = pickle.load(f)
        ret_threads = set(str(r["thread_id"]) for r in records)
        leak = ret_threads.intersection(golden_threads)
        print(f"\nRetrieval Corpus Leakage: {len(leak)} threads overlapped.")
        if len(leak) > 0:
            issues.append("Leakage detected in retrieval corpus!")

    if issues:
        print("\nISSUES FOUND:")
        for iss in issues:
            print(f"  - {iss}")
        sys.exit(1)
    else:
        print("\nValidation PASSED: No issues.")

    return df


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    csv_path = DATA_GOLDEN / "golden_set.csv"

    if args.validate:
        if not csv_path.exists():
            print("ERROR: Golden set does not exist to validate.")
            sys.exit(1)
        validate_golden_set(csv_path)
        return

    if csv_path.exists() and not args.force:
        print(f"File exists: {csv_path}. Use --force to overwrite.")
        return

    print("Loading data...")
    threads = load_threads()
    taxonomy = load_taxonomy()

    print("Preparing candidate records...")
    df = prepare_candidate_records(threads)

    print(f"Stratified sampling {GOLDEN_SET_SIZE} examples...")
    golden_df = stratified_sample(df, GOLDEN_SET_SIZE)

    csv_path = create_golden_csv(golden_df)
    print(f"Saved: {csv_path}")

    guidelines_path = create_labeling_guidelines(taxonomy)
    print(f"Saved: {guidelines_path}")

    print("\nValidating Golden Set...")
    validate_golden_set(csv_path)


if __name__ == "__main__":
    main()
