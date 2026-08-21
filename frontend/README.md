# Triage Agent — Frontend

A minimal React UI for the ticket triage agent. Talks to the real Python
agent through `api.py` (Flask) — it does not reimplement any classification
logic client-side.

## Run it

You need **both** the backend and the frontend running at the same time,
in two separate terminals.

**Terminal 1 — backend (from the project root, not this folder):**
```bash
pip install -r requirements.txt
python api.py
# Serving on http://localhost:5000
```

**Terminal 2 — frontend (from this folder):**
```bash
npm install
npm run dev
# Open http://localhost:5173
```

If the API is running somewhere other than `http://localhost:5000`, copy
`.env.example` to `.env` and change `VITE_API_URL`.

## What's in here

| Path | Purpose |
|---|---|
| `src/api.js` | Every network call to the Flask API — one place, one shape |
| `src/constants.js` | Urgency/category labels and colors, shared across components |
| `src/components/TryItPanel.jsx` | Type a ticket, get a live classification |
| `src/components/QueuePanel.jsx` | Fetches the sample tickets, batch-triages them, filterable list |
| `src/components/TicketResult.jsx` | The result row used in both panels |
| `src/App.jsx` | Tabs + API health check |

## Building for deployment

```bash
npm run build
```
Outputs static files to `dist/` — deploy that folder anywhere that serves
static files (Netlify, Vercel, S3, GitHub Pages). Set `VITE_API_URL` to
wherever you deploy `api.py` (Render, Railway, Fly.io, etc.) before building.
