"""Renders triage results as a single self-contained HTML file.

No build step, no JS framework -- one .html file with inline CSS and a
small vanilla-JS filter, because that's all a triage queue view needs.
Kept separate from main.py so the "produce a decision" logic and the
"display the decision" logic don't get tangled together.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

URGENCY_META = {
    "critical": {"color": "#C4302B", "bg": "#FBEAE8", "label": "Critical"},
    "high":     {"color": "#B5680A", "bg": "#FBF1E2", "label": "High"},
    "medium":   {"color": "#2A56A8", "bg": "#EAF0FB", "label": "Medium"},
    "low":      {"color": "#5B6472", "bg": "#EEF0F3", "label": "Low"},
}

CATEGORY_LABELS = {
    "billing": "Billing",
    "technical_issue": "Technical Issue",
    "account_access": "Account Access",
    "bug_report": "Bug Report",
    "feature_request": "Feature Request",
    "security": "Security",
    "complaint": "Complaint",
    "general_inquiry": "General Inquiry",
}

URGENCY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _card(r: dict) -> str:
    um = URGENCY_META[r["urgency"]]
    conf_pct = round(r["confidence"] * 100)
    review_banner = ""
    if r["needs_human_review"]:
        reasons = "".join(f"<li>{html.escape(x)}</li>" for x in r["review_reasons"])
        review_banner = f"""
        <div class="review-banner">
          <span class="review-dot"></span>
          <div>
            <div class="review-title">Held for human review</div>
            <ul class="review-reasons">{reasons}</ul>
          </div>
        </div>"""

    return f"""
    <article class="card" data-urgency="{r['urgency']}" style="--u-color:{um['color']};--u-bg:{um['bg']};">
      <div class="card-rail"></div>
      <div class="card-body">
        <div class="card-top">
          <span class="ticket-id">{html.escape(r['ticket_id'])}</span>
          <span class="badge urgency-badge">{um['label']}</span>
          <span class="badge category-badge">{CATEGORY_LABELS.get(r['category'], r['category'])}</span>
          <span class="method-tag">{r['method']}</span>
        </div>
        <h3 class="subject">{html.escape(r['subject'])}</h3>
        <p class="reasoning">{html.escape(r['reasoning'])}</p>
        <div class="meta-row">
          <div class="team">→ <strong>{html.escape(r['assigned_team'])}</strong></div>
          <div class="confidence">
            <span class="confidence-label">confidence {conf_pct}%</span>
            <div class="confidence-track"><div class="confidence-fill" style="width:{conf_pct}%;"></div></div>
          </div>
        </div>
        {review_banner}
      </div>
    </article>"""


def _stat(label: str, value) -> str:
    return f'<div class="stat"><div class="stat-value">{value}</div><div class="stat-label">{html.escape(label)}</div></div>'


def generate_report(results, stats, out_path: str) -> None:
    """results: list[TriageResult]-like (has .to_dict()); stats: BatchStats."""
    result_dicts = [r.to_dict() if hasattr(r, "to_dict") else r for r in results]
    result_dicts.sort(key=lambda r: URGENCY_ORDER[r["urgency"]])

    cards_html = "\n".join(_card(r) for r in result_dicts)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    stats_html = "".join([
        _stat("tickets triaged", stats.total),
        _stat("flagged for review", stats.flagged_for_review),
        _stat("avg confidence", f"{round(stats.avg_confidence * 100)}%"),
        _stat("processed in", f"{stats.elapsed_seconds}s"),
    ])

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ticket Triage Queue</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink: #14181F;
    --ink-soft: #4B525E;
    --paper: #EDEFF3;
    --surface: #FFFFFF;
    --line: #DBDFE6;
    --accent: #3557E8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: 'Inter', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  header {{
    padding: 40px clamp(20px, 5vw, 64px) 28px;
    border-bottom: 1px solid var(--line);
    background: var(--surface);
  }}
  .eyebrow {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 10px;
  }}
  h1 {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(28px, 4vw, 38px);
    margin: 0 0 6px;
    letter-spacing: -0.01em;
  }}
  .subtitle {{ color: var(--ink-soft); margin: 0; font-size: 15px; }}
  .stats-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 28px;
    margin-top: 26px;
  }}
  .stat-value {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 26px;
    font-weight: 600;
  }}
  .stat-label {{
    font-size: 12px;
    color: var(--ink-soft);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 2px;
  }}
  main {{
    max-width: 900px;
    margin: 0 auto;
    padding: 32px clamp(20px, 5vw, 64px) 80px;
  }}
  .filters {{
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    padding: 7px 14px;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--surface);
    color: var(--ink-soft);
    cursor: pointer;
  }}
  .filter-btn.active {{
    background: var(--ink);
    color: var(--surface);
    border-color: var(--ink);
  }}
  .card {{
    display: flex;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 10px;
    margin-bottom: 14px;
    overflow: hidden;
  }}
  .card-rail {{ width: 5px; background: var(--u-color); flex-shrink: 0; }}
  .card-body {{ padding: 18px 22px; flex: 1; min-width: 0; }}
  .card-top {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }}
  .ticket-id {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12.5px;
    color: var(--ink-soft);
    margin-right: 4px;
  }}
  .badge {{
    font-size: 11.5px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 999px;
  }}
  .urgency-badge {{ color: var(--u-color); background: var(--u-bg); }}
  .category-badge {{ color: var(--ink-soft); background: var(--paper); }}
  .method-tag {{
    margin-left: auto;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10.5px;
    color: #9AA1AC;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .subject {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 17px;
    margin: 0 0 6px;
  }}
  .reasoning {{
    font-size: 13.5px;
    color: var(--ink-soft);
    margin: 0 0 14px;
    line-height: 1.5;
  }}
  .meta-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    flex-wrap: wrap;
  }}
  .team {{ font-size: 13.5px; color: var(--ink-soft); }}
  .team strong {{ color: var(--ink); }}
  .confidence {{ display: flex; align-items: center; gap: 8px; min-width: 160px; }}
  .confidence-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--ink-soft);
    white-space: nowrap;
  }}
  .confidence-track {{
    width: 90px;
    height: 5px;
    background: var(--paper);
    border-radius: 3px;
    overflow: hidden;
  }}
  .confidence-fill {{ height: 100%; background: var(--u-color); }}
  .review-banner {{
    margin-top: 14px;
    display: flex;
    gap: 10px;
    padding: 12px 14px;
    background: #FBF1E2;
    border: 1px solid #F0DDB4;
    border-radius: 8px;
  }}
  .review-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #B5680A; margin-top: 5px; flex-shrink: 0;
  }}
  .review-title {{ font-size: 12.5px; font-weight: 600; color: #7A4C08; margin-bottom: 4px; }}
  .review-reasons {{ margin: 0; padding-left: 16px; font-size: 12.5px; color: #7A4C08; line-height: 1.5; }}
  footer {{
    text-align: center;
    font-size: 11.5px;
    color: #9AA1AC;
    font-family: 'IBM Plex Mono', monospace;
    padding-bottom: 40px;
  }}
</style>
</head>
<body>
<header>
  <p class="eyebrow">Support Ops · Automated Triage</p>
  <h1>Ticket Triage Queue</h1>
  <p class="subtitle">Generated {generated_at} · sorted by urgency</p>
  <div class="stats-row">{stats_html}</div>
</header>
<main>
  <div class="filters" id="filters">
    <button class="filter-btn active" data-filter="all">All</button>
    <button class="filter-btn" data-filter="critical">Critical</button>
    <button class="filter-btn" data-filter="high">High</button>
    <button class="filter-btn" data-filter="medium">Medium</button>
    <button class="filter-btn" data-filter="low">Low</button>
  </div>
  <div id="cards">
    {cards_html}
  </div>
</main>
<footer>AI Support Ticket Triage Agent — heuristic + LLM hybrid classifier</footer>
<script>
  document.getElementById('filters').addEventListener('click', function(e) {{
    if (!e.target.classList.contains('filter-btn')) return;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    var filter = e.target.dataset.filter;
    document.querySelectorAll('.card').forEach(function(card) {{
      card.style.display = (filter === 'all' || card.dataset.urgency === filter) ? '' : 'none';
    }});
  }});
</script>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
