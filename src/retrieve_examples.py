"""
Phase 9: Historical resolution retrieval.

Embeds resolved threads and retrieves similar examples for grounding replies.

Produces:
  data/processed/retrieval_index.pkl  (cached)
  data/processed/embeddings.npz      (cached)
"""

import json
import sys
import pickle
import numpy as np
from pathlib import Path
from src.config import DATA_PROCESSED, DATA_GOLDEN, EMBEDDING_MODEL, RETRIEVAL_TOP_K, ensure_dirs


def load_resolved_threads() -> list[dict]:
    """Load threads that have a resolution."""
    path = DATA_PROCESSED / "threads.jsonl"
    if not path.exists():
        print("ERROR: Run build_threads first.")
        sys.exit(1)

    threads = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            if t.get("resolution_heuristic", {}).get("is_resolved_heuristic", False):
                quality = t.get("resolution_heuristic", {}).get("historical_precedent_quality", "low_quality")
                if quality in ["actionable", "next_step"]:
                    threads.append(t)
    return threads


def build_retrieval_records(threads: list[dict]) -> list[dict]:
    """Build retrieval records from resolved threads, excluding golden threads."""
    import pandas as pd
    golden_path = DATA_GOLDEN / "golden_set.csv"
    golden_ids = set()
    if golden_path.exists():
        golden_df = pd.read_csv(golden_path)
        golden_ids = set(golden_df["thread_id"].dropna().astype(str))
        
    records = []
    for t in threads:
        thread_id_str = str(t["thread_id"])
        if thread_id_str in golden_ids:
            continue
            
        # Extract first customer message and last brand response
        customer_msg = ""
        brand_response = ""
        context_parts = []

        for msg in t["messages"]:
            if msg["author_type"] == "customer" and not customer_msg:
                customer_msg = msg["text"]
            elif msg["author_type"] == "brand":
                brand_response = msg["text"]
            context_parts.append(f"[{msg['author_type']}]: {msg['text'][:100]}")

        if customer_msg and brand_response:
            records.append({
                "customer_message": customer_msg,
                "conversation_context": " | ".join(context_parts[:5]),
                "brand_response": brand_response,
                "resolution_type": t.get("resolution_heuristic", {}).get("resolution_type", "unresolved"),
                "thread_id": t["thread_id"],
            })
    return records


def build_index(records: list[dict], force_rebuild: bool = False):
    """Build or load embedding index."""
    embeddings_path = DATA_PROCESSED / "embeddings.npz"
    index_path = DATA_PROCESSED / "retrieval_index.pkl"

    if not force_rebuild and embeddings_path.exists() and index_path.exists():
        print("Loading cached embeddings...")
        data = np.load(embeddings_path)
        embeddings = data["embeddings"]
        with open(index_path, "rb") as f:
            cached_records = pickle.load(f)
        return embeddings, cached_records

    print(f"Building embeddings with {EMBEDDING_MODEL}...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [r["customer_message"] for r in records]

    # Batch encode
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings = np.array(embeddings, dtype=np.float32)

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    # Save
    np.savez_compressed(embeddings_path, embeddings=embeddings)
    with open(index_path, "wb") as f:
        pickle.dump(records, f)

    print(f"Saved {len(embeddings)} embeddings to {embeddings_path}")
    return embeddings, records


def retrieve(query: str, top_k: int = None, intent_filter: str = None,
             _model=None, _embeddings=None, _records=None) -> list[dict]:
    """
    Retrieve top-k similar historical examples for a query.

    Returns list of:
      {"score": float, "historical_customer_message": str,
       "historical_brand_response": str, "resolution_type": str, "thread_id": str}
    """
    if top_k is None:
        top_k = RETRIEVAL_TOP_K

    if _embeddings is None or _records is None:
        records = build_retrieval_records(load_resolved_threads())
        _embeddings, _records = build_index(records)

    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)

    # Encode query
    query_emb = _model.encode([query[:500]])[0].astype(np.float32)
    query_norm = np.linalg.norm(query_emb)
    if query_norm > 0:
        query_emb = query_emb / query_norm

    # Cosine similarity (embeddings already normalized)
    scores = _embeddings @ query_emb

    # Get top-k
    top_indices = np.argsort(scores)[::-1][:top_k * 3]  # get extra for filtering

    results = []
    for idx in top_indices:
        record = _records[idx]
        result = {
            "score": round(float(scores[idx]), 4),
            "historical_customer_message": record["customer_message"],
            "historical_brand_response": record["brand_response"],
            "resolution_type": record["resolution_type"],
            "thread_id": record["thread_id"],
        }
        results.append(result)

        if len(results) >= top_k:
            break

    return results


class RetrievalEngine:
    """Cached retrieval engine for use in the agent pipeline."""

    def __init__(self):
        self._model = None
        self._embeddings = None
        self._records = None
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(EMBEDDING_MODEL)
        records = build_retrieval_records(load_resolved_threads())
        self._embeddings, self._records = build_index(records)
        self._loaded = True

    def retrieve(self, query: str, top_k: int = None) -> list[dict]:
        self.load()
        return retrieve(query, top_k=top_k,
                       _model=self._model,
                       _embeddings=self._embeddings,
                       _records=self._records)


def main():
    ensure_dirs()
    print("Loading resolved threads...")
    threads = load_resolved_threads()
    print(f"Found {len(threads)} resolved threads")

    records = build_retrieval_records(threads)
    print(f"Built {len(records)} retrieval records")

    embeddings, records = build_index(records, force_rebuild=True)
    print(f"Index built: {embeddings.shape}")

    # Test retrieval
    if records:
        test_query = records[0]["customer_message"]
        results = retrieve(test_query)
        print(f"\nTest query: {test_query[:80]}...")
        print(f"Top {len(results)} results:")
        for r in results:
            print(f"  score={r['score']:.3f}: {r['historical_customer_message'][:80]}...")


if __name__ == "__main__":
    main()
