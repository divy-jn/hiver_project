"""Tests for escalation decision logic."""

import pytest
from src.escalation import escalation_decision


def test_security_escalation():
    """Security keywords should trigger escalation."""
    result = escalation_decision(
        message="Someone hacked my account and made unauthorized charges",
        intent="account_issue",
        classifier_confidence=0.8,
        retrieval_results=[{"score": 0.7}],
        reply_confidence=0.6,
    )
    assert result["decision"] == "ESCALATE"
    assert any("security" in s for s in result["signals"])


def test_legal_escalation():
    """Legal keywords should trigger escalation."""
    result = escalation_decision(
        message="I will contact my lawyer if this is not resolved",
        intent="complaint",
        classifier_confidence=0.9,
        retrieval_results=[{"score": 0.8}],
        reply_confidence=0.7,
    )
    assert result["decision"] == "ESCALATE"
    assert any("legal" in s for s in result["signals"])


def test_routine_auto_handle():
    """Routine request with high confidence should be auto-handled."""
    result = escalation_decision(
        message="Can you tell me the status of my order?",
        intent="order_status",
        classifier_confidence=0.9,
        retrieval_results=[{"score": 0.85}],
        reply_confidence=0.8,
    )
    assert result["decision"] == "AUTO"


def test_low_confidence_escalation():
    """Low classifier + retrieval confidence should escalate."""
    result = escalation_decision(
        message="I have this issue with my thing",
        intent="unknown",
        classifier_confidence=0.2,
        retrieval_results=[{"score": 0.15}],
        reply_confidence=0.1,
    )
    assert result["decision"] == "ESCALATE"


def test_no_retrieval_results():
    """No retrieval results should be an escalation signal."""
    result = escalation_decision(
        message="Something went wrong with my account",
        intent="account_issue",
        classifier_confidence=0.5,
        retrieval_results=[],
        reply_confidence=0.3,
    )
    assert any("no_retrieval" in s for s in result["signals"])


def test_escalation_returns_reason():
    """All escalation decisions must have a reason."""
    for msg, conf in [
        ("hacked my account", 0.9),
        ("where is my order", 0.9),
        ("vague issue", 0.2),
    ]:
        result = escalation_decision(
            message=msg, intent="test",
            classifier_confidence=conf,
            retrieval_results=[{"score": 0.5}],
            reply_confidence=0.5,
        )
        assert result["reason"] != ""
        assert result["decision"] in ("AUTO", "ESCALATE")


def test_angry_customer_escalation():
    """Very angry customer language should contribute to escalation."""
    result = escalation_decision(
        message="This is unacceptable! Worst company ever! I'm furious and disgusted!",
        intent="complaint",
        classifier_confidence=0.8,
        retrieval_results=[{"score": 0.5}],
        reply_confidence=0.5,
    )
    assert any("angry" in s for s in result["signals"])
