// Set to true to render from extension/mocks/nudge-response.json instead of
// the live server — useful for working on the UI with no backend running.
const USE_MOCK = false;

const cardsEl = document.getElementById("cards");
const tabListEl = document.getElementById("tab-list");

function labelEmoji(label) {
  return { work: "🛠️", reference: "📚", distraction: "🌀" }[label] || "•";
}

function renderCards(cards) {
  cardsEl.innerHTML = "";
  cards.forEach((card) => {
    const el = document.createElement("article");
    el.className = "card";
    el.innerHTML = `
      <div class="card-label">${labelEmoji(card.label)} ${card.domain}</div>
      <h3>${card.title}</h3>
      <p>${card.line}</p>
      <button data-tab-id="${card.tabId}">Take me there</button>
    `;
    el.querySelector("button").addEventListener("click", () => jumpToTab(card.tabId));
    cardsEl.appendChild(el);
  });
}

function renderTabList(tabs) {
  tabListEl.innerHTML = "";
  tabs.forEach((tab) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${tab.domain}</span> — <em>${tab.title}</em>`;
    li.addEventListener("click", () => jumpToTab(tab.tabId));
    tabListEl.appendChild(li);
  });
}

function jumpToTab(tabId) {
  // The tab can be gone if it closed between /nudge and the click. Reload so
  // the page reflects reality instead of appearing inert.
  chrome.tabs.update(tabId, { active: true }, () => {
    if (chrome.runtime.lastError) {
      console.warn("[nd-tab-nudger]", chrome.runtime.lastError.message);
      loadNudge();
    }
  });
}

async function loadNudge() {
  try {
    const data = USE_MOCK
      ? await fetch("../mocks/nudge-response.json").then((r) => r.json())
      : await getNudge();

    renderCards(data.cards || []);
    renderTabList(data.open_tabs || []);
  } catch (err) {
    cardsEl.innerHTML = `<p class="error">Couldn't reach the nudge server. Is it running?</p>`;
    console.error(err);
  }
}

loadNudge();
