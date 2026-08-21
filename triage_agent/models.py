"""Core data structures shared by every part of the agent.

Keeping these in one small file (instead of scattering dicts around) means
there's exactly one place that defines "what a category is" or "what a
triaged ticket looks like". Everything else imports from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Category(str, Enum):
    """The support categories the agent knows how to route.

    A closed set on purpose. An open-ended "let the model invent a label"
    approach reads as flexible but is actually a liability for a routing
    system: downstream teams, dashboards, and SLAs all assume a fixed,
    known set of buckets. If a genuinely new category shows up often, it
    gets added here deliberately -- not invented per-ticket by the model.
    """

    BILLING = "billing"
    TECHNICAL_ISSUE = "technical_issue"
    ACCOUNT_ACCESS = "account_access"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    SECURITY = "security"
    COMPLAINT = "complaint"
    GENERAL_INQUIRY = "general_inquiry"


class Urgency(str, Enum):
    """Ordered urgency levels. Order matters for the routing/escalation logic."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return [Urgency.LOW, Urgency.MEDIUM, Urgency.HIGH, Urgency.CRITICAL].index(self)


@dataclass
class Ticket:
    """A raw, unprocessed support ticket."""

    id: str
    subject: str
    body: str
    customer_email: Optional[str] = None
    submitted_at: Optional[str] = None

    @property
    def full_text(self) -> str:
        """Subject + body concatenated, used as the single input the classifiers score."""
        return f"{self.subject}\n{self.body}"


@dataclass
class TriageResult:
    """The agent's decision for a single ticket, plus the reasoning behind it."""

    ticket_id: str
    subject: str
    category: Category
    urgency: Urgency
    confidence: float  # 0.0 - 1.0
    assigned_team: str
    needs_human_review: bool
    review_reasons: list[str] = field(default_factory=list)
    reasoning: str = ""
    method: str = "heuristic"  # "llm" or "heuristic" -- which classifier produced this

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["urgency"] = self.urgency.value
        d["confidence"] = round(self.confidence, 2)
        return d
