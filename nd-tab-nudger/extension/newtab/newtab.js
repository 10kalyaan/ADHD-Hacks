// Set to true to render from extension/mocks/nudge-response.json instead of
// the live server — useful for working on the UI with no backend running.
const USE_MOCK = false;

// Matches the validated palette in newtab.css. Fixed order, never cycled.
const LABEL_COLORS = {
  work: "#b4552f",
  sidequest: "#7d5088",
  chill: "#2a8a5f",
};
const LABEL_ORDER = ["work", "sidequest", "chill"];
const SURFACE = "#fdf9f6";

const $ = (id) => document.getElementById(id);

// Tab titles come from whatever page the user had open, so they are untrusted
// input. This page can call chrome.tabs, so building it with innerHTML would
// let a hostile page title run script with that access.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function svgEl(tag, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

/* ---------------- greeting ---------------- */

function renderGreeting() {
  const h = new Date().getHours();
  const part = h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
  $("greeting").textContent = `Good ${part}`;
}

/* ---------------- stats ---------------- */

function relativeAge(ms) {
  const mins = Math.floor((Date.now() - ms) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  return `${Math.floor(hours / 24)}d`;
}

async function sessionCount(key) {
  // storage.session is unavailable outside the extension context (and in mock
  // mode), so never let it break the rest of the render.
  try {
    const stored = await chrome.storage.session.get(key);
    return stored[key] || 0;
  } catch {
    return 0;
  }
}

async function renderStats(allTabs) {
  $("stat-open").textContent = allTabs.length;

  const oldest = allTabs.reduce(
    (min, t) => (t.openedAt && t.openedAt < min ? t.openedAt : min),
    Infinity
  );
  $("stat-oldest").textContent = Number.isFinite(oldest) ? relativeAge(oldest) : "–";
  $("stat-closed").textContent = await sessionCount("closedCount");
}

/* ---------------- today's split (pie) ---------------- */

function arcPath(cx, cy, r, startFrac, endFrac) {
  const a0 = startFrac * 2 * Math.PI - Math.PI / 2;
  const a1 = endFrac * 2 * Math.PI - Math.PI / 2;
  const x0 = cx + r * Math.cos(a0);
  const y0 = cy + r * Math.sin(a0);
  const x1 = cx + r * Math.cos(a1);
  const y1 = cy + r * Math.sin(a1);
  const large = endFrac - startFrac > 0.5 ? 1 : 0;
  return `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`;
}

function renderSplit(allTabs) {
  const pie = $("pie");
  const legend = $("legend");
  pie.replaceChildren();
  legend.replaceChildren();

  const counts = {};
  allTabs.forEach((t) => {
    const label = LABEL_ORDER.includes(t.label) ? t.label : "sidequest";
    counts[label] = (counts[label] || 0) + 1;
  });

  const present = LABEL_ORDER.filter((l) => counts[l]);
  const total = allTabs.length;

  if (!total) {
    $("pie-desc").textContent = "No tabs tracked yet.";
    legend.append(el("li", null, "No tabs tracked yet."));
    return;
  }

  if (present.length === 1) {
    // A single category has no slice boundaries — draw a full circle rather
    // than a 0-to-1 sweep, which degenerates into a zero-length arc.
    pie.append(svgEl("circle", { cx: 50, cy: 50, r: 46, fill: LABEL_COLORS[present[0]] }));
  } else {
    let at = 0;
    present.forEach((label) => {
      const frac = counts[label] / total;
      pie.append(
        svgEl("path", {
          d: arcPath(50, 50, 46, at, at + frac),
          fill: LABEL_COLORS[label],
          // 2px surface gap between segments, per the mark spec.
          stroke: SURFACE,
          "stroke-width": 2,
        })
      );
      at += frac;
    });
  }

  const pct = (label) => Math.round((counts[label] / total) * 100);
  $("pie-desc").textContent =
    "Open tabs by kind: " + present.map((l) => `${l} ${pct(l)}%`).join(", ") + ".";

  // Direct-labelled legend, so identity never rests on colour alone.
  present.forEach((label) => {
    const li = el("li");
    const dot = el("span", "swatch");
    dot.style.background = LABEL_COLORS[label];
    li.append(dot, el("span", "name", label), el("span", "meta", `${counts[label]} · ${pct(label)}%`));
    legend.append(li);
  });
}

/* ---------------- domain meters ---------------- */

function renderDomains(allTabs) {
  const list = $("domains");
  list.replaceChildren();

  const byDomain = {};
  allTabs.forEach((t) => {
    const d = t.domain || "unknown";
    if (!byDomain[d]) byDomain[d] = { count: 0, label: t.label };
    byDomain[d].count += 1;
  });

  const top = Object.entries(byDomain)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 5);

  if (!top.length) {
    list.append(el("li", "empty", "Nothing tracked yet."));
    return;
  }

  const max = top[0][1].count;
  top.forEach(([domain, info]) => {
    const li = el("li");
    const track = el("div", "track");
    const fill = el("div", "fill");
    // Floor the width so a single-tab domain still shows a visible mark.
    fill.style.width = `${Math.max((info.count / max) * 100, 4)}%`;
    fill.style.background = LABEL_COLORS[info.label] || LABEL_COLORS.sidequest;
    track.append(fill);
    li.append(el("span", "host", domain), track, el("span", "count", info.count));
    list.append(li);
  });
}

/* ---------------- garden ---------------- */

function sprout(i) {
  const s = svgEl("svg", { viewBox: "0 0 22 34" });
  const hue = [LABEL_COLORS.work, LABEL_COLORS.sidequest, LABEL_COLORS.chill][i % 3];
  s.append(
    svgEl("line", {
      x1: 11, y1: 34, x2: 11, y2: 14,
      stroke: "#c9a898", "stroke-width": 2, "stroke-linecap": "round",
    }),
    svgEl("ellipse", { cx: 11, cy: 9, rx: 5, ry: 8, fill: hue, opacity: 0.85 })
  );
  return s;
}

async function renderGarden() {
  const acted = await sessionCount("actedCount");

  const wrap = $("sprouts");
  wrap.replaceChildren();
  for (let i = 0; i < Math.min(acted, 24); i++) wrap.append(sprout(i));

  $("garden-count").textContent = acted ? `${acted} tended` : "";
  $("garden-note").textContent = acted
    ? "Every tab you act on plants something new. Nothing here ever wilts."
    : "Jump to a tab and something grows here. Nothing ever wilts.";
}

/* ---------------- cards + open tab list ---------------- */

function renderCards(cards) {
  const cardsEl = $("cards");
  cardsEl.replaceChildren();

  if (!cards.length) {
    cardsEl.append(el("p", "empty", "Nothing is waiting on you right now."));
    return;
  }

  cards.forEach((card) => {
    const article = el("article", "card");
    const pill = el("span", "card-label", card.label || "tab");
    pill.dataset.label = card.label || "";
    article.append(pill, el("h3", null, card.title), el("p", null, card.line));

    const button = el("button", null, "→ Jump to tab");
    button.addEventListener("click", () => jumpToTab(card.tabId));
    article.append(button);
    cardsEl.append(article);
  });
}

async function renderTabList(tabs) {
  const list = $("tab-list");
  list.replaceChildren();

  if (!tabs.length) {
    list.append(el("li", "empty", "Nothing else open."));
    return;
  }

  // Tabs the user has actually switched to this session. Anything tracked but
  // never activated was opened in the background and never read.
  let seen = [];
  try {
    ({ seenTabs: seen = [] } = await chrome.storage.session.get("seenTabs"));
  } catch {
    seen = [];
  }

  // Cap the list: a tab hoarder can have dozens open, and an endless column
  // buries everything below it.
  const SHOWN = 8;
  tabs.slice(0, SHOWN).forEach((tab) => {
    const li = el("li");

    const tag = el("span", "tag", tab.label || "tab");
    tag.dataset.label = tab.label || "";

    li.append(tag, el("span", "title", tab.title), el("span", "host", tab.domain));

    if (!seen.includes(tab.tabId)) {
      li.append(el("span", "flag", "not opened"));
    }

    li.addEventListener("click", () => jumpToTab(tab.tabId));
    list.append(li);
  });

  if (tabs.length > SHOWN) {
    list.append(el("li", "more", `+${tabs.length - SHOWN} more open`));
  }
}

/* ---------------- actions ---------------- */

async function jumpToTab(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    await chrome.tabs.update(tabId, { active: true });
    // Activating a tab does not raise the window it lives in. Without this
    // step a tab in another window goes active out of sight and the click
    // looks like it did nothing.
    if (tab.windowId != null) {
      await chrome.windows.update(tab.windowId, { focused: true });
    }
    try {
      const acted = await sessionCount("actedCount");
      await chrome.storage.session.set({ actedCount: acted + 1 });
    } catch {
      /* the garden counter is cosmetic — never block the jump on it */
    }
  } catch (err) {
    // Tab closed between /nudge and the click — refresh so the page stops
    // offering it rather than sitting there inert.
    console.warn("[nd-tab-nudger] jump failed:", err.message);
    loadNudge();
  }
}

function setupSearch() {
  $("search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const q = $("search-input").value.trim();
    if (!q) return;
    const looksLikeUrl = !/\s/.test(q) && /^(https?:\/\/|[\w-]+\.[a-z]{2,})/i.test(q);
    window.location.href = looksLikeUrl
      ? (q.startsWith("http") ? q : `https://${q}`)
      : `https://www.google.com/search?q=${encodeURIComponent(q)}`;
  });
}

/* ---------------- boot ---------------- */

async function loadNudge() {
  try {
    const data = USE_MOCK
      ? await fetch("../mocks/nudge-response.json").then((r) => r.json())
      : await getNudge();

    const cards = data.cards || [];
    const openTabs = data.open_tabs || [];
    // Cards come out of the same tracked set, so the stats span both.
    const allTabs = [...cards, ...openTabs];

    renderCards(cards);
    await renderTabList(openTabs);
    renderSplit(allTabs);
    renderDomains(allTabs);
    await renderStats(allTabs);
  } catch (err) {
    $("cards").replaceChildren(
      el("p", "error", "Couldn't reach the nudge server. Is it running?")
    );
    console.error(err);
  }
}

renderGreeting();
setupSearch();
renderGarden();
loadNudge();
