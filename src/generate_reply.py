"""
Phase 10: Grounded reply generation.

Generates replies using retrieved historical examples as evidence.
Explicitly prevents hallucination and policy invention.
"""

import json
import re
from src.config import (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL,
                        LLM_TEMPERATURE, LLM_MAX_RETRIES, LLM_TIMEOUT, PROMPTS)


def build_reply_prompt() -> str:
    """Build the reply generation system prompt."""
    prompt_path = PROMPTS / "reply_generator.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    prompt = """You are a customer support agent drafting a reply to a customer message.

## Rules — STRICTLY FOLLOW
1. Base your reply ONLY on the historical examples provided below
2. Do NOT invent policies, refunds, credits, dates, account changes, or actions
3. Do NOT claim to have performed any action unless the system actually did
4. If historical examples show a consistent resolution pattern, follow it
5. If examples are insufficient or conflicting, ask the customer for more information
6. Preserve the brand's historical support tone (observe how they write)
7. Do NOT leak internal information or system details
8. Keep the reply concise and professional
9. If you cannot confidently help, say you'll connect them with a specialist

## Output Format
Return ONLY valid JSON:
{
  "reply": "<your drafted reply>",
  "grounding_used": ["<thread_id_1>", "<thread_id_2>"],
  "confidence": <0.0-1.0>
}

confidence should be:
- 0.8-1.0: Strong historical precedent, clear resolution path
- 0.5-0.8: Partial match, reasonable inference
- 0.2-0.5: Weak evidence, reply is best-effort
- 0.0-0.2: Very little grounding, mostly asking for info"""

    PROMPTS.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt


def generate_reply(message: str, intent: str, retrieval_results: list[dict],
                   context: list[str] = None, _client=None) -> dict:
    """
    Generate a grounded reply using historical examples.

    Returns: {"reply": str, "grounding_used": list, "confidence": float}
    """
    system_prompt = build_reply_prompt()

    # Build user message with evidence
    parts = [f"## Customer Message\n{message[:500]}"]

    if context:
        parts.append(f"\n## Conversation Context\n" +
                     "\n".join(c[:200] for c in context[-3:]))

    parts.append(f"\n## Detected Intent: {intent}")

    parts.append("\n## Historical Examples (use these as evidence)")
    if retrieval_results:
        for i, r in enumerate(retrieval_results[:5]):
            parts.append(f"\n### Example {i+1} (similarity: {r.get('score', 'N/A')})")
            parts.append(f"Customer: {r['historical_customer_message'][:200]}")
            parts.append(f"Brand response: {r['historical_brand_response'][:300]}")
            parts.append(f"Thread ID: {r.get('thread_id', 'unknown')}")
    else:
        parts.append("No similar historical examples found.")

    user_msg = "\n".join(parts)

    if not OPENAI_API_KEY:
        # Fallback: template response
        if retrieval_results:
            return {
                "reply": f"Thank you for reaching out. Based on similar cases, "
                         f"I'd like to help resolve your {intent.replace('_', ' ')} issue. "
                         f"Could you please provide more details so I can assist you better?",
                "grounding_used": [r.get("thread_id", "") for r in retrieval_results[:2]],
                "confidence": 0.2,
            }
        return {
            "reply": "Thank you for contacting us. Let me look into this for you. "
                     "Could you please provide more details about your issue?",
            "grounding_used": [],
            "confidence": 0.1,
        }

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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=LLM_TEMPERATURE,
                timeout=LLM_TIMEOUT,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            result = json.loads(content)

            return {
                "reply": str(result.get("reply", ""))[:1000],
                "grounding_used": result.get("grounding_used", []),
                "confidence": float(result.get("confidence", 0.5)),
            }

        except json.JSONDecodeError:
            if content:
                # Try to salvage
                match = re.search(r'"reply"\s*:\s*"([^"]*)"', content)
                if match:
                    return {
                        "reply": match.group(1)[:1000],
                        "grounding_used": [],
                        "confidence": 0.3,
                    }
        except Exception as e:
            if attempt == LLM_MAX_RETRIES - 1:
                print(f"WARNING: Reply generation failed: {e}")

    # Deterministic fallback
    return {
        "reply": "Thank you for reaching out. I understand your concern and "
                 "I'll need to look into this further. Let me connect you with "
                 "a specialist who can help resolve this for you.",
        "grounding_used": [],
        "confidence": 0.05,
    }
