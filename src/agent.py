"""
Phase 12: End-to-end support agent.

Orchestrates: classify → retrieve → generate reply → escalation decision.

CLI: python -m src.agent --message "..."
"""

import json
import argparse
import sys
from src.config import ensure_dirs
from src.train_classifier import classify_intent, load_taxonomy
from src.retrieve_examples import RetrievalEngine
from src.generate_reply import generate_reply
from src.escalation import escalation_decision


class SupportAgent:
    """AI customer support agent."""

    def __init__(self, taxonomy=None):
        self.taxonomy = taxonomy or load_taxonomy()
        self.retrieval = RetrievalEngine()
        self._client = None

    def _get_client(self):
        if self._client is None:
            from src.config import LLM_API_KEY, LLM_BASE_URL
            if LLM_API_KEY:
                from openai import OpenAI
                kwargs = {"api_key": LLM_API_KEY}
                if LLM_BASE_URL:
                    kwargs["base_url"] = LLM_BASE_URL
                self._client = OpenAI(**kwargs)
        return self._client

    def handle(self, message: str, context: list[str] = None) -> dict:
        """
        Handle a customer message end-to-end.

        Args:
            message: The customer's message text
            context: Optional list of prior messages in the conversation

        Returns:
            {
                "intent": {"name": str, "confidence": float, "reason": str},
                "retrieval": {"results": list},
                "reply": str,
                "escalation": {"decision": str, "reason": str}
            }
        """
        # Step 1: Classify intent
        intent_result = classify_intent(
            message, self.taxonomy, _client=self._get_client()
        )

        # Step 2: Retrieve historical examples
        try:
            retrieval_results = self.retrieval.retrieve(message)
        except Exception as e:
            print(f"WARNING: Retrieval failed: {e}")
            retrieval_results = []

        # Step 3: Generate grounded reply
        reply_result = generate_reply(
            message=message,
            intent=intent_result["intent"],
            retrieval_results=retrieval_results,
            context=context,
            _client=self._get_client(),
        )

        # Step 4: Escalation decision
        esc_result = escalation_decision(
            message=message,
            intent=intent_result["intent"],
            classifier_confidence=intent_result["confidence"],
            retrieval_results=retrieval_results,
            reply_confidence=reply_result["confidence"],
            context=context,
        )

        return {
            "intent": {
                "name": intent_result["intent"],
                "confidence": intent_result["confidence"],
                "reason": intent_result.get("reason", ""),
            },
            "retrieval": {
                "results": retrieval_results,
            },
            "reply": reply_result["reply"],
            "reply_confidence": reply_result["confidence"],
            "grounding_used": reply_result["grounding_used"],
            "escalation": {
                "decision": esc_result["decision"],
                "reason": esc_result["reason"],
                "signals": esc_result.get("signals", []),
            },
        }


def main():
    parser = argparse.ArgumentParser(description="AI Customer Support Agent")
    parser.add_argument("--message", "-m", required=True,
                        help="Customer message to process")
    parser.add_argument("--context", "-c", nargs="*", default=None,
                        help="Prior conversation context")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    args = parser.parse_args()

    ensure_dirs()
    agent = SupportAgent()
    result = agent.handle(args.message, args.context)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"CUSTOMER: {args.message[:200]}")
        print(f"{'='*60}")
        print(f"\nINTENT: {result['intent']['name']} "
              f"(confidence: {result['intent']['confidence']:.2f})")
        print(f"REASON: {result['intent']['reason']}")
        print(f"\nRETRIEVAL: {len(result['retrieval']['results'])} examples found")
        for r in result['retrieval']['results'][:3]:
            print(f"  [{r['score']:.2f}] {r['historical_customer_message'][:80]}...")
        print(f"\nREPLY: {result['reply']}")
        print(f"\nESCALATION: {result['escalation']['decision']}")
        print(f"REASON: {result['escalation']['reason']}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
