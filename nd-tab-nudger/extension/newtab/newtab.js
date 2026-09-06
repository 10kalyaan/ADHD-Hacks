// Set to true to render from extension/mocks/nudge-response.json instead of
// the live server — useful for working on the UI with no backend running.
const USE_MOCK = false;

const cardsEl = document.getElementById("cards");
const tabListEl = document.getElementById("tab-list");

function labelEmoji(label) {
  return { work: "🛠️", reference: "📚", distraction: "🌀" }[label] || "•";
}

// Tab titles come from whatever page the user had open, so they are
// untrusted input. This page can call chrome.tabs, so building it with
// innerHTML would let a hostile page title run script with that access.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function renderCards(cards) {
  cardsEl.replaceChildren();
  cards.forEach((card) => {
    const article = el("article", "card");
    article.append(
      el("div", "card-label", `${labelEmoji(card.label)} ${card.domain}`),
      el("h3", null, card.title),
      el("p", null, card.line)
    );

    const button = el("button", null, "Take me there");
    button.dataset.tabId = card.tabId;
    button.addEventListener("click", () => jumpToTab(card.tabId));
    article.append(button);

    cardsEl.append(article);
  });
}

function renderTabList(tabs) {
  tabListEl.replaceChildren();
  tabs.forEach((tab) => {
    const li = document.createElement("li");
    li.append(el("span", null, tab.domain), " — ", el("em", null, tab.title));
    li.addEventListener("click", () => jumpToTab(tab.tabId));
    tabListEl.append(li);
  });
}

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
  } catch (err) {
    // Tab closed between /nudge and the click — refresh so the page stops
    // offering it rather than sitting there inert.
    console.warn("[nd-tab-nudger] jump failed:", err.message);
    loadNudge();
  }
}

async function loadNudge() {
  try {
    const data = USE_MOCK
      ? await fetch("../mocks/nudge-response.json").then((r) => r.json())
      : await getNudge();

    renderCards(data.cards || []);
    renderTabList(data.open_tabs || []);
  } catch (err) {
    cardsEl.replaceChildren(
      el("p", "error", "Couldn't reach the nudge server. Is it running?")
    );
    console.error(err);
  }
}

loadNudge();
