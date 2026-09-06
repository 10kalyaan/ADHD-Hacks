# ND Tab Nudger

Chrome extension for neurodivergent users (ADHD + autism) that tracks open
tabs and nudges you toward what actually matters — instead of doomscrolling
or drowning in forty open tabs. Built for the Actian VectorAI DB Build
Challenge.

## What it does

- Tracks every open tab (title, domain, time opened) as it's created.
- Classifies each tab as `work`, `reference`, or `distraction` via
  similarity search against a hand-labeled seed set.
- On a new tab, surfaces the 1-2 tabs that most need your attention —
  ranked by a fusion of staleness (how long it's been waiting) and
  semantic closeness to "an actionable task" — with a one-liner per card
  (naming one tiny next action, not the whole task) and a one-click jump
  back to that tab.
- On known distraction domains (Reddit, X, Instagram, YouTube), shows a
  small dismissible corner card nudging you back to what you were doing.
- If you've bounced between distraction tabs several times in the last
  15 minutes, nudges adapt: fewer cards (choice overload makes ADHD
  task-initiation harder, not easier) and a sharper, more concrete line.
  This is a session-only in-memory counter — see
  [server/nudging/session_state.py](server/nudging/session_state.py) —
  not a learned profile; it resets on server restart.

Tone throughout: playful, never shaming. Nudge copy is grounded in
ADHD task-initiation research (implementation intentions / next-smallest-step
framing, and leaning on curiosity over urgency) — see the design notes at
the top of [server/nudging/copy_generator.py](server/nudging/copy_generator.py).

## How VectorAI DB is used

| Requirement | How it's satisfied |
|---|---|
| **Storage** | Every tracked tab is a point in the `tabs` collection — title embedding + payload (tabId, domain, openedAt, label). Not a bolt-on log file. |
| **Classification** | New tab titles are embedded and compared via similarity search against `labels`, a ~18-example seed collection (work/reference/distraction). Majority vote of the top-k neighbors assigns the label. |
| **Beyond basic similarity search** | Nudge ranking uses **hybrid fusion** (client-side Reciprocal Rank Fusion): one ranking by staleness (time since opened), one by semantic closeness to a fixed "actionable task" anchor vector, fused into a single ranked list. See [server/nudging/ranking.py](server/nudging/ranking.py). |

Why a Flask server in the middle: `actian-vectorai-client` is Python-only, so
a Chrome extension can't call VectorAI DB directly — the local server is the
only way to use the required tool from a browser extension.

## Setup

Prereqs: Docker, Python 3.10+, a Gemini API key, an OpenAI API key.

```bash
cp .env.example .env   # fill in GEMINI_API_KEY and OPENAI_API_KEY
docker compose up -d   # VectorAI DB: gRPC :6574, REST :6573, web UI :6575

cd server
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python smoke_test.py              # optional: verifies the DB layer, no API key needed
python -m ingestion.seed_labels   # seeds the labels collection once
python app.py                     # starts Flask on :5000
```

The SDK talks gRPC, so `VECTORAI_URL` is a bare `host:port` — a `http://`
scheme is rejected. Browse the collections at <http://localhost:6575> while
demoing.

Then load the extension:

1. Go to `chrome://extensions`, enable Developer Mode.
2. "Load unpacked" → select the `extension/` folder.
3. Open a new tab, browse normally, visit Reddit/YouTube/etc. to see the
   overlay.

`extension/newtab/newtab.js` has a `USE_MOCK` flag — flip it to `false`
once the server above is running; it defaults to mock data so the UI works
standalone.

## Repo structure

```
nd-tab-nudger/
├── extension/        # Chrome extension (manifest, background, new tab, overlay)
├── server/
│   ├── ingestion/     # POST /ingest — embed, classify, upsert
│   ├── nudging/       # GET /nudge — hybrid fusion ranking + Gemini copy
│   └── vectordb/      # shared VectorAI DB client + collection schemas
├── docker-compose.yml
└── docs/              # API contract, demo script
```

See [docs/api-contract.md](docs/api-contract.md) for the full request/response
shapes.

## Scope

This is a 2-3 hour hackathon build. Not in scope: a persisted/learned user
profile, reflection summaries, a settings page, idle-time precision, nudge
pre-generation/caching, dynamic per-domain permission requests, data export.
(The distraction-pressure signal above is session-only in-memory state, not
a learning loop — it doesn't persist anything or read the DB.)
