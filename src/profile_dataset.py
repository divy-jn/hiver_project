"""
Phase 1: Dataset profiling.

Produces:
  data/processed/dataset_profile.json   (machine-readable)
  reports/dataset_profile.md            (human-readable)
"""

import json
import sys
import pandas as pd
import numpy as np
from collections import Counter
from src.config import RAW_CSV, DATA_PROCESSED, REPORTS, ensure_dirs


def load_raw(path=None):
    """Load raw CSV with minimal dtype coercion."""
    path = path or RAW_CSV
    if not path.exists():
        print(f"ERROR: {path} not found.")
        print("Download from: https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter")
        print(f"Place the file at: {path}")
        sys.exit(1)
    df = pd.read_csv(path, dtype={"tweet_id": str, "in_response_to_tweet_id": str})
    return df


def profile(df: pd.DataFrame) -> dict:
    """Compute a comprehensive profile of the dataset."""
    # Basic stats
    n_rows, n_cols = df.shape
    columns = list(df.columns)
    dtypes = {c: str(df[c].dtype) for c in columns}
    missing = {c: int(df[c].isna().sum()) for c in columns}
    n_duplicates = int(df.duplicated().sum())

    # Inbound vs outbound
    # Convention: author_id that appears in 'in_response_to_tweet_id' targets are brands
    has_response_to = df["in_response_to_tweet_id"].notna()
    n_responses = int(has_response_to.sum())
    n_initiating = int((~has_response_to).sum())

    # Unique authors
    n_authors = int(df["author_id"].nunique())

    # Identify likely brand accounts: authors who appear frequently and mostly respond
    author_counts = df["author_id"].value_counts()
    response_authors = df.loc[has_response_to, "author_id"].value_counts()

    # Brand heuristic: author has >50 tweets AND >80% are responses
    brand_candidates = []
    for author, total in author_counts.items():
        resp_count = response_authors.get(author, 0)
        if total >= 50 and resp_count / total > 0.5:
            brand_candidates.append({
                "author_id": str(author),
                "total_tweets": int(total),
                "response_tweets": int(resp_count),
                "response_ratio": round(resp_count / total, 3),
            })
    brand_candidates.sort(key=lambda x: x["total_tweets"], reverse=True)

    # Timestamp range
    if "created_at" in df.columns and df["created_at"].notna().any():
        timestamps = pd.to_datetime(df["created_at"], errors="coerce")
        ts_min = str(timestamps.min())
        ts_max = str(timestamps.max())
    else:
        ts_min = ts_max = "unavailable"

    # Text length distribution
    text_col = "text" if "text" in df.columns else None
    if text_col:
        lengths = df[text_col].dropna().str.len()
        text_stats = {
            "mean": round(float(lengths.mean()), 1),
            "median": round(float(lengths.median()), 1),
            "min": int(lengths.min()),
            "max": int(lengths.max()),
            "p25": round(float(lengths.quantile(0.25)), 1),
            "p75": round(float(lengths.quantile(0.75)), 1),
        }
    else:
        text_stats = {}

    # Reply chain structure
    n_reply_targets = int(df["in_response_to_tweet_id"].nunique())

    # Thread estimation: tweets that are responded to
    responded_tweet_ids = set(df.loc[has_response_to, "in_response_to_tweet_id"].dropna())
    all_tweet_ids = set(df["tweet_id"].dropna())
    n_thread_roots = len(responded_tweet_ids & all_tweet_ids)

    return {
        "row_count": n_rows,
        "column_count": n_cols,
        "columns": columns,
        "dtypes": dtypes,
        "missing_values": missing,
        "duplicate_rows": n_duplicates,
        "n_initiating_tweets": n_initiating,
        "n_response_tweets": n_responses,
        "n_unique_authors": n_authors,
        "n_unique_reply_targets": n_reply_targets,
        "timestamp_range": {"min": ts_min, "max": ts_max},
        "text_length_stats": text_stats,
        "n_brand_candidates": len(brand_candidates),
        "top_brand_candidates": brand_candidates[:20],
        "n_thread_roots_in_dataset": n_thread_roots,
    }


def write_markdown(profile_data: dict, path):
    """Write human-readable profile report."""
    lines = [
        "# Dataset Profile: Customer Support on Twitter",
        "",
        f"**Rows**: {profile_data['row_count']:,}",
        f"**Columns**: {profile_data['column_count']}",
        f"**Duplicate rows**: {profile_data['duplicate_rows']:,}",
        "",
        "## Columns",
        "",
        "| Column | Dtype | Missing |",
        "|--------|-------|---------|",
    ]
    for col in profile_data["columns"]:
        dtype = profile_data["dtypes"][col]
        miss = profile_data["missing_values"][col]
        lines.append(f"| {col} | {dtype} | {miss:,} |")

    lines += [
        "",
        "## Message Distribution",
        "",
        f"- **Initiating tweets** (no `in_response_to`): {profile_data['n_initiating_tweets']:,}",
        f"- **Response tweets**: {profile_data['n_response_tweets']:,}",
        f"- **Unique authors**: {profile_data['n_unique_authors']:,}",
        f"- **Unique reply targets**: {profile_data['n_unique_reply_targets']:,}",
        "",
        "## Timestamps",
        "",
        f"- **Min**: {profile_data['timestamp_range']['min']}",
        f"- **Max**: {profile_data['timestamp_range']['max']}",
        "",
        "## Text Length",
        "",
    ]
    if profile_data["text_length_stats"]:
        ts = profile_data["text_length_stats"]
        lines.append(f"- Mean: {ts['mean']}, Median: {ts['median']}")
        lines.append(f"- Range: [{ts['min']}, {ts['max']}]")
        lines.append(f"- IQR: [{ts['p25']}, {ts['p75']}]")

    lines += [
        "",
        "## Thread Structure",
        "",
        f"- **Thread roots found in dataset**: {profile_data['n_thread_roots_in_dataset']:,}",
        "",
        "## Top Brand Candidates",
        "",
        "| Author ID | Total Tweets | Responses | Response Ratio |",
        "|-----------|-------------|-----------|----------------|",
    ]
    for b in profile_data["top_brand_candidates"]:
        lines.append(
            f"| {b['author_id']} | {b['total_tweets']:,} | "
            f"{b['response_tweets']:,} | {b['response_ratio']:.1%} |"
        )
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ensure_dirs()
    print("Loading dataset...")
    df = load_raw()
    print(f"Loaded {len(df):,} rows, {len(df.columns)} columns")

    print("Profiling...")
    result = profile(df)

    out_json = DATA_PROCESSED / "dataset_profile.json"
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved: {out_json}")

    out_md = REPORTS / "dataset_profile.md"
    write_markdown(result, out_md)
    print(f"Saved: {out_md}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Rows:            {result['row_count']:,}")
    print(f"Initiating:      {result['n_initiating_tweets']:,}")
    print(f"Responses:       {result['n_response_tweets']:,}")
    print(f"Brand candidates: {result['n_brand_candidates']}")
    print(f"Thread roots:    {result['n_thread_roots_in_dataset']:,}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
