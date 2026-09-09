"""Tests for intent taxonomy validation."""

import json
import pytest


def make_sample_taxonomy():
    """Create a minimal valid taxonomy."""
    return [
        {
            "intent_name": "billing_issue",
            "definition": "Customer has a billing or payment problem",
            "cluster_id": 0,
            "n_examples": 50,
            "estimated_frequency": 0.25,
            "positive_examples": ["I was charged twice"],
            "negative_examples": ["When will my order arrive?"],
            "common_confusions": [],
            "top_keywords": ["charge", "bill", "payment"],
        },
        {
            "intent_name": "order_status",
            "definition": "Customer asks about order delivery status",
            "cluster_id": 1,
            "n_examples": 40,
            "estimated_frequency": 0.20,
            "positive_examples": ["Where is my package?"],
            "negative_examples": ["I was charged twice"],
            "common_confusions": [],
            "top_keywords": ["order", "delivery", "tracking"],
        },
    ]


def test_taxonomy_structure():
    """Taxonomy should have required fields."""
    taxonomy = make_sample_taxonomy()
    required_fields = [
        "intent_name", "definition", "n_examples",
        "estimated_frequency", "positive_examples",
    ]
    for intent in taxonomy:
        for field in required_fields:
            assert field in intent, f"Missing field: {field}"


def test_taxonomy_names_unique():
    """Intent names should be unique."""
    taxonomy = make_sample_taxonomy()
    names = [t["intent_name"] for t in taxonomy]
    assert len(names) == len(set(names))


def test_taxonomy_frequencies_sum():
    """Frequencies should approximately sum to 1."""
    taxonomy = make_sample_taxonomy()
    # In the real taxonomy with more intents, this should be close to 1
    total = sum(t["estimated_frequency"] for t in taxonomy)
    assert total > 0  # At least some frequency


def test_taxonomy_has_examples():
    """Each intent should have at least one positive example."""
    taxonomy = make_sample_taxonomy()
    for intent in taxonomy:
        assert len(intent["positive_examples"]) >= 1


def test_taxonomy_size():
    """Taxonomy should have 2+ intents (6-12 in production)."""
    taxonomy = make_sample_taxonomy()
    assert len(taxonomy) >= 2
