"""AI Support Ticket Triage Agent.

A small, explainable agent that reads a support ticket and decides:
  - what category it belongs to
  - how urgent it is
  - how confident the agent is in that call
  - which team should own it
  - whether a human should double-check it before it's routed

See README.md for the design rationale.
"""

from .models import Category, Urgency, Ticket, TriageResult

__all__ = ["Category", "Urgency", "Ticket", "TriageResult"]
