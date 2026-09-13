"""
Phase 5: Intent discovery from brand's actual support data.

Uses TF-IDF clustering + LLM labeling to derive 6-12 intents.

Produces:
  data/processed/intent_taxonomy.json
  reports/intent_taxonomy.md
"""

import json
import sys
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import Counter
from src.config import (DATA_PROCESSED, REPORTS, RANDOM_SEED, TARGET_INTENTS,
                        LLM_API_KEY, LLM_MODEL, LLM_BASE_URL,
                        LLM_TEMPERATURE, LLM_MAX_RETRIES, LLM_TIMEOUT, ensure_dirs)


def load_threads() -> list[dict]:
    path = DATA_PROCESSED / "threads.jsonl"
    if not path.exists():
        print("ERROR: Run build_threads first.")
        sys.exit(1)
    threads = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            threads.append(json.loads(line))
    return threads


def extract_customer_messages(threads: list[dict]) -> list[dict]:
    """Extract first customer message from each thread (the support request)."""
    messages = []
    for t in threads:
        for msg in t["messages"]:
            if msg["author_type"] == "customer":
                messages.append({
                    "text": msg["text"],
                    "thread_id": t["thread_id"],
                    "resolved": t.get("resolution_heuristic", {}).get("is_resolved_heuristic", False),
                })
                break  # first customer message only
    return messages


def cluster_messages(messages: list[dict], n_clusters: int = 10) -> tuple:
    """Cluster customer messages using TF-IDF + KMeans."""
    texts = [m["text"] for m in messages]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.8,
    )
    X = vectorizer.fit_transform(texts)

    km = KMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, n_init=10)
    labels = km.fit_predict(X)

    # Get top terms per cluster
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]
    terms = vectorizer.get_feature_names_out()
    cluster_terms = {}
    for i in range(n_clusters):
        top_terms = [terms[ind] for ind in order_centroids[i, :15]]
        cluster_terms[i] = top_terms

    return labels, cluster_terms, vectorizer


def label_clusters_with_llm(cluster_terms: dict, cluster_examples: dict) -> dict:
    """Use LLM to name and define each cluster."""
    if not LLM_API_KEY:
        print("WARNING: No LLM_API_KEY set. Using heuristic labels.")
        return label_clusters_heuristic(cluster_terms)

    from openai import OpenAI
    client_kwargs = {"api_key": LLM_API_KEY}
    if LLM_BASE_URL:
        client_kwargs["base_url"] = LLM_BASE_URL
    client = OpenAI(**client_kwargs)

    prompt = "You are an expert at customer support intent taxonomy design.\n\n"
    prompt += "I have clustered customer support messages into groups. For each cluster, "
    prompt += "I'll give you the top keywords and example messages. "
    prompt += "Please assign a concise snake_case intent name and a one-sentence definition.\n\n"
    prompt += "Return a JSON array of objects with fields: cluster_id, intent_name, definition\n\n"

    for cid, terms in cluster_terms.items():
        prompt += f"Cluster {cid}:\n"
        prompt += f"  Keywords: {', '.join(terms[:10])}\n"
        examples = cluster_examples.get(cid, [])[:5]
        for ex in examples:
            prompt += f"  Example: {ex[:150]}\n"
        prompt += "\n"

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        # Normalize: might be wrapped in {"intents": [...]}
        if isinstance(result, dict):
            for key in ["intents", "clusters", "results"]:
                if key in result:
                    result = result[key]
                    break
            if isinstance(result, dict):
                result = list(result.values())
        return {item["cluster_id"]: item for item in result}
    except Exception as e:
        print(f"WARNING: LLM labeling failed ({e}). Using heuristic labels.")
        return label_clusters_heuristic(cluster_terms)


def label_clusters_heuristic(cluster_terms: dict) -> dict:
    """Fallback: derive intent names from top terms."""
    labels = {}
    for cid, terms in cluster_terms.items():
        # Simple heuristic: use top 2 terms as name
        name = "_".join(terms[:2]).lower().replace(" ", "_")
        labels[cid] = {
            "cluster_id": cid,
            "intent_name": name,
            "definition": f"Customer messages related to: {', '.join(terms[:5])}",
        }
    return labels


def build_taxonomy(messages: list[dict], labels, cluster_terms: dict,
                   cluster_labels: dict) -> list[dict]:
    """Build the final intent taxonomy with examples and stats."""
    # Group messages by cluster
    cluster_msgs = {}
    for msg, label in zip(messages, labels):
        cluster_msgs.setdefault(int(label), []).append(msg)

    taxonomy = []
    for cid in sorted(cluster_msgs.keys()):
        info = cluster_labels.get(cid, {})
        msgs = cluster_msgs[cid]

        # Get positive examples (first 5)
        pos_examples = [m["text"][:200] for m in msgs[:5]]

        # Negative examples: messages from other clusters
        neg_examples = []
        for other_cid, other_msgs in cluster_msgs.items():
            if other_cid != cid and other_msgs:
                neg_examples.append(other_msgs[0]["text"][:200])
            if len(neg_examples) >= 3:
                break

        intent = {
            "intent_name": info.get("intent_name", f"cluster_{cid}"),
            "definition": info.get("definition", ""),
            "cluster_id": cid,
            "n_examples": len(msgs),
            "estimated_frequency": round(len(msgs) / max(sum(len(v) for v in cluster_msgs.values()), 1), 3),
            "positive_examples": pos_examples,
            "negative_examples": neg_examples,
            "common_confusions": [],
            "top_keywords": cluster_terms.get(cid, [])[:10],
        }
        taxonomy.append(intent)

    return taxonomy


def write_taxonomy_md(taxonomy: list[dict], path):
    """Write human-readable intent taxonomy."""
    lines = [
        "# Intent Taxonomy",
        "",
        f"**Total intents**: {len(taxonomy)}",
        "",
    ]

    for intent in taxonomy:
        lines += [
            f"## {intent['intent_name']}",
            "",
            f"**Definition**: {intent['definition']}",
            f"**Frequency**: {intent['estimated_frequency']:.1%} ({intent['n_examples']} examples)",
            f"**Keywords**: {', '.join(intent['top_keywords'][:8])}",
            "",
            "### Positive Examples",
            "",
        ]
        for ex in intent["positive_examples"][:3]:
            lines.append(f"- {ex}")

        lines += ["", "### Negative Examples", ""]
        for ex in intent["negative_examples"][:2]:
            lines.append(f"- {ex}")
        lines += ["", "---", ""]

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ensure_dirs()
    print("Loading threads...")
    threads = load_threads()
    messages = extract_customer_messages(threads)
    print(f"Extracted {len(messages):,} customer messages")

    if len(messages) < 50:
        print("ERROR: Too few messages for clustering. Need at least 50.")
        sys.exit(1)

    # Determine number of clusters
    n_clusters = min(max(TARGET_INTENTS[0], len(messages) // 100), TARGET_INTENTS[1])
    n_clusters = max(n_clusters, TARGET_INTENTS[0])
    print(f"Clustering into {n_clusters} intents...")

    labels, cluster_terms, vectorizer = cluster_messages(messages, n_clusters)

    # Get examples per cluster
    cluster_examples = {}
    for msg, label in zip(messages, labels):
        cluster_examples.setdefault(int(label), []).append(msg["text"])

    print("Labeling clusters...")
    cluster_labels = label_clusters_with_llm(cluster_terms, cluster_examples)

    print("Building taxonomy...")
    taxonomy = build_taxonomy(messages, labels, cluster_terms, cluster_labels)

    # Save JSON
    out_json = DATA_PROCESSED / "intent_taxonomy.json"
    out_json.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {out_json}")

    # Save markdown
    out_md = REPORTS / "intent_taxonomy.md"
    write_taxonomy_md(taxonomy, out_md)
    print(f"Saved: {out_md}")

    # Summary
    print(f"\n{'='*50}")
    print(f"{'Intent':<25} {'Count':<8} {'Freq':<8}")
    print(f"{'-'*50}")
    for intent in sorted(taxonomy, key=lambda x: x["n_examples"], reverse=True):
        print(f"{intent['intent_name']:<25} {intent['n_examples']:<8} {intent['estimated_frequency']:.1%}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
