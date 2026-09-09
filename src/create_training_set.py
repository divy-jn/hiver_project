"""
Phase 6: Create training set for baseline models.

Assigns weak/heuristic labels (via clustering) to non-golden threads.
Strictly excludes any threads present in the golden set to prevent data leakage.

Produces:
  data/processed/training_set.csv
"""

import json
import sys
import pandas as pd
from pathlib import Path
from src.config import DATA_PROCESSED, DATA_GOLDEN, ensure_dirs


def load_golden_thread_ids() -> set:
    """Load the set of thread IDs that are in the golden evaluation set."""
    golden_path = DATA_GOLDEN / "golden_set.csv"
    if not golden_path.exists():
        print("ERROR: Run create_golden_set first.")
        sys.exit(1)
    
    df = pd.read_csv(golden_path)
    # Ensure they are strings for robust comparison
    return set(df["thread_id"].dropna().astype(str))


def load_taxonomy() -> list[dict]:
    path = DATA_PROCESSED / "intent_taxonomy.json"
    if not path.exists():
        print("ERROR: Run discover_intents first.")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ensure_dirs()
    print("Loading golden set thread IDs for exclusion...")
    golden_ids = load_golden_thread_ids()
    print(f"Loaded {len(golden_ids)} golden threads to exclude.")

    print("Loading taxonomy...")
    taxonomy = load_taxonomy()
    n_clusters = len(taxonomy)
    intent_map = {t["cluster_id"]: t["intent_name"] for t in taxonomy}

    print("Loading all threads and extracting messages...")
    from src.discover_intents import load_threads, extract_customer_messages, cluster_messages
    threads = load_threads()
    messages = extract_customer_messages(threads)
    
    print(f"Total customer messages: {len(messages)}")

    print(f"Clustering to assign weak labels...")
    labels, _, _ = cluster_messages(messages, n_clusters)

    records = []
    excluded_count = 0

    for msg, label in zip(messages, labels):
        thread_id_str = str(msg["thread_id"])
        
        # EXPLICIT LEAKAGE PREVENTION
        if thread_id_str in golden_ids:
            excluded_count += 1
            continue
            
        intent_name = intent_map.get(int(label), f"cluster_{label}")
        records.append({
            "thread_id": msg["thread_id"],
            "text": msg["text"],
            "intent": intent_name,
            "label_status": "weak_training_label"
        })

    print(f"Excluded {excluded_count} messages that belong to golden threads.")
    
    df = pd.DataFrame(records)
    out_path = DATA_PROCESSED / "training_set.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Saved {len(df)} training examples to {out_path}")


if __name__ == "__main__":
    main()
