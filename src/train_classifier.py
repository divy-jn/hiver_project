"""
Phase 8: LLM-based intent classifier.

Uses structured JSON output with retry handling and deterministic fallback.

Produces classifications like:
  {"intent": "...", "confidence": 0.91, "reason": "..."}
"""

import json
import re
from src.config import (LLM_API_KEY, LLM_MODEL, LLM_BASE_URL,
                        LLM_TEMPERATURE, LLM_MAX_RETRIES, LLM_TIMEOUT,
                        DATA_PROCESSED, PROMPTS)


def load_taxonomy():
    path = DATA_PROCESSED / "intent_taxonomy.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_system_prompt(taxonomy: list[dict]) -> str:
    """Build the intent classification system prompt."""
    prompt_path = PROMPTS / "intent_classifier.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    lines = [
        "You are an intent classifier for customer support messages.",
        "",
        "Classify the customer message into EXACTLY ONE of the following intents.",
        "Return a JSON object with fields: intent, confidence, reason.",
        "",
        "## Intents",
        "",
    ]
    for intent in taxonomy:
        lines.append(f"### {intent['intent_name']}")
        lines.append(f"Definition: {intent['definition']}")
        if intent.get("positive_examples"):
            lines.append("Examples:")
            for ex in intent["positive_examples"][:2]:
                lines.append(f"  - {ex[:120]}")
        lines.append("")

    lines += [
        "## Output Format",
        'Return ONLY valid JSON: {"intent": "<intent_name>", "confidence": <0.0-1.0>, "reason": "<brief reason>"}',
        "",
        "Rules:",
        "- Choose the MOST SPECIFIC matching intent",
        "- Confidence should reflect how clearly the message matches",
        "- Keep reason under 30 words",
        "- If genuinely unclear, still pick the best match with lower confidence",
    ]
    prompt = "\n".join(lines)

    # Save prompt for reproducibility
    PROMPTS.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt


def classify_intent(message: str, taxonomy: list[dict] = None,
                    _client=None) -> dict:
    """
    Classify a message's intent using LLM.

    Returns: {"intent": str, "confidence": float, "reason": str}
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    intent_names = [t["intent_name"] for t in taxonomy]
    system_prompt = build_system_prompt(taxonomy)

    if not LLM_API_KEY:
        # Fallback: return first intent with low confidence
        return {
            "intent": intent_names[0] if intent_names else "unknown",
            "confidence": 0.1,
            "reason": "No API key — deterministic fallback",
        }

    if _client is None:
        from openai import OpenAI
        kwargs = {"api_key": LLM_API_KEY}
        if LLM_BASE_URL:
            kwargs["base_url"] = LLM_BASE_URL
        _client = OpenAI(**kwargs)

    user_msg = f"Classify this customer message:\n\n{message[:500]}"

    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = _client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=LLM_TEMPERATURE,
                timeout=LLM_TIMEOUT,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            result = json.loads(content)

            # Validate
            intent = result.get("intent", "")
            if intent not in intent_names:
                # Fuzzy match
                for name in intent_names:
                    if name.lower() in intent.lower() or intent.lower() in name.lower():
                        intent = name
                        break
                else:
                    intent = intent_names[0]  # fallback

            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            reason = str(result.get("reason", ""))[:200]

            return {
                "intent": intent,
                "confidence": confidence,
                "reason": reason,
            }

        except json.JSONDecodeError:
            # Try to extract JSON from response
            if content:
                match = re.search(r'\{[^}]+\}', content)
                if match:
                    try:
                        result = json.loads(match.group())
                        return {
                            "intent": result.get("intent", intent_names[0]),
                            "confidence": float(result.get("confidence", 0.3)),
                            "reason": result.get("reason", "Extracted from malformed response"),
                        }
                    except Exception:
                        pass
            if attempt == LLM_MAX_RETRIES - 1:
                break
        except Exception as e:
            if attempt == LLM_MAX_RETRIES - 1:
                print(f"WARNING: LLM classification failed after {LLM_MAX_RETRIES} retries: {e}")
                break

    # Deterministic fallback
    return {
        "intent": intent_names[0] if intent_names else "unknown",
        "confidence": 0.1,
        "reason": "LLM failed — deterministic fallback to most common intent",
    }


if __name__ == "__main__":
    import sys
    taxonomy = load_taxonomy()
    msg = sys.argv[1] if len(sys.argv) > 1 else "I need a refund for my last order"
    result = classify_intent(msg, taxonomy)
    print(json.dumps(result, indent=2))
