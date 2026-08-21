"""Routing and human-review rules.

Kept separate from the classifiers on purpose: classification ("what is
this ticket?") and routing ("given what it is, who handles it and does a
human need to look first?") are different decisions with different owners
in a real company -- support ops would tune this file constantly without
ever touching the classifier. Separating them means that tuning is a
one-file, low-risk change.
"""

from __future__ import annotations

from .models import Category, Urgency, TriageResult

# Every category has a home team. This is the "default" routing table.
TEAM_ROUTING: dict[Category, str] = {
    Category.BILLING: "Billing & Payments",
    Category.TECHNICAL_ISSUE: "Technical Support",
    Category.ACCOUNT_ACCESS: "Account Support",
    Category.BUG_REPORT: "Engineering",
    Category.FEATURE_REQUEST: "Product Team",
    Category.SECURITY: "Security / Trust & Safety",
    Category.COMPLAINT: "Customer Success",
    Category.GENERAL_INQUIRY: "General Support",
}

# Below this confidence, a human should confirm the routing before it goes out.
CONFIDENCE_REVIEW_THRESHOLD = 0.6


def assign_team(category: Category, urgency: Urgency) -> str:
    """Decide which team owns the ticket.

    Almost always just the category's home team. The one override:
    CRITICAL tickets always go through Security/Trust & Safety triage
    first regardless of category, because a mislabeled critical issue
    (e.g. a security incident logged as a "bug report") is far more
    costly than a Security team briefly looking at a ticket that turns
    out not to be theirs.
    """
    if urgency == Urgency.CRITICAL and category != Category.SECURITY:
        return f"{TEAM_ROUTING[category]} (CC: Security — critical severity)"
    return TEAM_ROUTING[category]


def needs_human_review(
    category: Category,
    urgency: Urgency,
    confidence: float,
) -> list[str]:
    """Return the list of reasons a ticket should be held for human review
    before it's auto-routed. An empty list means it's safe to auto-route.

    Three independent triggers, each defensible on its own:
      1. Low confidence -- the agent itself isn't sure. This is the main
         signal and covers most ambiguous/mixed-topic tickets.
      2. Security category -- even a confident security call is high
         stakes enough that a human should be in the loop before anything
         is closed or auto-responded to.
      3. Critical urgency -- same logic: the cost of a wrong auto-routing
         decision scales with urgency, so the review bar gets lower as
         urgency gets higher, on purpose.
    """
    reasons = []
    if confidence < CONFIDENCE_REVIEW_THRESHOLD:
        reasons.append(f"Low classification confidence ({confidence:.2f} < {CONFIDENCE_REVIEW_THRESHOLD})")
    if category == Category.SECURITY:
        reasons.append("Security-related tickets always get human confirmation")
    if urgency == Urgency.CRITICAL:
        reasons.append("Critical-urgency tickets always get human confirmation")
    return reasons


def route(
    ticket_id: str,
    subject: str,
    category: Category,
    urgency: Urgency,
    confidence: float,
    reasoning: str,
    method: str,
) -> TriageResult:
    """Combine a classification into a final, routable TriageResult."""
    review_reasons = needs_human_review(category, urgency, confidence)
    return TriageResult(
        ticket_id=ticket_id,
        subject=subject,
        category=category,
        urgency=urgency,
        confidence=confidence,
        assigned_team=assign_team(category, urgency),
        needs_human_review=bool(review_reasons),
        review_reasons=review_reasons,
        reasoning=reasoning,
        method=method,
    )
