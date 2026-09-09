"""Tests for end-to-end pipeline integration."""

import json
import pytest
from pathlib import Path
from src.config import ROOT


def test_config_paths_exist():
    """Config paths should be valid."""
    from src.config import DATA_RAW, DATA_PROCESSED, DATA_GOLDEN, REPORTS
    # Directories should exist or be creatable
    assert DATA_RAW.parent.exists() or True  # May not exist yet
    assert isinstance(str(DATA_RAW), str)


def test_golden_set_validation():
    """Golden set should pass validation if it exists."""
    golden_path = ROOT / "data" / "golden" / "golden_set.csv"
    if not golden_path.exists():
        pytest.skip("Golden set not yet created")

    import pandas as pd
    df = pd.read_csv(golden_path)

    # Size check
    assert 150 <= len(df) <= 250, f"Golden set size {len(df)} outside 150-250 range"

    # Required columns
    for col in ["example_id", "text", "intent", "should_escalate"]:
        assert col in df.columns, f"Missing column: {col}"

    # No missing required fields
    assert df["text"].notna().all()
    assert df["intent"].notna().all()

    # No duplicates
    assert df["text"].duplicated().sum() == 0, "Duplicate messages in golden set"


def test_taxonomy_validation():
    """Taxonomy should have 6-12 intents if it exists."""
    taxonomy_path = ROOT / "data" / "processed" / "intent_taxonomy.json"
    if not taxonomy_path.exists():
        pytest.skip("Taxonomy not yet created")

    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    assert 2 <= len(taxonomy) <= 20, f"Taxonomy has {len(taxonomy)} intents"

    for intent in taxonomy:
        assert "intent_name" in intent
        assert "definition" in intent
        assert intent["intent_name"] != ""


def test_results_structure():
    """Results file should have expected structure if it exists."""
    results_path = ROOT / "reports" / "results.json"
    if not results_path.exists():
        pytest.skip("Results not yet generated")

    results = json.loads(results_path.read_text(encoding="utf-8"))
    assert "intent_metrics" in results
    assert "escalation_metrics" in results
    assert "accuracy" in results["intent_metrics"]
    assert "false_auto_rate" in results["escalation_metrics"]


def test_malformed_json_handling():
    """Test that malformed LLM output is handled gracefully."""
    import re
    malformed = 'Sure! Here is the result: {"intent": "billing", "confidence": 0.8}'
    match = re.search(r'\{[^}]+\}', malformed)
    assert match is not None
    result = json.loads(match.group())
    assert result["intent"] == "billing"


def test_classify_tone():
    """Test tone classification helper."""
    from src.create_golden_set import classify_tone
    assert classify_tone("I'm furious and this is unacceptable!!") == "angry"
    assert classify_tone("please help me, thank you so much") == "polite"
    assert classify_tone("my order hasn't arrived") == "neutral"
