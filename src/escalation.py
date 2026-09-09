"""
Phase 11: Escalation policy.

Conservative escalation with explicit reasons.
"""

import json
from src.config import (ESCALATION_CONFIDENCE_THRESHOLD,
                        RETRIEVAL_SCORE_THRESHOLD, PROMPTS)


# Keywords/patterns that signal escalation
SECURITY_KEYWORDS = [
    "hack", "hacked", "unauthorized", "stolen", "breach", "security",
    "locked out", "compromised", "identity theft", "fraud", "phishing",
]

LEGAL_KEYWORDS = [
    "lawyer", "legal", "sue", "suing", "lawsuit", "attorney",
    "consumer protection", "ftc", "regulation", "court",
]

SAFETY_KEYWORDS = [
    "threat", "threatening", "harm", "danger", "emergency",
]

REPEATED_KEYWORDS = [
    "again", "still not resolved", "third time", "fourth time",
    "multiple times", "keep telling", "already contacted",
    "been waiting for weeks", "no one has helped",
]

ANGER_KEYWORDS = [
    "furious", "outraged", "unacceptable", "disgusting", "worst company",
    "never again", "scam", "thieves", "terrible", "horrible",
]

HIGH_VALUE_KEYWORDS = [
    "large amount", "significant charge", "thousands",
    "unauthorized charge", "wrong amount",
]


def escalation_decision(
    message: str,
    intent: str,
    classifier_confidence: float,
    retrieval_results: list[dict],
    reply_confidence: float,
    context: list[str] = None,
) -> dict:
    """
    Decide whether to auto-handle or escalate.

    Returns: {"decision": "AUTO"|"ESCALATE", "reason": str, "signals": list}
    """
    text_lower = message.lower()
    signals = []

    # 1. Security/account compromise
    security_hits = [w for w in SECURITY_KEYWORDS if w in text_lower]
    if len(security_hits) >= 1:
        signals.append(f"security_concern: {', '.join(security_hits)}")

    # 2. Legal/regulatory
    legal_hits = [w for w in LEGAL_KEYWORDS if w in text_lower]
    if legal_hits:
        signals.append(f"legal_concern: {', '.join(legal_hits)}")

    # 3. Safety
    safety_hits = [w for w in SAFETY_KEYWORDS if w in text_lower]
    if safety_hits:
        signals.append(f"safety_concern: {', '.join(safety_hits)}")

    # 4. Repeated unresolved issue
    repeat_hits = [w for w in REPEATED_KEYWORDS if w in text_lower]
    if len(repeat_hits) >= 2:
        signals.append(f"repeated_unresolved: {', '.join(repeat_hits)}")

    # 5. Extreme anger
    anger_hits = [w for w in ANGER_KEYWORDS if w in text_lower]
    if len(anger_hits) >= 2:
        signals.append(f"customer_very_angry: {', '.join(anger_hits)}")

    # 6. High-value financial
    value_hits = [w for w in HIGH_VALUE_KEYWORDS if w in text_lower]
    if value_hits:
        signals.append(f"high_value_issue: {', '.join(value_hits)}")

    # 7. Low classifier confidence
    if classifier_confidence < ESCALATION_CONFIDENCE_THRESHOLD:
        signals.append(f"low_classifier_confidence: {classifier_confidence:.2f}")

    # 8. Insufficient retrieval evidence
    if retrieval_results:
        best_score = max(r.get("score", 0) for r in retrieval_results)
        if best_score < RETRIEVAL_SCORE_THRESHOLD:
            signals.append(f"weak_retrieval: best_score={best_score:.2f}")
    else:
        signals.append("no_retrieval_results")

    # 9. Low reply confidence
    if reply_confidence < 0.3:
        signals.append(f"low_reply_confidence: {reply_confidence:.2f}")

    # 10. Context: deep thread suggests unresolved complexity
    if context and len(context) > 6:
        signals.append(f"deep_thread: {len(context)} messages")

    # Decision logic: escalate if any high-priority signal or 2+ medium signals
    high_priority = ["security_concern", "legal_concern", "safety_concern"]
    has_high = any(any(hp in s for hp in high_priority) for s in signals)

    if has_high:
        reason = f"High-priority escalation signal: {signals[0]}"
        return {"decision": "ESCALATE", "reason": reason, "signals": signals}

    if len(signals) >= 2:
        reason = f"Multiple escalation signals ({len(signals)}): " + "; ".join(signals[:3])
        return {"decision": "ESCALATE", "reason": reason, "signals": signals}

    if len(signals) == 1 and any(k in signals[0] for k in ["repeated", "angry", "no_retrieval"]):
        reason = f"Escalation signal: {signals[0]}"
        return {"decision": "ESCALATE", "reason": reason, "signals": signals}

    # Auto-handle
    if signals:
        reason = f"Auto-handling despite minor signal: {signals[0]}"
    else:
        reason = "No escalation signals detected. Confident auto-handling."

    return {"decision": "AUTO", "reason": reason, "signals": signals}


def save_escalation_prompt():
    """Save the escalation rules as a prompt file for documentation."""
    prompt = """# Escalation Policy

## ESCALATE immediately for:
- Security concerns (hack, unauthorized access, data breach)
- Legal/regulatory threats (lawyers, lawsuits, regulatory complaints)
- Safety concerns (threats, harm, emergency)

## ESCALATE if 2+ of:
- Repeated unresolved issues (customer says "again", "third time")
- Extreme customer anger (furious, outraged, "worst company")
- Low classifier confidence (< 0.4)
- Weak retrieval matches (best score < 0.3)
- Low reply confidence (< 0.3)
- Deep conversation thread (> 6 messages)
- High-value financial issue

## AUTO-HANDLE when:
- Clear intent classification (confidence > 0.4)
- Good retrieval matches (score > 0.3)
- Standard tone and routine request
- Single, well-understood issue

## Philosophy:
Conservative — prefer false escalation over false auto-handle.
A missed escalation risks customer harm; an unnecessary escalation
only costs a human agent's time.
"""
    PROMPTS.mkdir(parents=True, exist_ok=True)
    path = PROMPTS / "escalation.txt"
    path.write_text(prompt, encoding="utf-8")
    return path
