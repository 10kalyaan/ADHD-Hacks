// Injected only on the distraction domains listed in manifest.json's
// content_scripts.matches. Renders a dismissible corner card inside a
// shadow DOM so the host page's CSS can't clobber it (or vice versa).

(async function () {
  const SESSION_DISMISS_KEY = "nd-tab-nudger-dismissed";
  if (sessionStorage.getItem(SESSION_DISMISS_KEY)) return;

  let data;
  try {
    const res = await fetch("http://localhost:5000/nudge");
    if (!res.ok) return;
    data = await res.json();
  } catch {
    return; // server not running — fail silent, never block the page
  }

  if (!data || !data.overlay_line) return;

  const host = document.createElement("div");
  host.id = "nd-tab-nudger-overlay-host";
  document.documentElement.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });

  const styleLink = document.createElement("link");
  styleLink.rel = "stylesheet";
  styleLink.href = chrome.runtime.getURL("overlay/overlay.css");
  shadow.appendChild(styleLink);

  const card = document.createElement("div");
  card.className = "nudger-card";

  const targetCard = (data.cards && data.cards[0]) || null;

  card.innerHTML = `
    <button class="nudger-close" aria-label="Dismiss">×</button>
    <p class="nudger-line">${data.overlay_line}</p>
    ${targetCard ? `<button class="nudger-jump">Take me to ${targetCard.domain}</button>` : ""}
  `;
  shadow.appendChild(card);

  shadow.querySelector(".nudger-close").addEventListener("click", () => {
    sessionStorage.setItem(SESSION_DISMISS_KEY, "1");
    host.remove();
  });

  const jumpBtn = shadow.querySelector(".nudger-jump");
  if (jumpBtn && targetCard) {
    jumpBtn.addEventListener("click", () => {
      chrome.runtime.sendMessage({ type: "JUMP_TO_TAB", tabId: targetCard.tabId });
    });
  }
})();
