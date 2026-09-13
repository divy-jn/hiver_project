"""
Phase 4 (execution order): Create golden evaluation set.

Stratified sampling across intents, lengths, tones, thread depths.
Labels are auto-assigned from clustering + heuristics, clearly marked for review.

Produces:
  data/golden/golden_set.csv
  data/golden/labeling_guidelines.md
"""

import json
import sys
import hashlib
import pandas as pd
import numpy as np
from collections import Counter
from src.config import (DATA_PROCESSED, DATA_GOLDEN, GOLDEN_SET_SIZE,
                        RANDOM_SEED, ensure_dirs)


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


def load_cluster_assignments():
    """Re-run clustering to get per-message cluster assignments."""
    from src.discover_intents import (load_threads as lt, extract_customer_messages,
                                      cluster_messages)
    threads = lt()
    messages = extract_customer_messages(threads)

    taxonomy = load_taxonomy()
    n_clusters = len(taxonomy)

    labels, _, _ = cluster_messages(messages, n_clusters)
    return messages, labels, taxonomy


def classify_tone(text: str) -> str:
    """Simple keyword-based tone classification."""
    text_lower = text.lower()
    angry_words = ["angry", "furious", "unacceptable", "worst", "terrible",
                   "disgusted", "hate", "ridiculous", "scam", "fraud", "!!"]
    frustrated_words = ["frustrated", "annoyed", "disappointed", "still waiting",
                        "again", "still no", "how long", "keep getting"]
    polite_words = ["please", "thank", "thanks", "appreciate", "kind",
                    "would you", "could you"]

    angry_count = sum(1 for w in angry_words if w in text_lower)
    frustrated_count = sum(1 for w in frustrated_words if w in text_lower)
    polite_count = sum(1 for w in polite_words if w in text_lower)

    if angry_count >= 2:
        return "angry"
    elif frustrated_count >= 2:
        return "frustrated"
    elif polite_count >= 2:
        return "polite"
    else:
        return "neutral"


def should_escalate_heuristic(text: str, thread_depth: int, is_resolved_heuristic: bool) -> tuple[bool, str]:
    """Heuristic escalation labeling for golden set."""
    text_lower = text.lower()

    # Security/account access
    security_words = ["hack", "unauthorized", "stolen", "breach", "security",
                      "locked out", "can't access", "compromised"]
    if any(w in text_lower for w in security_words):
        return True, "security_concern"

    # Legal/regulatory
    legal_words = ["lawyer", "legal", "sue", "attorney", "lawsuit", "ftc",
                   "consumer protection", "regulation"]
    if any(w in text_lower for w in legal_words):
        return True, "legal_concern"

    # Repeated/unresolved
    repeat_words = ["again", "still not resolved", "third time", "multiple times",
                    "keep telling", "already contacted", "been waiting"]
    if sum(1 for w in repeat_words if w in text_lower) >= 2:
        return True, "repeated_unresolved"

    # Very angry
    if classify_tone(text) == "angry":
        return True, "customer_very_angry"

    # Deep threads suggest complexity
    if thread_depth > 6:
        return True, "complex_issue"

    return False, ""


def stratified_sample(messages, labels, taxonomy, threads, target_size=200):
    """Create stratified sample covering all required dimensions."""
    rng = np.random.RandomState(RANDOM_SEED)

    # Map intent names
    intent_map = {t["cluster_id"]: t["intent_name"] for t in taxonomy}

    # Build enriched records
    thread_map = {t["thread_id"]: t for t in threads}
    records = []
    for msg, label in zip(messages, labels):
        thread = thread_map.get(msg["thread_id"], {})
        thread_msgs = thread.get("messages", [])
        thread_depth = len(thread_msgs)

        # Build context string (prior messages)
        context_parts = []
        for m in thread_msgs:
            if m["text"] == msg["text"]:
                break
            context_parts.append(f"[{m['author_type']}]: {m['text'][:100]}")
        context = " | ".join(context_parts[-3:])  # last 3 prior messages

        intent = intent_map.get(int(label), f"cluster_{label}")
        text = msg["text"]
        tone = classify_tone(text)
        escalate, esc_reason = should_escalate_heuristic(text, thread_depth, msg.get("is_resolved_heuristic", False))

        records.append({
            "text": text,
            "thread_id": msg["thread_id"],
            "intent": intent,
            "cluster_id": int(label),
            "tone": tone,
            "thread_depth": thread_depth,
            "text_length": len(text),
            "is_resolved_heuristic": msg.get("is_resolved_heuristic", False),
            "should_escalate": escalate,
            "escalation_reason": esc_reason,
            "context": context,
        })

    df = pd.DataFrame(records)

    # Stratified sampling strategy:
    # 1. Proportional by intent (minimum 5 per intent)
    # 2. Over-sample rare intents and edge cases
    # 3. Include angry/frustrated examples
    # 4. Include various text lengths
    # 5. Include escalation-worthy examples

    sampled_indices = set()

    # A) Minimum per intent
    min_per_intent = max(5, target_size // len(taxonomy) // 2)
    for intent_name in intent_map.values():
        intent_df = df[df["intent"] == intent_name]
        n = min(min_per_intent, len(intent_df))
        idx = intent_df.sample(n=n, random_state=RANDOM_SEED).index
        sampled_indices.update(idx)

    # B) Escalation examples (at least 20% of target)
    escalation_df = df[df["should_escalate"] == True]
    n_esc = min(len(escalation_df), max(target_size // 5, 30))
    remaining_esc = escalation_df[~escalation_df.index.isin(sampled_indices)]
    if len(remaining_esc) > 0:
        n_add = min(n_esc, len(remaining_esc))
        idx = remaining_esc.sample(n=n_add, random_state=RANDOM_SEED).index
        sampled_indices.update(idx)

    # C) Tone diversity
    for tone in ["angry", "frustrated", "polite"]:
        tone_df = df[(df["tone"] == tone) & (~df.index.isin(sampled_indices))]
        n = min(10, len(tone_df))
        if n > 0:
            idx = tone_df.sample(n=n, random_state=RANDOM_SEED).index
            sampled_indices.update(idx)

    # D) Length diversity (short, medium, long)
    for q_low, q_high in [(0, 0.1), (0.45, 0.55), (0.9, 1.0)]:
        low = df["text_length"].quantile(q_low)
        high = df["text_length"].quantile(q_high)
        len_df = df[(df["text_length"] >= low) & (df["text_length"] <= high)
                     & (~df.index.isin(sampled_indices))]
        n = min(10, len(len_df))
        if n > 0:
            idx = len_df.sample(n=n, random_state=RANDOM_SEED).index
            sampled_indices.update(idx)

    # E) Fill remaining with proportional sampling
    remaining_target = target_size - len(sampled_indices)
    if remaining_target > 0:
        remaining_df = df[~df.index.isin(sampled_indices)]
        if len(remaining_df) > 0:
            n = min(remaining_target, len(remaining_df))
            idx = remaining_df.sample(n=n, random_state=RANDOM_SEED).index
            sampled_indices.update(idx)

    # Trim if over target
    sampled_indices = list(sampled_indices)
    if len(sampled_indices) > target_size:
        rng.shuffle(sampled_indices)
        sampled_indices = sampled_indices[:target_size]

    golden_df = df.loc[sampled_indices].copy()
    golden_df = golden_df.reset_index(drop=True)
    golden_df.index.name = "example_id"

    return golden_df


def create_golden_csv(golden_df: pd.DataFrame):
    """Save golden set with required columns."""
    # Determine sampling group
    def sampling_group(row):
        if row["should_escalate"]:
            return "escalation"
        if row["tone"] in ["angry", "frustrated"]:
            return "negative_tone"
        if row["text_length"] < 50:
            return "short_message"
        if row["text_length"] > 200:
            return "long_message"
        return "standard"

    golden_df["sampling_group"] = golden_df.apply(sampling_group, axis=1)
    golden_df["example_id"] = range(len(golden_df))
    golden_df["label_status"] = "auto_labeled"  # Needs human review

    # Expected reply characteristics
    golden_df["expected_reply_characteristics"] = golden_df.apply(
        lambda r: "empathetic_and_solution" if r["tone"] in ["angry", "frustrated"]
        else "informational" if r["intent"].endswith("_request") or r["intent"].endswith("_info")
        else "helpful_and_professional",
        axis=1
    )

    cols = [
        "example_id", "text", "context", "intent", "should_escalate",
        "escalation_reason", "expected_reply_characteristics",
        "thread_id", "sampling_group", "tone", "text_length",
        "thread_depth", "is_resolved_heuristic", "label_status",
    ]
    # Only include columns that exist
    cols = [c for c in cols if c in golden_df.columns]

    out = DATA_GOLDEN / "golden_set.csv"
    golden_df[cols].to_csv(out, index=False, encoding="utf-8")
    return out


def create_labeling_guidelines(taxonomy):
    """Create labeling guidelines document."""
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
            "",
            "**Positive examples:**",
        ]
        for ex in intent.get("positive_examples", [])[:3]:
            lines.append(f"- {ex[:150]}")
        lines += [""]

    lines += [
        "## Escalation Criteria",
        "",
        "Mark `should_escalate = True` if ANY of the following apply:",
        "",
        "1. **Security concern**: Account compromise, unauthorized access, data breach",
        "2. **Legal/regulatory**: Mentions of lawyers, lawsuits, regulatory complaints",
        "3. **Repeated unresolved**: Customer indicates prior failed resolution attempts",
        "4. **Extreme anger**: Hostile, threatening, or deeply dissatisfied customer",
        "5. **Complex multi-issue**: Multiple intertwined problems requiring investigation",
        "6. **High-impact financial**: Large disputed amounts, billing errors",
        "7. **Safety concern**: Any threat or safety-related situation",
        "",
        "Mark `should_escalate = False` for routine inquiries, standard requests,",
        "and issues with clear resolution paths.",
        "",
        "## Ambiguous Cases",
        "",
        "- If a message could belong to 2 intents, choose the MORE SPECIFIC one",
        "- If genuinely ambiguous, label with the intent that would lead to the",
        "  most helpful response",
        "- When in doubt about escalation, prefer ESCALATE (conservative)",
        "",
        "## Labeling Process",
        "",
        "1. Read the customer message and any available context",
        "2. Assign an intent from the taxonomy",
        "3. Decide whether to escalate",
        "4. If escalating, provide a reason",
        "5. Mark `label_status` as `human_reviewed` when done",
        "",
        "## Quality Checks",
        "",
        "- Every example must have an intent label",
        "- Escalation reason is required when `should_escalate = True`",
        "- Re-read any example you're unsure about after labeling 20+ examples",
        "",
    ]

    out = DATA_GOLDEN / "labeling_guidelines.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def validate_golden_set(path):
    """Validate the golden set meets requirements."""
    df = pd.read_csv(path)
    issues = []

    # Size check
    if len(df) < 150:
        issues.append(f"Too few examples: {len(df)} (need 150-250)")
    if len(df) > 250:
        issues.append(f"Too many examples: {len(df)} (need 150-250)")

    # Required fields
    for col in ["example_id", "text", "intent", "should_escalate"]:
        if col not in df.columns:
            issues.append(f"Missing required column: {col}")
        elif df[col].isna().any():
            n_missing = df[col].isna().sum()
            issues.append(f"Missing values in {col}: {n_missing}")

    # Duplicate messages
    n_dup = df["text"].duplicated().sum()
    if n_dup > 0:
        issues.append(f"Duplicate messages: {n_dup}")

    # Class distribution
    if "intent" in df.columns:
        dist = df["intent"].value_counts()
        print("\nIntent distribution:")
        for intent, count in dist.items():
            print(f"  {intent}: {count} ({count/len(df):.1%})")

    if "should_escalate" in df.columns:
        esc_rate = df["should_escalate"].mean()
        print(f"\nEscalation rate: {esc_rate:.1%}")

    if "label_status" in df.columns:
        auto = (df["label_status"] == "auto_labeled").sum()
        human = (df["label_status"] == "human_reviewed").sum()
        print(f"\nLabel Status:")
        print(f"  auto_labeled: {auto}")
        print(f"  human_reviewed: {human}")

    # Golden thread overlap
    training_path = DATA_PROCESSED / "training_set.csv"
    if training_path.exists():
        train_df = pd.read_csv(training_path)
        train_threads = set(train_df["thread_id"].dropna().astype(str))
        golden_threads = set(df["thread_id"].dropna().astype(str))
        leak = train_threads.intersection(golden_threads)
        print(f"\nLeakage Check:")
        print(f"  Overlap with training set: {len(leak)} threads")

    if issues:
        print("\nValidation ISSUES:")
        for issue in issues:
            print(f"  ⚠ {issue}")
    else:
        print("\n✓ Golden set validation passed")

    return issues


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing golden set")
    parser.add_argument("--validate", action="store_true", help="Only validate existing golden set")
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
        print(f"File exists: {csv_path}")
        print("Use --force to overwrite. Skipping golden set creation to protect human reviews.")
        return

    print("Loading data...")
    threads = load_threads()
    taxonomy = load_taxonomy()

    print("Computing cluster assignments...")
    messages, labels, _ = load_cluster_assignments()

    print(f"Stratified sampling {GOLDEN_SET_SIZE} examples...")
    golden_df = stratified_sample(messages, labels, taxonomy, threads, GOLDEN_SET_SIZE)

    print(f"Created golden set with {len(golden_df)} examples")
    csv_path = create_golden_csv(golden_df)
    print(f"Saved: {csv_path}")

    guidelines_path = create_labeling_guidelines(taxonomy)
    print(f"Saved: {guidelines_path}")

    print("\nValidating...")
    validate_golden_set(csv_path)


if __name__ == "__main__":
    main()
