"""
Phase 14: LLM-as-judge for reply quality evaluation.

Evaluates generated replies on 6 dimensions with explicit rubric.

Produces structured scores per example.
"""

import json
import re
from src.config import (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL,
                        LLM_TEMPERATURE, LLM_MAX_RETRIES, LLM_TIMEOUT, PROMPTS)


JUDGE_RUBRIC = """You are an expert quality judge for customer support replies.

Evaluate the GENERATED REPLY against the CUSTOMER MESSAGE and HISTORICAL EVIDENCE.

## Scoring Rubric (0 = poor, 1 = acceptable, 2 = good)

### Groundedness (0-2)
- 0: Reply contains claims/actions not supported by any evidence
- 1: Reply is partially grounded but adds unsupported details
- 2: Reply is fully grounded in the provided evidence

### Correctness (0-2)
- 0: Reply contains factual errors or contradicts evidence
- 1: Reply is mostly correct but has minor inaccuracies
- 2: Reply is factually accurate and consistent

### Resolution Match (0-2)
- 0: Reply does not address the customer's issue
- 1: Reply partially addresses the issue
- 2: Reply directly addresses and attempts to resolve the issue

### Relevance (0-2)
- 0: Reply is off-topic or generic
- 1: Reply is somewhat relevant but misses key aspects
- 2: Reply is highly relevant and focused

### Tone (0-2)
- 0: Reply is inappropriate, rude, or robotic
- 1: Reply is acceptable but could be more empathetic/professional
- 2: Reply matches professional support tone, empathetic where needed

### Completeness (0-2)
- 0: Reply misses critical information or next steps
- 1: Reply covers main points but misses some details
- 2: Reply is thorough and includes necessary next steps

## Output
Return ONLY valid JSON:
{
  "groundedness": <0-2>,
  "correctness": <0-2>,
  "resolution_match": <0-2>,
  "relevance": <0-2>,
  "tone": <0-2>,
  "completeness": <0-2>,
  "overall": <sum 0-12>,
  "failure_tags": ["<tag1>", ...],
  "brief_justification": "<1-2 sentences>"
}

Possible failure_tags: hallucination, wrong_intent, generic_response, missing_info,
inappropriate_tone, over_promising, under_delivering, off_topic, no_resolution"""


def save_judge_prompt():
    """Save judge prompt for documentation."""
    PROMPTS.mkdir(parents=True, exist_ok=True)
    path = PROMPTS / "judge.txt"
    path.write_text(JUDGE_RUBRIC, encoding="utf-8")
    return path


def judge_reply(
    customer_message: str,
    generated_reply: str,
    intent: str,
    retrieval_evidence: list[dict] = None,
    _client=None,
) -> dict:
    """
    Judge a generated reply's quality.

    Returns: scores dict with 6 dimensions + overall + failure_tags
    """
    # Build evaluation context
    parts = [f"## Customer Message\n{customer_message[:500]}"]
    parts.append(f"\n## Detected Intent: {intent}")

    if retrieval_evidence:
        parts.append("\n## Historical Evidence Provided to Generator")
        for i, ev in enumerate(retrieval_evidence[:3]):
            parts.append(f"\nEvidence {i+1}:")
            parts.append(f"Customer: {ev.get('historical_customer_message', '')[:200]}")
            parts.append(f"Brand: {ev.get('historical_brand_response', '')[:200]}")

    parts.append(f"\n## Generated Reply to Evaluate\n{generated_reply[:500]}")

    user_msg = "\n".join(parts)

    if not OPENAI_API_KEY:
        # Cannot judge without API
        return _default_scores("no_api_key")

    if _client is None:
        from openai import OpenAI
        kwargs = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL
        _client = OpenAI(**kwargs)

    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = _client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": JUDGE_RUBRIC},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,  # Judge should be deterministic
                timeout=LLM_TIMEOUT,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            result = json.loads(content)

            # Validate and clamp scores
            scores = {}
            for dim in ["groundedness", "correctness", "resolution_match",
                        "relevance", "tone", "completeness"]:
                val = result.get(dim, 1)
                scores[dim] = max(0, min(2, int(val)))

            scores["overall"] = sum(scores[d] for d in
                                    ["groundedness", "correctness", "resolution_match",
                                     "relevance", "tone", "completeness"])
            scores["failure_tags"] = result.get("failure_tags", [])
            scores["brief_justification"] = str(result.get("brief_justification", ""))[:300]

            return scores

        except Exception as e:
            if attempt == LLM_MAX_RETRIES - 1:
                print(f"WARNING: Judge failed: {e}")

    return _default_scores("judge_failed")


def _default_scores(reason: str) -> dict:
    return {
        "groundedness": -1,
        "correctness": -1,
        "resolution_match": -1,
        "relevance": -1,
        "tone": -1,
        "completeness": -1,
        "overall": -1,
        "failure_tags": [reason],
        "brief_justification": f"Scoring unavailable: {reason}",
    }
