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

// Exposed as globals for MV3 non-module scripts (background.js, content
// scripts). newtab.js can also just include this file via <script> tag.
if (typeof module !== "undefined") {
  module.exports = { ingestTab, getNudge, API_BASE };
}
