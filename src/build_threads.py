"""
Phase 3: Thread reconstruction.

Builds conversation threads from reply relationships.

Produces:
  data/processed/threads.jsonl
"""

import json
import sys
from collections import defaultdict
import pandas as pd
from src.config import RAW_CSV, DATA_PROCESSED, ensure_dirs
from src.profile_dataset import load_raw


def load_selected_brand() -> str:
    """Load the selected brand identifier."""
    path = DATA_PROCESSED / "selected_brand.json"
    if not path.exists():
        print("ERROR: Run select_brand first.")
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["brand"]


def build_threads(df: pd.DataFrame, brand_id: str) -> list[dict]:
    """
    Build conversation threads for a given brand.

    Strategy:
    1. Find all brand responses (tweets by brand_id with in_response_to set)
    2. For each brand response, trace backward to find the customer's original message
    3. Also trace forward to find follow-ups
    4. Group into threads by following reply chains
    """
    # Index tweets by ID for fast lookup
    tweet_map = {}
    for _, row in df.iterrows():
        tid = str(row["tweet_id"]) if pd.notna(row["tweet_id"]) else None
        if tid:
            tweet_map[tid] = {
                "tweet_id": tid,
                "author_id": str(row["author_id"]) if pd.notna(row["author_id"]) else "",
                "text": str(row["text"]) if pd.notna(row["text"]) else "",
                "created_at": str(row["created_at"]) if pd.notna(row.get("created_at")) else "",
                "in_response_to": str(row["in_response_to_tweet_id"]) if pd.notna(row["in_response_to_tweet_id"]) else None,
            }

    # Build reply chains: child -> parent
    children = defaultdict(list)
    for tid, tweet in tweet_map.items():
        parent = tweet["in_response_to"]
        if parent:
            children[parent].append(tid)

    # Find thread roots: tweets that start a conversation with the brand
    # A root is a tweet replied to by the brand, which itself has no parent in dataset
    brand_responses = {tid: t for tid, t in tweet_map.items()
                       if t["author_id"] == brand_id and t["in_response_to"]}

    # Trace each brand response to find conversation roots
    visited_roots = set()
    threads = []

    def trace_root(tid):
        """Trace upward to find the root of a thread."""
        seen = set()
        current = tid
        while current in tweet_map and current not in seen:
            seen.add(current)
            parent = tweet_map[current]["in_response_to"]
            if parent and parent in tweet_map:
                current = parent
            else:
                break
        return current

    def collect_thread(root_id, max_depth=20):
        """Collect all messages in a thread starting from root, BFS."""
        messages = []
        queue = [root_id]
        seen = set()
        depth = 0

        while queue and depth < max_depth:
            next_queue = []
            for tid in queue:
                if tid in seen or tid not in tweet_map:
                    continue
                seen.add(tid)
                tweet = tweet_map[tid]
                author_type = "brand" if tweet["author_id"] == brand_id else "customer"
                messages.append({
                    "tweet_id": tid,
                    "author_type": author_type,
                    "author_id": tweet["author_id"],
                    "text": tweet["text"],
                    "timestamp": tweet["created_at"],
                    "in_response_to": tweet["in_response_to"],
                })
                # Add children
                for child_id in children.get(tid, []):
                    if child_id not in seen:
                        next_queue.append(child_id)
            queue = next_queue
            depth += 1

        return messages

    # Build threads
    for resp_id, resp in brand_responses.items():
        root_id = trace_root(resp_id)
        if root_id in visited_roots:
            continue
        visited_roots.add(root_id)

        messages = collect_thread(root_id)
        if len(messages) < 2:
            continue

        # Sort by timestamp if available, else by reply chain
        # Try timestamp sort first
        def sort_key(m):
            return m.get("timestamp", "") or ""
        messages.sort(key=sort_key)

        # Determine resolution
        has_brand = any(m["author_type"] == "brand" for m in messages)
        has_customer = any(m["author_type"] == "customer" for m in messages)

        if not (has_brand and has_customer):
            continue

        last_msg = messages[-1]
        # Resolution heuristic: brand has last word, or second-to-last
        resolved = last_msg["author_type"] == "brand"
        if not resolved and len(messages) >= 2:
            resolved = messages[-2]["author_type"] == "brand"

        resolution_text = ""
        if resolved:
            # Find last brand message
            for m in reversed(messages):
                if m["author_type"] == "brand":
                    resolution_text = m["text"]
                    break

        thread = {
            "thread_id": root_id,
            "brand_id": brand_id,
            "n_messages": len(messages),
            "messages": [
                {
                    "author_type": m["author_type"],
                    "text": m["text"],
                    "timestamp": m["timestamp"],
                }
                for m in messages
            ],
            "resolution": {
                "resolved": resolved,
                "response_text": resolution_text if resolved else "",
                "resolution_type": "brand_final" if resolved else "unresolved",
            },
        }
        threads.append(thread)

    return threads


def main():
    ensure_dirs()
    print("Loading dataset...")
    df = load_raw()
    brand_id = load_selected_brand()
    print(f"Building threads for brand: {brand_id}")

    # Filter to relevant tweets (brand + their conversation partners)
    brand_tweets = df[df["author_id"] == brand_id]
    brand_tweet_ids = set(brand_tweets["tweet_id"])
    brand_reply_targets = set(brand_tweets["in_response_to_tweet_id"].dropna())

    # Get all tweets in conversations with this brand
    relevant_ids = brand_tweet_ids | brand_reply_targets
    # Also get replies to brand tweets
    replies_to_brand = df[df["in_response_to_tweet_id"].isin(brand_tweet_ids)]
    relevant_ids |= set(replies_to_brand["tweet_id"])
    # Get the tweets that brand replied to
    customer_tweets = df[df["tweet_id"].isin(brand_reply_targets)]
    relevant_ids |= set(customer_tweets["tweet_id"])

    relevant_df = df[df["tweet_id"].isin(relevant_ids)].copy()
    print(f"Filtered to {len(relevant_df):,} relevant tweets")

    threads = build_threads(relevant_df, brand_id)
    print(f"Built {len(threads):,} threads")

    # Stats
    resolved = sum(1 for t in threads if t["resolution"]["resolved"])
    avg_len = sum(t["n_messages"] for t in threads) / max(len(threads), 1)
    print(f"  Resolved: {resolved:,} ({resolved/max(len(threads),1):.1%})")
    print(f"  Avg messages/thread: {avg_len:.1f}")

    # Save
    out = DATA_PROCESSED / "threads.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for t in threads:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
