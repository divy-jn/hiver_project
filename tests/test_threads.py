"""Tests for thread reconstruction logic."""

import json
import pytest
import pandas as pd
from src.build_threads import build_threads


@pytest.fixture
def sample_df():
    """Create a minimal DataFrame simulating the raw dataset."""
    return pd.DataFrame({
        "tweet_id": ["1", "2", "3", "4", "5", "6"],
        "author_id": ["customer1", "brand1", "customer1", "brand1", "customer2", "brand1"],
        "text": [
            "I have a problem with my order",
            "Sorry to hear that! Can you share your order number?",
            "Order #12345",
            "Thanks! We'll look into it right away.",
            "Why was I charged twice?",
            "We apologize for the inconvenience. We'll issue a refund.",
        ],
        "in_response_to_tweet_id": [None, "1", "2", "3", None, "5"],
        "created_at": [
            "2017-10-01 10:00:00",
            "2017-10-01 10:05:00",
            "2017-10-01 10:10:00",
            "2017-10-01 10:15:00",
            "2017-10-02 09:00:00",
            "2017-10-02 09:10:00",
        ],
    })


def test_build_threads_basic(sample_df):
    """Threads should be reconstructed from reply chains."""
    threads = build_threads(sample_df, "brand1")
    assert len(threads) >= 1
    for t in threads:
        assert "thread_id" in t
        assert "messages" in t
        assert len(t["messages"]) >= 2


def test_thread_has_customer_and_brand(sample_df):
    """Each thread should contain both customer and brand messages."""
    threads = build_threads(sample_df, "brand1")
    for t in threads:
        author_types = {m["author_type"] for m in t["messages"]}
        assert "customer" in author_types
        assert "brand" in author_types


def test_thread_resolution(sample_df):
    """Threads where brand has last message should be marked resolved."""
    threads = build_threads(sample_df, "brand1")
    # At least one thread should be resolved
    resolved = [t for t in threads if t["resolution_heuristic"]["is_resolved_heuristic"]]
    assert len(resolved) >= 1
    for t in resolved:
        assert t["resolution_heuristic"]["response_text"] != ""


def test_thread_messages_have_text(sample_df):
    """All messages should have non-empty text."""
    threads = build_threads(sample_df, "brand1")
    for t in threads:
        for m in t["messages"]:
            assert m["text"] != ""
            assert m["author_type"] in ("customer", "brand")


def test_empty_dataset():
    """Empty DataFrame should produce no threads."""
    df = pd.DataFrame({
        "tweet_id": [],
        "author_id": [],
        "text": [],
        "in_response_to_tweet_id": [],
        "created_at": [],
    })
    threads = build_threads(df, "brand1")
    assert threads == []


def test_no_brand_messages():
    """Dataset with no brand messages should produce no threads."""
    df = pd.DataFrame({
        "tweet_id": ["1"],
        "author_id": ["customer1"],
        "text": ["Hello"],
        "in_response_to_tweet_id": [None],
        "created_at": ["2017-01-01"],
    })
    threads = build_threads(df, "brand1")
    assert threads == []
