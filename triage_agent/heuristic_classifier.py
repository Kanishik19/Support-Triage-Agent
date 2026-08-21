"""Deterministic keyword-scoring classifier.

Why this exists alongside an LLM classifier (see llm_classifier.py):

  1. Reliability. This has zero external dependencies and zero network
     calls, so it always works -- no API key, no rate limit, no outage.
     It's the fallback the LLM classifier drops into if anything goes
     wrong, and it's what the demo runs on by default.
  2. Explainability. Every score traces back to specific matched words.
     That's easy to defend in an interview ("why did it say HIGH
     urgency?" -> "because the message contained 'production is down'").
     An LLM's internal reasoning is comparatively opaque.
  3. Baseline. It gives the LLM classifier something concrete to beat,
     and something to compare against when sanity-checking LLM output.

It is intentionally simple: weighted keyword/phrase matching per category
and per urgency level, normalized into a 0-1 confidence score. No ML
libraries, no training step -- just a table of signal words a human can
read top to bottom in thirty seconds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Category, Urgency

# --------------------------------------------------------------------------
# Signal tables. Each category/urgency maps to phrases that are evidence for
# it. Longer, more specific phrases are checked first so "cannot log in"
# doesn't just get partial-credited as a generic "login" hit.
# --------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.BILLING: [
        "invoice", "charged twice", "double charged", "refund", "billing",
        "subscription", "payment failed", "credit card", "overcharged",
        "receipt", "renew", "pricing", "plan upgrade", "downgrade", "charge",
        "billed", "autopay", "proration",
    ],
    Category.SECURITY: [
        "unauthorized access", "hacked", "suspicious login", "data breach",
        "phishing", "someone else logged in", "compromised", "leaked",
        "suspicious activity", "2fa", "two-factor", "fraudulent",
        "account was accessed", "malware", "vulnerability",
    ],
    Category.ACCOUNT_ACCESS: [
        "cannot log in", "can't log in", "cannot login", "can't login",
        "locked out", "reset my password", "password reset", "forgot password",
        "two factor", "verification code", "account locked", "sign in",
        "log in", "login", "mfa", "username",
    ],
    Category.BUG_REPORT: [
        "error message", "stack trace", "crashes", "crashed", "not working",
        "broken", "bug", "exception", "500 error", "404", "fails to load",
        "freezes", "throws an error", "doesn't work", "regression",
    ],
    Category.TECHNICAL_ISSUE: [
        "integration", "api", "webhook", "sync issue", "not syncing",
        "slow performance", "timeout", "configuration", "setup help",
        "connect", "server", "latency", "outage", "downtime", "down",
    ],
    Category.FEATURE_REQUEST: [
        "feature request", "would be nice", "could you add", "please add",
        "suggestion", "it would be great if", "wish list", "enhancement",
        "request a feature", "roadmap", "any plans to add",
    ],
    Category.COMPLAINT: [
        "unacceptable", "very disappointed", "terrible experience", "worst",
        "frustrated", "unhappy", "poor service", "complaint", "ridiculous",
        "fed up", "angry", "furious", "cancel my account", "cancelling",
        "switching to a competitor",
    ],
    Category.GENERAL_INQUIRY: [
        "just wondering", "quick question", "how do i", "how does",
        "wanted to ask", "curious about", "documentation", "question about",
        "clarify", "what is the difference",
    ],
}

URGENCY_KEYWORDS: dict[Urgency, list[str]] = {
    Urgency.CRITICAL: [
        "production is down", "entire team is blocked", "losing money",
        "data loss", "security breach", "cannot access any", "complete outage",
        "all users affected", "revenue impact", "urgent", "asap", "emergency",
        "escalate immediately", "immediately",
    ],
    Urgency.HIGH: [
        "blocking", "blocked", "can't work", "cannot work", "deadline",
        "high priority", "important client", "escalate", "not able to use",
        "affecting multiple users", "today",
    ],
    Urgency.MEDIUM: [
        "soon", "this week", "annoying", "keeps happening", "several times",
        "intermittent", "workaround",
    ],
    Urgency.LOW: [
        "whenever you get a chance", "no rush", "not urgent", "just curious",
        "low priority", "someday", "eventually",
    ],
}

# Category-level default urgency when no explicit urgency language is present.
# e.g. a security ticket defaults to more urgent than a feature request.
CATEGORY_BASE_URGENCY: dict[Category, Urgency] = {
    Category.SECURITY: Urgency.HIGH,
    Category.BUG_REPORT: Urgency.MEDIUM,
    Category.TECHNICAL_ISSUE: Urgency.MEDIUM,
    Category.ACCOUNT_ACCESS: Urgency.MEDIUM,
    Category.BILLING: Urgency.MEDIUM,
    Category.COMPLAINT: Urgency.MEDIUM,
    Category.FEATURE_REQUEST: Urgency.LOW,
    Category.GENERAL_INQUIRY: Urgency.LOW,
}


@dataclass
class HeuristicScore:
    category: Category
    category_confidence: float
    urgency: Urgency
    urgency_confidence: float
    matched_category_phrases: list[str]
    matched_urgency_phrases: list[str]


def _matches(text: str, phrases: list[str]) -> list[str]:
    """Return which phrases from the list appear in text (simple substring match)."""
    return [p for p in phrases if p in text]


def score_ticket(text: str) -> HeuristicScore:
    """Score a ticket's raw text against every category and urgency table.

    Category confidence = (matches for the winning category) / (total matches
    across all categories), so a ticket that only hits billing words gets a
    near-1.0 score, while one with a couple of scattered billing AND bug
    words gets a lower, more honest score -- which is exactly the signal we
    want to trigger human review.
    """
    text = text.lower()

    category_hits = {
        cat: _matches(text, phrases) for cat, phrases in CATEGORY_KEYWORDS.items()
    }
    total_hits = sum(len(v) for v in category_hits.values())

    if total_hits == 0:
        best_category = Category.GENERAL_INQUIRY
        category_confidence = 0.35  # no signal at all -> low confidence, not zero
        matched_category_phrases: list[str] = []
    else:
        best_category = max(category_hits, key=lambda c: len(category_hits[c]))
        matched_category_phrases = category_hits[best_category]
        category_confidence = len(matched_category_phrases) / total_hits
        # A single weak match shouldn't look as confident as five matches.
        # Blend the "share of total signal" with an absolute-count bonus.
        strength_bonus = min(len(matched_category_phrases) / 3, 1.0) * 0.25
        category_confidence = min(0.99, category_confidence * 0.75 + strength_bonus)

    urgency_hits = {
        u: _matches(text, phrases) for u, phrases in URGENCY_KEYWORDS.items()
    }
    explicit_urgency = max(urgency_hits, key=lambda u: len(urgency_hits[u]))
    matched_urgency_phrases = urgency_hits[explicit_urgency]

    if matched_urgency_phrases:
        urgency = explicit_urgency
        urgency_confidence = min(0.95, 0.55 + 0.15 * len(matched_urgency_phrases))
    else:
        # Fall back to the category's typical urgency -- lower confidence
        # because we're inferring, not reading it directly off the text.
        urgency = CATEGORY_BASE_URGENCY.get(best_category, Urgency.LOW)
        urgency_confidence = 0.65

    return HeuristicScore(
        category=best_category,
        category_confidence=round(category_confidence, 3),
        urgency=urgency,
        urgency_confidence=round(urgency_confidence, 3),
        matched_category_phrases=matched_category_phrases,
        matched_urgency_phrases=matched_urgency_phrases,
    )


def explain(score: HeuristicScore) -> str:
    """Turn a HeuristicScore into a one-line human-readable reason."""
    cat_evidence = ", ".join(f"'{p}'" for p in score.matched_category_phrases[:3]) or "no strong keyword match"
    urg_evidence = ", ".join(f"'{p}'" for p in score.matched_urgency_phrases[:3]) or f"defaulted from category ({score.category.value})"
    return (
        f"Categorized as {score.category.value} on: {cat_evidence}. "
        f"Urgency {score.urgency.value} on: {urg_evidence}."
    )
