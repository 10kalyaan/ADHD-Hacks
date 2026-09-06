// Flip to false once the Flask server is up (Workstream C checkpoint).
// Keeps Workstream A unblocked against extension/mocks/nudge-response.json.
const USE_MOCK = true;

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
  chrome.tabs.update(tabId, { active: true });
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
