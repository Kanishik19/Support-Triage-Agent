"""Lightweight sanity tests for the heuristic path (the offline-safe core).

Deliberately not pytest-based -- `python test_agent.py` with plain asserts
is enough for a 24-hour project and doesn't add a test-framework dependency
for something this small. Run: python test_agent.py
"""

from triage_agent.agent import TriageAgent
from triage_agent.models import Ticket, Category, Urgency

agent = TriageAgent(use_llm=False)  # force the deterministic path for repeatable tests


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    assert condition, name


def test_billing_ticket_routes_to_billing():
    t = Ticket(id="X1", subject="Refund request", body="I was charged twice on my invoice, please refund.")
    r = agent.triage(t)
    check("billing keywords -> billing category", r.category == Category.BILLING)
    check("billing routes to Billing & Payments", r.assigned_team == "Billing & Payments")


def test_critical_language_sets_critical_urgency_and_forces_review():
    t = Ticket(id="X2", subject="URGENT", body="Production is down, entire team is blocked, we are losing money.")
    r = agent.triage(t)
    check("explicit critical language -> CRITICAL", r.urgency == Urgency.CRITICAL)
    check("critical urgency always flagged for review", r.needs_human_review is True)
    check("critical tickets CC security", "Security" in r.assigned_team)


def test_security_ticket_always_flagged_regardless_of_confidence():
    t = Ticket(id="X3", subject="Account compromised", body="Someone else logged into my account, this looks like unauthorized access and a data breach.")
    r = agent.triage(t)
    check("security keywords -> SECURITY category", r.category == Category.SECURITY)
    check("security tickets always held for human review", r.needs_human_review is True)


def test_vague_short_ticket_gets_low_confidence_and_review():
    t = Ticket(id="X4", subject="invoice", body="where is it")
    r = agent.triage(t)
    check("thin ticket -> low-ish confidence", r.confidence < 0.85)


def test_feature_request_routes_to_product_and_defaults_low_urgency():
    t = Ticket(id="X5", subject="Feature idea", body="Would be nice if you could add dark mode. No rush, just a suggestion.")
    r = agent.triage(t)
    check("feature request -> FEATURE_REQUEST category", r.category == Category.FEATURE_REQUEST)
    check("feature request -> routes to Product Team", r.assigned_team == "Product Team")
    check("explicit 'no rush' -> LOW urgency", r.urgency == Urgency.LOW)


def test_batch_processing_returns_stats_for_every_ticket():
    tickets = [
        Ticket(id="B1", subject="Refund", body="Please refund my invoice."),
        Ticket(id="B2", subject="Bug", body="The export button throws an error and crashes."),
    ]
    results, stats = agent.triage_batch(tickets)
    check("batch returns one result per ticket", len(results) == 2)
    check("batch stats total matches input size", stats.total == 2)
    check("batch stats sum to total across categories", sum(stats.by_category.values()) == 2)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"\n{len(tests)} tests passed.")
