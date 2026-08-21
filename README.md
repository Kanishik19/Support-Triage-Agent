# AI Support Ticket Triage Agent

A small agent that reads incoming support tickets and decides, for each one:
**what it's about, how urgent it is, how confident the agent is, who should
own it, and whether a human needs to check it first.**

Built for a 24-hour AI agent challenge. Optimized for *correctness →
reliability → explainability → usability → polish*, in that order.

---

## Quick start

```bash
# No install needed for the default (heuristic) path -- stdlib only.
python main.py --report

# Prints a summary table to the terminal, writes:
#   output/results.json   (structured results, one object per ticket)
#   output/results.html   (visual triage queue, open it in a browser)
```

Optional: run the sanity tests (`python test_agent.py`), or point at your
own ticket file with `--input path/to/tickets.json` (same shape as
`data/sample_tickets.json`).

### Web app (API + React UI)

There's also a small full-stack version: `api.py` exposes the exact same
`TriageAgent` over HTTP, and `frontend/` is a React app that calls it.

```bash
# Terminal 1 — backend
pip install -r requirements.txt
python api.py                      # http://localhost:5000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

See `frontend/README.md` for details. The API is a thin wrapper — it
imports and calls `TriageAgent` directly, so the web app and the CLI are
guaranteed to behave identically; there's no duplicated logic to drift
out of sync.

### Optional LLM mode

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python main.py --llm --report
```

With `--llm`, each ticket is classified by Claude first; if that call fails
for *any* reason (no key, network, rate limit), that one ticket silently
falls back to the heuristic classifier and the batch keeps going. Without
`--llm`, the agent never touches the network at all.

---

## Architecture

```
data/sample_tickets.json  →  main.py  →  TriageAgent.triage_batch()
                                              │
                              per ticket:     ▼
                         ┌─────────────────────────────────┐
                         │ 1. Try LLM classifier (optional) │
                         │    ↳ falls back on any failure   │
                         │ 2. Heuristic classifier (default)│
                         └────────────────┬──────────────────┘
                                          ▼
                                    router.route()
                              (team assignment +
                               human-review check)
                                          ▼
                                   TriageResult
                                          │
                         ┌────────────────┴────────────────┐
                         ▼                                  ▼
                 output/results.json               output/results.html
```

Six small files, each with one job:

| File | Responsibility |
|---|---|
| `triage_agent/models.py` | `Ticket`, `TriageResult`, `Category`, `Urgency` — the shared vocabulary |
| `triage_agent/heuristic_classifier.py` | Deterministic keyword-scoring classifier (the reliable core) |
| `triage_agent/llm_classifier.py` | Optional Claude-backed classifier (forced structured output) |
| `triage_agent/router.py` | Category → team mapping, and the human-review rules |
| `triage_agent/agent.py` | Orchestrates classifier(s) + router, handles batches |
| `main.py` / `generate_report.py` | CLI, JSON output, HTML report |
| `api.py` | Flask API — HTTP wrapper around `TriageAgent`, no separate logic |
| `frontend/` | React UI that calls `api.py` (see `frontend/README.md`) |

No framework, no database, no queue, no vector store. A ticket goes in, a
decision comes out. That's the whole system, which is also why it's easy
to explain end-to-end in an interview.

---

## Why a hybrid classifier instead of "just call an LLM"

The obvious approach is: send the ticket to an LLM, ask for JSON, done.
I built that (`llm_classifier.py`), but I didn't want the *whole system*
to depend on an API key, network access, and a model's mood on a given
day — especially for something billed as reliable infrastructure. So the
agent has two classifiers behind one interface:

- **Heuristic classifier** (`heuristic_classifier.py`) — keyword/phrase
  tables per category and urgency level, scored by match strength. Zero
  dependencies, zero network calls, fully deterministic, and every score
  traces back to specific matched words, which makes it trivial to debug
  and explain ("why did it say billing?" → "it matched 'refund',
  'invoice', 'charged twice'"). This is what the demo runs on by default.
- **LLM classifier** (`llm_classifier.py`) — used when `--llm` is passed
  and an API key is available. Handles nuance the keyword table can't
  (sarcasm, mixed-topic tickets, phrasing outside the keyword list).

`TriageAgent.triage()` tries the LLM first (if enabled) and **falls back
to the heuristic classifier per-ticket** on any failure, so one bad API
call never kills a batch. This is the main design decision I'd defend in
an interview: reliability comes from the fallback chain, not from picking
"the best" classifier.

### Forced structured output, not parsed prose

The LLM classifier doesn't ask Claude to "reply in JSON" and hope for the
best. It uses Anthropic's tool-use feature with `tool_choice` forcing a
call to a `submit_triage` tool with a strict JSON schema (see
`TRIAGE_TOOL` in `llm_classifier.py`). The SDK guarantees the shape of the
response, so there's no regex-scraping a maybe-JSON-maybe-not string out
of free text — a small choice, but it removes an entire class of flaky
parsing bugs.

---

## Scoring logic (heuristic path)

1. **Category**: every category has a list of signal phrases (`invoice`,
   `refund`, `charged twice` for billing; `cannot log in`, `password
   reset` for account access; etc). The ticket text is matched against all
   lists at once. The category with the most matches wins.
   `category_confidence` = (that category's matches) / (total matches
   across all categories), blended with a small bonus for absolute match
   count — one lonely keyword scores lower than five clear ones, even if
   nothing else in the ticket matched anything.

2. **Urgency**: same idea, but with its own keyword tables (`production is
   down`, `losing money` → critical; `blocking`, `deadline` → high; `no
   rush`, `whenever you get a chance` → low). If the ticket contains
   explicit urgency language, that wins directly. If it doesn't, urgency
   is inferred from the category's typical urgency (e.g. security defaults
   to high, feature requests default to low) — with a lower confidence,
   since it's an inference rather than something read off the text.

3. **Overall confidence** = `0.7 × category_confidence + 0.3 ×
   urgency_confidence`. Category is weighted higher because it's usually
   read directly from richer signal in the text; urgency is often inferred
   from the category default, so it shouldn't single-handedly drag every
   well-categorized ticket into "needs review" just because the customer
   didn't use an urgency word.

This is intentionally *not* ML — no training data, no model file, nothing
to version or retrain. For a fixed, well-understood label set like this
one, a readable keyword table is a legitimate production pattern (plenty
of real triage/spam/routing systems still ship one as a fast, explainable
first pass in front of a model), and it's the right scope for 24 hours.

---

## Routing logic

- Every category has a **home team** (`TEAM_ROUTING` in `router.py`) —
  e.g. billing → Billing & Payments, bug reports → Engineering.
- **One override**: any `CRITICAL`-urgency ticket gets CC'd to
  Security/Trust & Safety regardless of category, because a mislabeled
  critical issue (a security incident filed as a "bug report") is far
  costlier than Security briefly looking at a ticket that isn't theirs.

## Human-review logic

A ticket is held for human review if **any** of these is true:

1. `confidence < 0.6` — the agent itself wasn't sure.
2. Category is `security` — high-stakes enough to always want a human in
   the loop, independent of confidence.
3. Urgency is `critical` — same reasoning: the cost of a wrong
   auto-routing decision scales with urgency, so the review bar
   effectively drops as urgency rises.

These are separate, independently-defensible rules rather than one fuzzy
score, which makes the *reason* for every review flag inspectable
(`review_reasons` on every `TriageResult`) instead of a black-box "trust
me" number.

---

## Known limitations (honest, on purpose)

- **Substring matching has no negation handling.** "not blocking anything"
  still matches the keyword `blocking`. For a 24-hour keyword-based
  classifier this is an accepted tradeoff, not an oversight — the fix is
  either short-window negation detection (`not\s+\w*\s*blocking`) or
  leaning on the LLM path for tickets like this, which is exactly the kind
  of nuance the hybrid design defers to Claude for.
- **Fixed category set.** New categories require a code change, not just
  new data. Deliberate, per the tradeoff notes above.
- **Single-language, English keyword tables.** The LLM path would
  generalize across languages far better than the heuristic path.
- **No persistence.** Batches run in-memory and write flat files. Fine for
  a triage *decision engine*; a real deployment would sit in front of a
  ticketing system (Zendesk, Freshdesk, etc.) that owns storage and state.

## What I'd add next with more time

- Negation-aware phrase matching in the heuristic classifier.
- A small labeled eval set (50-100 tickets with known-correct answers) to
  actually measure heuristic-vs-LLM accuracy instead of eyeballing it.
- Feed the review queue back in: track how often humans override the
  agent's call, and use that to tune the keyword tables and the confidence
  threshold over time.
- Webhook/API endpoint instead of batch-file CLI, for a live ticketing
  system integration.
