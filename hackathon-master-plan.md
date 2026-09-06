# ND Tab Nudger — Hackathon Build Plan (Single Source of Truth)

Actian VectorAI DB Build Challenge submission. 2–3 hr build, 3-person team,
runs local. This doc replaces the scattered planning across chat — read this,
not the earlier docs, if there's a conflict.

---

## 1. Product

A Chrome extension for neurodivergent users that:
- Tracks time per tab/domain
- Nudges the user toward what to do next on their open tabs (instead of doomscrolling) via the New Tab page
- Interrupts doomscrolling in-page when they land on a known distraction domain

Tone: playful/witty, never judgmental or shaming. Broad ND audience (ADHD + autism), targeting two failure modes: doomscrolling and tab hoarding.

---

## 2. Why this architecture

**VectorAI DB is Python-only (SDK: `actian-vectorai-client`), so a Chrome
extension can't talk to it directly.** That's why there's a local Flask
server in the middle — it's not extra complexity for its own sake, it's the
only way to use the required tool from a browser extension.

**Two collections, three DB behaviors, all required by the challenge rules
(storage + classification + "beyond basic similarity search"):**

| Collection | Purpose | Behavior |
|---|---|---|
| `tabs` | Storage | Every tracked tab is a point: title embedding + payload (tabId, domain, openedAt, label) |
| `labels` | Classification seed set | ~15-18 hand-written example texts, 5-6 each for `work`/`reference`/`distraction` |

- **Storage**: `tabs` collection — this is the "storage" requirement, done for real (not a bolt-on log file).
- **Classification**: new tab's title embedding gets compared against `labels` via similarity search, majority-vote of top-k neighbors assigns a label. This is the "classification" requirement.
- **Beyond basic similarity search**: nudge candidate ranking uses **hybrid fusion** (client-side RRF, built into the SDK) — one query ranks by staleness (time since opened), a second ranks by semantic closeness to a fixed "actionable task" reference vector, fused into one ranked list. This satisfies the "must go beyond plain similarity search" judging criterion explicitly.

**Why a live Claude call instead of pre-generated/cached nudges:** the original production plan (batch generation + cache, to avoid per-open latency/cost at scale) is unnecessary for a demo with a handful of users over 2-3 hours. One live call per `/nudge` request is simpler to build and still fast enough.

**Why static host_permissions for the overlay instead of dynamic per-domain requests:** the production plan used `optional_host_permissions` + runtime `chrome.permissions.request()` scoped to user-edited domains, for a minimal install prompt and a clean privacy story. That machinery (permission request flow, dynamic content-script registration) is the expensive part to build, not the overlay itself — so for the hackathon, hardcode the distraction domain list directly in the manifest.

---

## 3. Priority ladder

Build top-down. Stop wherever the clock runs out — everything above the cut line still works as a demo.

**P0 — required, this is the real 2-3hr scope**
1. Tab tracking (background.js → `/ingest` → `tabs` collection)
2. Classification via VectorAI DB (`labels` seed collection, KNN majority vote)
3. New Tab nudge UI (hybrid fusion ranking + Claude one-liner, jump-to-tab action)
4. Doomscroll overlay — in-page corner card on distraction domains
5. Working actions on both surfaces — click-through to focus the target tab (`chrome.tabs.update`), not static text

**P1 — add if P0 finishes with time to spare**
6. Flat list of other open tabs on the New Tab page (read-only, no bulk actions)
7. Hardcoded in-memory "snooze this session" toggle (no persistence, no settings page)

**P2 — only if P0 and P1 are both solid and demo-ready**
8. Toolbar popup
9. Stash/save action on the tab list

Explicitly **not** in scope for this build (from the original production plan, deferred to a post-hackathon version if this goes anywhere): personalization/learning loop, reflection summaries, settings page, idle-time precision (vs. simple "time since opened"), pre-generation/caching of nudges, dynamic per-domain permission requests, data export.

---

## 4. Time budget

1. **~15 min** — VectorAI DB up via Docker, both collections created, `labels` seeded. *Do this first, as a group — everyone else is blocked on it existing, even if not on it being finished.*
2. **~30 min** — Flask `/ingest`: embed (OpenAI `text-embedding-3-small`) + classify + upsert
3. **~25 min** — Flask `/nudge`: hybrid fusion + single Claude call, returns candidates + overlay line
4. **~20 min** — extension skeleton: manifest (incl. static host_permissions), background.js tracking + POST
5. **~20 min** — New Tab page: fetch `/nudge`, render cards, jump-to-tab action
6. **~20 min** — content script: inject on distraction domains, render corner card (shadow DOM), jump/dismiss actions
7. **~15-20 min buffer** — CORS/wiring fixes, one full run-through, README, demo video

Total: ~2h15-2h30 for full P0. Buffer beyond that goes to P1.

---

## 5. Team split

**First 10 minutes, all three together:** lock the API contract in §6, and get VectorAI DB running via `docker-compose up`. Nobody starts their own piece until both of those are done — everything downstream depends on them.

### Workstream A — Extension / UI (1 person)
Owns everything in `extension/`.
- `manifest.json`, `background.js` (tab tracking, POST to `/ingest`)
- New Tab page (fetch `/nudge`, render cards + tab list, jump-to-tab)
- Overlay content script (inject on distraction domains, fetch `/nudge`, render corner card, jump/dismiss)
- **Unblocked immediately** by the mocked `/nudge` response in `extension/mocks/` — don't wait for the real server.
- **Checkpoint:** extension fully clickable against mock JSON before integration.

### Workstream B — Backend: Ingestion & Classification (1 person)
Owns `server/ingestion/` + `tabs`/`labels` schemas.
- `POST /ingest` route, embedding call, upsert into `tabs`, classification (similarity search + majority vote vs `labels`), seed script
- **Unblocked immediately** once VectorAI DB + collections exist.
- **Checkpoint:** `curl POST /ingest` with a fake payload returns 200 and a classified point lands in `tabs`.

### Workstream C — Backend: Nudge Generation & Ranking (1 person)
Owns `server/nudging/`.
- `GET /nudge` route, hybrid fusion query (RRF), single Claude call for copy, overlay line reuses the same response
- **Unblocked immediately** once VectorAI DB exists — can work against manually-inserted fake points while B's ingestion is still being built, so B and C don't block each other.
- **Checkpoint:** `curl GET /nudge` returns real fused ranking + real Claude copy.

### Integration checkpoints
- **T+10 min:** contract locked, DB running, everyone starts
- **T+~45 min:** B and C each confirm their route standalone (curl/Postman)
- **T+~90 min:** A swaps mocks for real fetch calls, first real end-to-end run
- **remaining time:** bug fixing, polish, record demo, write README

---

## 6. API Contract (locked first, source of truth)

### `POST /ingest`
Request:
```json
{
  "tabId": 123,
  "title": "Reddit - Dive into anything",
  "url": "https://reddit.com/r/all",
  "domain": "reddit.com",
  "openedAt": 1730000000000
}
```
Response: `200 { "status": "ok", "label": "distraction" }`

### `GET /nudge`
Response:
```json
{
  "cards": [
    {
      "tabId": 456,
      "title": "Q3 planning doc",
      "domain": "docs.google.com",
      "line": "This one's been waiting patiently. Suspiciously patiently.",
      "label": "work"
    },
    {
      "tabId": 789,
      "title": "React hooks guide",
      "domain": "reactjs.org",
      "line": "Still open from three hours ago. It's not going anywhere on its own.",
      "label": "reference"
    }
  ],
  "overlay_line": "Reddit again? Your Q3 doc says hi.",
  "open_tabs": [
    { "tabId": 111, "title": "Gmail", "domain": "mail.google.com", "openedAt": 1729999000000 }
  ]
}
```
`overlay_line` and `cards` share one endpoint so both the content script and the New Tab page call the same thing.

---

## 7. Repo structure

```
nd-tab-nudger/
├── extension/                       # Workstream A
│   ├── manifest.json
│   ├── background.js
│   ├── newtab/
│   │   ├── newtab.html
│   │   ├── newtab.js
│   │   └── newtab.css
│   ├── overlay/
│   │   ├── content-script.js
│   │   └── overlay.css
│   ├── shared/
│   │   └── api-client.js
│   ├── mocks/
│   │   └── nudge-response.json
│   └── icons/
│
├── server/
│   ├── app.py
│   ├── config.py                    # port, distraction domain list
│   ├── requirements.txt
│   │
│   ├── ingestion/                   # Workstream B
│   │   ├── routes.py
│   │   ├── embeddings.py
│   │   ├── classifier.py
│   │   └── seed_labels.py
│   │
│   ├── nudging/                     # Workstream C
│   │   ├── routes.py
│   │   ├── ranking.py               # hybrid fusion (RRF)
│   │   └── copy_generator.py        # Claude call
│   │
│   └── vectordb/
│       └── client.py                # shared client + collection schemas
│
├── docker-compose.yml                # VectorAI DB locally
├── .env.example                      # ANTHROPIC_API_KEY, OPENAI_API_KEY, VECTORAI_HOST
├── docs/
│   ├── api-contract.md               # copy of §6, keep in sync
│   └── demo-script.md
└── README.md
```

---

## 8. Submission requirements (DoraHacks)

Confirm before end of build:
- [ ] Public GitHub/GitLab repo with README
- [ ] README covers: what it does, how VectorAI DB is used (storage + classification + hybrid fusion), setup steps, how to run locally
- [ ] Working demo — video or Loom, since a live link isn't the deliverable here
- [ ] Short write-up submitted through DoraHacks

Judging weights to keep in mind while building: VectorAI DB usage 30% (this is why §2's "why this architecture" matters — be ready to explain it, not just show it working), real-world impact 25%, technical execution 25%, demo/presentation 20%.

---

## 9. Still open / decide before or during build

- Exact distraction domain list to hardcode (reddit, twitter/x, instagram, youtube — confirm the set)
- What text exactly goes into the `labels` seed collection — someone should draft the 15-18 example lines before Workstream B needs them at the ~15 min mark
- Demo script / what you'll actually click through on camera — not written yet
