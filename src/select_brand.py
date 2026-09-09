"""
Phase 2: Brand selection.

Scores candidate brands on multiple factors and selects the best one
for building our support agent.

Produces:
  data/processed/selected_brand.json
"""

import json
import sys
import pandas as pd
import numpy as np
from src.config import RAW_CSV, DATA_PROCESSED, ensure_dirs
from src.profile_dataset import load_raw


def identify_brands(df: pd.DataFrame) -> list[str]:
    """Identify brand accounts: high volume + mostly responses."""
    has_resp = df["in_response_to_tweet_id"].notna()
    author_total = df["author_id"].value_counts()
    author_resp = df.loc[has_resp, "author_id"].value_counts()

    brands = []
    for author, total in author_total.items():
        resp = author_resp.get(author, 0)
        if total >= 100 and resp / total > 0.5:
            brands.append(str(author))
    return brands


def score_brand(df: pd.DataFrame, brand_id: str) -> dict:
    """Score a single brand on multiple factors."""
    # Brand's tweets
    brand_tweets = df[df["author_id"] == brand_id]
    brand_tweet_ids = set(brand_tweets["tweet_id"])

    # Customer tweets that the brand replied to
    brand_responses = brand_tweets[brand_tweets["in_response_to_tweet_id"].notna()]
    customer_tweet_ids_replied = set(brand_responses["in_response_to_tweet_id"])

    # Customer tweets in dataset that the brand replied to
    customer_tweets = df[df["tweet_id"].isin(customer_tweet_ids_replied)]

    n_conversations = len(customer_tweet_ids_replied)
    n_customer_msgs = len(customer_tweets)
    n_brand_responses = len(brand_responses)

    # Thread depth: how many back-and-forth exchanges
    # Find chains: customer -> brand -> customer -> brand ...
    replied_to_brand = df[df["in_response_to_tweet_id"].isin(brand_tweet_ids)]
    customer_followups = replied_to_brand[replied_to_brand["author_id"] != brand_id]
    n_multi_turn = len(customer_followups)

    # Resolution heuristic: brand has last message in thread
    # (simplified: brand responded and no further customer reply)
    brand_resp_ids = set(brand_responses["tweet_id"])
    further_replies = df[df["in_response_to_tweet_id"].isin(brand_resp_ids)]
    customer_further = further_replies[further_replies["author_id"] != brand_id]
    n_resolved_approx = n_brand_responses - len(customer_further)

    # Text diversity (unique trigrams in customer messages as proxy for intent diversity)
    if len(customer_tweets) > 0 and "text" in customer_tweets.columns:
        sample = customer_tweets["text"].dropna().head(2000)
        from sklearn.feature_extraction.text import CountVectorizer
        try:
            cv = CountVectorizer(ngram_range=(1, 2), max_features=500, stop_words="english")
            cv.fit(sample)
            n_vocab = len(cv.vocabulary_)
        except Exception:
            n_vocab = 0
    else:
        n_vocab = 0

    # Avg response length
    avg_resp_len = float(brand_tweets["text"].dropna().str.len().mean()) if "text" in brand_tweets.columns else 0

    # Score: weighted combination
    score = (
        0.25 * min(n_conversations / 5000, 1.0)      # enough conversations
        + 0.15 * min(n_multi_turn / 1000, 1.0)        # multi-turn depth
        + 0.20 * min(n_resolved_approx / 3000, 1.0)   # resolved conversations
        + 0.20 * min(n_vocab / 400, 1.0)               # intent diversity
        + 0.10 * min(avg_resp_len / 150, 1.0)          # substantive responses
        + 0.10 * min(n_customer_msgs / 5000, 1.0)      # customer message volume
    )

    return {
        "brand_id": brand_id,
        "n_conversations": n_conversations,
        "n_customer_messages": n_customer_msgs,
        "n_brand_responses": n_brand_responses,
        "n_multi_turn": n_multi_turn,
        "n_resolved_approx": n_resolved_approx,
        "vocab_diversity": n_vocab,
        "avg_response_length": round(avg_resp_len, 1),
        "selection_score": round(score, 4),
    }


def main():
    ensure_dirs()
    print("Loading dataset...")
    df = load_raw()

    print("Identifying brand accounts...")
    brands = identify_brands(df)
    print(f"Found {len(brands)} brand candidates")

    print("Scoring brands (this may take a minute)...")
    scores = []
    for i, brand in enumerate(brands):
        if i % 10 == 0:
            print(f"  Scoring {i+1}/{len(brands)}...")
        scores.append(score_brand(df, brand))

    scores.sort(key=lambda x: x["selection_score"], reverse=True)

    # Select top brand
    selected = scores[0]
    alternatives = scores[1:6]

    result = {
        "brand": selected["brand_id"],
        "identifier": selected["brand_id"],
        "selection_score": selected["selection_score"],
        "reason": (
            f"Selected {selected['brand_id']} with score {selected['selection_score']:.4f}. "
            f"It has {selected['n_conversations']:,} conversations, "
            f"{selected['n_resolved_approx']:,} approximately resolved, "
            f"vocabulary diversity of {selected['vocab_diversity']}, "
            f"and {selected['n_multi_turn']:,} multi-turn exchanges. "
            f"This gives the strongest evaluation story with sufficient volume, "
            f"diversity, and resolution data."
        ),
        "stats": selected,
        "alternatives_considered": [
            {"brand": a["brand_id"], "score": a["selection_score"],
             "conversations": a["n_conversations"]}
            for a in alternatives
        ],
        "all_rankings": scores[:20],
    }

    out = DATA_PROCESSED / "selected_brand.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")

    print(f"\n{'='*60}")
    print(f"SELECTED BRAND: {selected['brand_id']}")
    print(f"Score: {selected['selection_score']:.4f}")
    print(f"Conversations: {selected['n_conversations']:,}")
    print(f"Resolved: {selected['n_resolved_approx']:,}")
    print(f"Multi-turn: {selected['n_multi_turn']:,}")
    print(f"Diversity: {selected['vocab_diversity']}")
    print(f"{'='*60}")

    print("\nTop 10 brands:")
    print(f"{'Rank':<5} {'Brand':<20} {'Score':<8} {'Convos':<10} {'Resolved':<10}")
    for i, s in enumerate(scores[:10]):
        print(f"{i+1:<5} {s['brand_id']:<20} {s['selection_score']:<8.4f} "
              f"{s['n_conversations']:<10,} {s['n_resolved_approx']:<10,}")


if __name__ == "__main__":
    main()
