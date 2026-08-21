"""The agent itself: wires the classifiers and the router together.

Public surface is deliberately small:
    agent = TriageAgent()
    result = agent.triage(ticket)
    results = agent.triage_batch(tickets)

Everything else in the package is a private implementation detail behind
that interface, which is what makes this easy to explain in an interview:
"one method in, one structured result out, per ticket."
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .models import Ticket, TriageResult
from .heuristic_classifier import score_ticket, explain
from .llm_classifier import classify_with_llm, LLMUnavailableError
from . import router


@dataclass
class BatchStats:
    total: int
    by_category: dict
    by_urgency: dict
    by_team: dict
    flagged_for_review: int
    avg_confidence: float
    llm_used: int
    heuristic_used: int
    elapsed_seconds: float


class TriageAgent:
    def __init__(self, use_llm: bool = True):
        """use_llm=True means 'try the LLM classifier first, per ticket,
        and fall back to the heuristic classifier if it's unavailable.'
        Set use_llm=False to force the fully offline, deterministic path
        (useful for tests, demos without an API key, or CI)."""
        self.use_llm = use_llm

    def triage(self, ticket: Ticket) -> TriageResult:
        if self.use_llm:
            try:
                llm_result = classify_with_llm(ticket.subject, ticket.body)
                return router.route(
                    ticket_id=ticket.id,
                    subject=ticket.subject,
                    category=llm_result["category"],
                    urgency=llm_result["urgency"],
                    confidence=llm_result["confidence"],
                    reasoning=llm_result["reasoning"],
                    method="llm",
                )
            except LLMUnavailableError:
                pass  # fall through to heuristic path below

        score = score_ticket(ticket.full_text)
        return router.route(
            ticket_id=ticket.id,
            subject=ticket.subject,
            category=score.category,
            urgency=score.urgency,
            # a ticket's overall confidence is bounded by whichever of the
            # two calls (category, urgency) the agent is less sure about
            # Weighted rather than a flat min: category is the primary call
            # and usually has richer signal; urgency is often inferred from
            # the category when no explicit urgency language is present, so
            # it shouldn't single-handedly drag every ticket into review.
            confidence=round(0.7 * score.category_confidence + 0.3 * score.urgency_confidence, 3),
            reasoning=explain(score),
            method="heuristic",
        )

    def triage_batch(self, tickets: list[Ticket]) -> tuple[list[TriageResult], BatchStats]:
        start = time.perf_counter()
        results = [self.triage(t) for t in tickets]
        elapsed = time.perf_counter() - start

        by_category, by_urgency, by_team = {}, {}, {}
        flagged, llm_used, heuristic_used = 0, 0, 0
        for r in results:
            by_category[r.category.value] = by_category.get(r.category.value, 0) + 1
            by_urgency[r.urgency.value] = by_urgency.get(r.urgency.value, 0) + 1
            by_team[r.assigned_team] = by_team.get(r.assigned_team, 0) + 1
            if r.needs_human_review:
                flagged += 1
            if r.method == "llm":
                llm_used += 1
            else:
                heuristic_used += 1

        avg_conf = sum(r.confidence for r in results) / len(results) if results else 0.0

        stats = BatchStats(
            total=len(results),
            by_category=by_category,
            by_urgency=by_urgency,
            by_team=by_team,
            flagged_for_review=flagged,
            avg_confidence=round(avg_conf, 3),
            llm_used=llm_used,
            heuristic_used=heuristic_used,
            elapsed_seconds=round(elapsed, 3),
        )
        return results, stats
