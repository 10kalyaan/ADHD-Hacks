importScripts("shared/api-client.js");

// domain -> openedAt (ms), so we only send /ingest once per tab load rather
// than on every onUpdated tick.
const trackedTabs = new Map();

function domainFromUrl(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function isTrackable(url) {
  return !!url && (url.startsWith("http://") || url.startsWith("https://"));
}

async function trackTab(tab) {
  if (!tab || !isTrackable(tab.url)) return;
  if (trackedTabs.has(tab.id)) return;

  const domain = domainFromUrl(tab.url);
  if (!domain) return;

  const openedAt = Date.now();
  trackedTabs.set(tab.id, { domain, openedAt });

  try {
    await ingestTab({
      tabId: tab.id,
      title: tab.title || domain,
      url: tab.url,
      domain,
      openedAt,
    });
  } catch (err) {
    console.warn("[nd-tab-nudger] ingest failed", err);
  }
}

chrome.tabs.onCreated.addListener((tab) => trackTab(tab));

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") trackTab(tab);
});

// Tell the server which tabs are still open so it can drop the closed ones.
// Reconciling the whole set (rather than deleting one id) also clears rows
// orphaned by a browser restart, where onRemoved never fires.
async function syncOpenTabs() {
  try {
    const tabs = await chrome.tabs.query({});
    await syncTabs(tabs.filter((t) => isTrackable(t.url)).map((t) => t.id));
  } catch (err) {
    console.warn("[nd-tab-nudger] tab sync failed", err);
  }
}

// Closing a window fires onRemoved once per tab; coalesce the burst into a
// single reconcile instead of one full sync per closed tab.
let syncTimer = null;
function scheduleSync() {
  clearTimeout(syncTimer);
  syncTimer = setTimeout(syncOpenTabs, 400);
}

// Session-only counters the New Tab page reads for its stat row. storage.session
// lives in memory and clears when the browser closes, which is exactly the
// "this session" scope we want -- nothing persisted, nothing to clean up.
async function bumpSessionCounter(key) {
  try {
    const stored = await chrome.storage.session.get(key);
    await chrome.storage.session.set({ [key]: (stored[key] || 0) + 1 });
  } catch (err) {
    console.warn("[nd-tab-nudger] counter failed", err);
  }
}

chrome.tabs.onRemoved.addListener((tabId) => {
  // Only count tabs we were actually tracking, so closing a blank or internal
  // page does not inflate the number.
  if (trackedTabs.has(tabId)) bumpSessionCounter("closedCount");
  trackedTabs.delete(tabId);
  scheduleSync();
});

// Backfill anything already open when the extension loads/reloads, then prune
// whatever the server still thinks is open from a previous session.
chrome.tabs.query({}, async (tabs) => {
  await Promise.all(tabs.map(trackTab));
  syncOpenTabs();
});

// Content scripts can't call chrome.tabs directly, so the overlay's
// "jump to tab" button routes through here.
chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "JUMP_TO_TAB" && typeof msg.tabId === "number") {
    focusTab(msg.tabId);
  }
});

async function focusTab(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    await chrome.tabs.update(tabId, { active: true });
    // Activating a tab does not raise its window, so a target in another
    // window would go active off-screen and the jump would look broken.
    if (tab.windowId != null) {
      await chrome.windows.update(tab.windowId, { focused: true });
    }
    bumpSessionCounter("actedCount");
  } catch (err) {
    // Tab closed since /nudge was fetched — reconcile so it stops being
    // recommended.
    console.warn("[nd-tab-nudger] jump failed:", err.message);
    syncOpenTabs();
  }
}
