#!/usr/bin/env python3
"""CLI for the AI Support Ticket Triage Agent.

Usage:
    python main.py                                   # runs sample_tickets.json, heuristic mode
    python main.py --input data/sample_tickets.json   # explicit input file
    python main.py --llm                              # try Claude first, fall back to heuristic
    python main.py --output output/results.json       # where to write results
    python main.py --report                           # also generate an HTML report

Exit code is 0 on success, 1 on a fatal error (bad input file, etc).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from triage_agent.agent import TriageAgent
from triage_agent.models import Ticket

DEFAULT_INPUT = "data/sample_tickets.json"
DEFAULT_OUTPUT = "output/results.json"

URGENCY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def load_tickets(path: str) -> list[Ticket]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [
        Ticket(
            id=item["id"],
            subject=item["subject"],
            body=item["body"],
            customer_email=item.get("customer_email"),
            submitted_at=item.get("submitted_at"),
        )
        for item in raw
    ]


def print_summary(results, stats) -> None:
    print(f"\nTriaged {stats.total} tickets in {stats.elapsed_seconds}s "
          f"({stats.llm_used} via LLM, {stats.heuristic_used} via heuristic fallback)\n")

    header = f"{'ID':<8} {'CATEGORY':<18} {'URGENCY':<10} {'CONF':<6} {'TEAM':<32} {'REVIEW?'}"
    print(header)
    print("-" * len(header))
    for r in sorted(results, key=lambda r: URGENCY_ORDER[r.urgency.value]):
        flag = "⚠ YES" if r.needs_human_review else ""
        print(f"{r.ticket_id:<8} {r.category.value:<18} {r.urgency.value:<10} "
              f"{r.confidence:<6.2f} {r.assigned_team:<32} {flag}")

    print("\nBy category:", stats.by_category)
    print("By urgency: ", stats.by_urgency)
    print("By team:    ", stats.by_team)
    print(f"\nFlagged for human review: {stats.flagged_for_review}/{stats.total}")
    print(f"Average confidence:       {stats.avg_confidence}")


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Support Ticket Triage Agent")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to tickets JSON file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Path to write results JSON")
    parser.add_argument("--llm", action="store_true",
                         help="Try the Claude classifier first (needs ANTHROPIC_API_KEY), "
                              "falling back to the heuristic classifier per-ticket on failure")
    parser.add_argument("--report", action="store_true",
                         help="Also generate an HTML report next to the output file")
    args = parser.parse_args()

    try:
        tickets = load_tickets(args.input)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Failed to load tickets from {args.input}: {e}", file=sys.stderr)
        return 1

    agent = TriageAgent(use_llm=args.llm)
    results, stats = agent.triage_batch(tickets)

    print_summary(results, stats)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "results": [r.to_dict() for r in results],
                "stats": {
                    "total": stats.total,
                    "by_category": stats.by_category,
                    "by_urgency": stats.by_urgency,
                    "by_team": stats.by_team,
                    "flagged_for_review": stats.flagged_for_review,
                    "avg_confidence": stats.avg_confidence,
                    "llm_used": stats.llm_used,
                    "heuristic_used": stats.heuristic_used,
                    "elapsed_seconds": stats.elapsed_seconds,
                },
            },
            f,
            indent=2,
        )
    print(f"\nWrote results to {out_path}")

    if args.report:
        from generate_report import generate_report
        report_path = out_path.with_suffix(".html")
        generate_report(results, stats, str(report_path))
        print(f"Wrote HTML report to {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
