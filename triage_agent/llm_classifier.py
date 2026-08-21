"""LLM-backed classifier.

This is the "smart" path: it hands the ticket to Claude and asks for a
structured classification. It's optional -- the agent works fully offline
without it (see heuristic_classifier.py) -- but it handles nuance the
keyword table can't, e.g. sarcasm, mixed-topic tickets, or phrasing that
doesn't match any fixed keyword list.

Design choice worth calling out in an interview: rather than asking the
model to "reply in JSON" and hoping it doesn't wrap the answer in prose or
markdown fences, this forces the response through a tool call with a
strict JSON schema (Anthropic's tool-use / function-calling feature). The
SDK guarantees the tool input matches the schema, so there's no fragile
string-parsing step and no "the model added a sentence before the JSON"
failure mode.

If ANTHROPIC_API_KEY isn't set, or the call fails for any reason (network,
rate limit, malformed response), this raises LLMUnavailableError and the
orchestrator (agent.py) transparently falls back to the heuristic
classifier. The batch never stops because one classifier is unavailable.
"""

from __future__ import annotations

import os

from .models import Category, Urgency

MODEL = "claude-sonnet-4-6"

TRIAGE_TOOL = {
    "name": "submit_triage",
    "description": "Submit the triage classification for a single support ticket.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [c.value for c in Category],
                "description": "The single best-fitting support category.",
            },
            "urgency": {
                "type": "string",
                "enum": [u.value for u in Urgency],
                "description": "How urgently this ticket needs a response.",
            },
            "confidence": {
                "type": "number",
                "description": "Your confidence in the category call, from 0.0 (a guess) to 1.0 (unambiguous).",
            },
            "reasoning": {
                "type": "string",
                "description": "One or two sentences on why, citing specific phrases from the ticket.",
            },
        },
        "required": ["category", "urgency", "confidence", "reasoning"],
    },
}

SYSTEM_PROMPT = """You are a support ticket triage classifier for a software company.

Read the ticket and call submit_triage with your classification.

Category guide:
- billing: payments, invoices, refunds, subscriptions, pricing
- technical_issue: integrations, API/webhook problems, performance, setup
- account_access: login, password, MFA, locked-out issues
- bug_report: something in the product is broken or erroring
- feature_request: the customer wants new or changed functionality
- security: suspected unauthorized access, breaches, fraud
- complaint: dissatisfaction with service/experience, not a specific technical problem
- general_inquiry: questions that don't fit the above

Urgency guide:
- critical: outage, security breach, data loss, or explicit "urgent/emergency" language affecting the customer's ability to operate
- high: actively blocking the customer's work, or an important deadline
- medium: a real problem but not blocking
- low: questions, minor requests, no time pressure

Be conservative with confidence: use confidence below 0.6 whenever the ticket is
short, ambiguous, or plausibly fits more than one category. Do not inflate
confidence to seem decisive -- a well-calibrated low-confidence call is more
useful downstream than a falsely confident wrong one, because it determines
whether a human reviews the ticket before it's routed."""


class LLMUnavailableError(RuntimeError):
    """Raised whenever the LLM classifier can't produce a result and the
    caller should fall back to the heuristic classifier instead."""


def classify_with_llm(subject: str, body: str) -> dict:
    """Classify one ticket via the Claude API. Returns a dict matching
    TRIAGE_TOOL's schema. Raises LLMUnavailableError on any failure."""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMUnavailableError("ANTHROPIC_API_KEY is not set")

    try:
        import anthropic
    except ImportError as e:
        raise LLMUnavailableError("anthropic package is not installed") from e

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "submit_triage"},
            messages=[
                {
                    "role": "user",
                    "content": f"Subject: {subject}\n\nBody: {body}",
                }
            ],
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_triage":
                result = dict(block.input)
                # Basic sanity checks -- never trust external output blindly,
                # even schema-constrained output, without a final guard.
                result["category"] = Category(result["category"])
                result["urgency"] = Urgency(result["urgency"])
                result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
                return result
        raise LLMUnavailableError("Model did not call submit_triage")
    except LLMUnavailableError:
        raise
    except Exception as e:  # network errors, rate limits, malformed enums, etc.
        raise LLMUnavailableError(f"LLM classification failed: {e}") from e
