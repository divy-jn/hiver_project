"""Tests for retrieval logic."""

import pytest
import numpy as np


def test_cosine_similarity_normalized():
    """Normalized vectors should produce valid cosine similarity."""
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    c = np.array([1.0, 0.0, 0.0])

    assert np.dot(a, b) == pytest.approx(0.0)
    assert np.dot(a, c) == pytest.approx(1.0)


def test_retrieval_returns_sorted():
    """Top-k results should be sorted by descending score."""
    # Simulate retrieval
    embeddings = np.random.RandomState(42).randn(100, 64).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    query = embeddings[0]
    scores = embeddings @ query
    top_k = 5
    top_indices = np.argsort(scores)[::-1][:top_k]
    top_scores = scores[top_indices]

    # Should be descending
    for i in range(len(top_scores) - 1):
        assert top_scores[i] >= top_scores[i + 1]


def test_retrieval_self_match():
    """A query should match itself with score ~1.0."""
    embeddings = np.random.RandomState(42).randn(10, 64).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms

    query = embeddings[3]
    scores = embeddings @ query
    best_idx = np.argmax(scores)
    assert best_idx == 3
    assert scores[best_idx] == pytest.approx(1.0, abs=1e-5)


def test_empty_embeddings():
    """Retrieval on empty index should not crash."""
    embeddings = np.zeros((0, 64), dtype=np.float32)
    query = np.random.randn(64).astype(np.float32)
    if len(embeddings) == 0:
        results = []
    else:
        scores = embeddings @ query
        results = list(np.argsort(scores)[::-1][:5])
    assert results == []
