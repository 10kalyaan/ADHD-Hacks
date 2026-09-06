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

chrome.tabs.onRemoved.addListener((tabId) => {
  trackedTabs.delete(tabId);
});

// Backfill anything already open when the extension loads/reloads.
chrome.tabs.query({}, (tabs) => tabs.forEach(trackTab));

// Content scripts can't call chrome.tabs directly, so the overlay's
// "jump to tab" button routes through here.
chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "JUMP_TO_TAB" && typeof msg.tabId === "number") {
    chrome.tabs.update(msg.tabId, { active: true });
  }
});
