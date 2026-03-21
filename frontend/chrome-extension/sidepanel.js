const API_BASE = "http://localhost:8000";

let sessionId = null;
let departureTimestamp = null;

const summaryNode = document.getElementById("summary");
const keywordsNode = document.getElementById("keywords");
const transcriptNode = document.getElementById("transcript");

async function refreshTranscript() {
  if (!sessionId) return;
  const response = await fetch(`${API_BASE}/session/${sessionId}/transcript`);
  const data = await response.json();
  transcriptNode.innerHTML = data.transcript
    .map((entry) => `<p><strong>${new Date(entry.timestamp).toLocaleTimeString()}</strong><br/>${entry.text}</p>`)
    .join("");
}

document.getElementById("start-session").addEventListener("click", async () => {
  const response = await fetch(`${API_BASE}/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "cloud", language: "English", recap_length: "standard" })
  });
  const data = await response.json();
  sessionId = data.session_id;
  await chrome.storage.local.set({ sessionId });
  chrome.runtime.sendMessage({ type: "SET_SESSION_ID", sessionId });
  await refreshTranscript();
});

document.getElementById("leave").addEventListener("click", async () => {
  departureTimestamp = new Date().toISOString();
  await chrome.storage.local.set({ departureTimestamp });
});

document.getElementById("catch-up").addEventListener("click", async () => {
  if (!sessionId || !departureTimestamp) return;
  const response = await fetch(`${API_BASE}/recap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      from_timestamp: departureTimestamp,
      to_timestamp: new Date().toISOString()
    })
  });
  const data = await response.json();
  summaryNode.textContent = data.summary;
  keywordsNode.innerHTML = data.keywords.map((keyword) => `<span>${keyword}</span>`).join("");
  departureTimestamp = null;
  await chrome.storage.local.remove("departureTimestamp");
  await refreshTranscript();
});

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "HOTKEY_CATCH_ME_UP") {
    document.getElementById("catch-up").click();
  }
});

window.setInterval(() => {
  void refreshTranscript();
}, 5000);
