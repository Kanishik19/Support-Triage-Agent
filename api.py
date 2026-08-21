"""Flask API for the AI Support Ticket Triage Agent.

This is a thin HTTP wrapper around the existing triage_agent package --
it does not duplicate any classification logic. The frontend calls these
endpoints, which call TriageAgent, which is the exact same code the CLI
(main.py) uses. One source of truth for the agent's behavior.

Run:
    pip install -r requirements.txt
    python api.py

Then the API is live at http://localhost:5000
"""

from __future__ import annotations

import json
import os

from flask import Flask, jsonify, request

from triage_agent.agent import TriageAgent
from triage_agent.models import Ticket

app = Flask(__name__)

# Manual CORS instead of the flask-cors package -- one less dependency for
# a two-endpoint API. In production, replace "*" with your actual frontend
# origin (e.g. "https://your-frontend-domain.com").
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/<path:_path>", methods=["OPTIONS"])
def cors_preflight(_path):
    return "", 204

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_tickets.json")

# One shared heuristic agent instance (stateless, safe to reuse across requests).
# The LLM agent is created per-request only when explicitly asked for, since it
# depends on an API key that may or may not be configured.
_heuristic_agent = TriageAgent(use_llm=False)


def get_agent(use_llm: bool) -> TriageAgent:
    return TriageAgent(use_llm=True) if use_llm else _heuristic_agent


def ticket_from_json(data: dict, fallback_id: str) -> Ticket:
    return Ticket(
        id=str(data.get("id") or fallback_id),
        subject=(data.get("subject") or "").strip(),
        body=(data.get("body") or "").strip(),
        customer_email=data.get("customer_email"),
        submitted_at=data.get("submitted_at"),
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/tickets/sample")
def sample_tickets():
    """Returns the bundled sample tickets, for the frontend's demo queue."""
    try:
        with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": f"Sample tickets file not found at {SAMPLE_PATH}"}), 500


@app.post("/api/triage")
def triage_one():
    """Triage a single ticket. Body: {subject, body, use_llm?}"""
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()

    if not subject and not body:
        return jsonify({"error": "Provide at least a subject or a body."}), 400

    ticket = ticket_from_json({**data, "subject": subject or "(no subject)", "body": body}, "LIVE-1")
    agent = get_agent(bool(data.get("use_llm", False)))
    result = agent.triage(ticket)
    return jsonify(result.to_dict())


@app.post("/api/triage/batch")
def triage_batch():
    """Triage a batch of tickets. Body: {tickets: [{id, subject, body}, ...], use_llm?}"""
    data = request.get_json(silent=True) or {}
    tickets_in = data.get("tickets")

    if not isinstance(tickets_in, list) or not tickets_in:
        return jsonify({"error": "Provide a non-empty 'tickets' array."}), 400

    tickets = [ticket_from_json(t, f"T-{i+1}") for i, t in enumerate(tickets_in)]
    agent = get_agent(bool(data.get("use_llm", False)))
    results, stats = agent.triage_batch(tickets)

    return jsonify({
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
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
