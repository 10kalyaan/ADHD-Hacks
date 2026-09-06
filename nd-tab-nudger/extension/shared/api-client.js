// Thin wrapper around the local Flask server. Shared by background.js,
// newtab.js, and content-script.js so the API contract lives in one place.

const API_BASE = "http://localhost:5000";

async function ingestTab({ tabId, title, url, domain, openedAt }) {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tabId, title, url, domain, openedAt }),
  });
  if (!res.ok) throw new Error(`/ingest failed: ${res.status}`);
  return res.json();
}

async function getNudge() {
  const res = await fetch(`${API_BASE}/nudge`);
  if (!res.ok) throw new Error(`/nudge failed: ${res.status}`);
  return res.json();
}

// Tells the server which tabs are still open so it can drop the rest.
// Closed tabs are the oldest, so leaving them in would let them dominate the
// staleness ranking and get nudged even though they no longer exist.
async function syncTabs(openTabIds) {
  const res = await fetch(`${API_BASE}/tabs/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ openTabIds }),
  });
  if (!res.ok) throw new Error(`/tabs/sync failed: ${res.status}`);
  return res.json();
}

// Exposed as globals for MV3 non-module scripts (background.js, content
// scripts). newtab.js can also just include this file via <script> tag.
if (typeof module !== "undefined") {
  module.exports = { ingestTab, getNudge, syncTabs, API_BASE };
}
