const API_BASE = "http://localhost:8000";

const sessionStatusNode = document.getElementById("session-status");
const captureStatusNode = document.getElementById("capture-status");
const absenceStatusNode = document.getElementById("absence-status");
const absenceTimerNode = document.getElementById("absence-timer");
const summaryNode = document.getElementById("summary");
const keywordsNode = document.getElementById("keywords");
const transcriptNode = document.getElementById("transcript");
const transcriptCountNode = document.getElementById("transcript-count");
const consentModalNode = document.getElementById("consent-modal");
const consentCopyNode = document.getElementById("consent-copy");

let extensionState = null;
let timerInterval = null;
let pendingSessionStart = false;

function formatDuration(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map((value) => value.toString().padStart(2, "0")).join(":");
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function refreshTranscript() {
  if (!extensionState?.sessionId) {
    transcriptNode.innerHTML = "";
    transcriptCountNode.textContent = "0 chunks";
    return;
  }

  const response = await fetch(`${API_BASE}/session/${extensionState.sessionId}/transcript`);
  const data = await response.json();
  transcriptCountNode.textContent = `${data.transcript.length} chunks`;
  transcriptNode.innerHTML = data.transcript
    .map((entry) => `<p><strong>${formatTime(entry.timestamp)}</strong><br/>${entry.text}</p>`)
    .join("");
}

function renderState() {
  const state = extensionState || {};
  sessionStatusNode.textContent = state.sessionId ? `Live session ${state.sessionId.slice(0, 8)}` : "Inactive";
  captureStatusNode.textContent = state.captureStatus || "idle";
  summaryNode.textContent = state.latestSummary || "Waiting for your first recap.";
  keywordsNode.innerHTML = (state.latestKeywords || []).map((keyword) => `<span>${keyword}</span>`).join("");
  transcriptCountNode.textContent = `${state.transcriptCount || 0} chunks`;

  if (timerInterval) clearInterval(timerInterval);

  if (state.departureTimestamp) {
    absenceStatusNode.textContent = `Away since ${formatTime(state.departureTimestamp)}`;
    timerInterval = setInterval(() => {
      const seconds = Math.max(0, Math.floor((Date.now() - new Date(state.departureTimestamp).getTime()) / 1000));
      absenceTimerNode.textContent = formatDuration(seconds);
    }, 1000);
  } else {
    absenceStatusNode.textContent = "Present";
    absenceTimerNode.textContent = "00:00:00";
  }
}

function openConsentModal() {
  const modeLabel = "AssemblyAI tab audio capture";
  consentCopyNode.textContent =
    `Audio for this lecture will be processed via ${modeLabel}. No lecture data is shared without your consent.`;
  consentModalNode.classList.remove("hidden");
}

function closeConsentModal() {
  pendingSessionStart = false;
  consentModalNode.classList.add("hidden");
}

async function syncState() {
  const response = await chrome.runtime.sendMessage({ type: "GET_EXTENSION_STATE" });
  extensionState = response.state;
  renderState();
  await refreshTranscript();
}

document.getElementById("start-session").addEventListener("click", async () => {
  pendingSessionStart = true;
  openConsentModal();
});

document.getElementById("consent-cancel").addEventListener("click", () => {
  closeConsentModal();
});

document.getElementById("consent-accept").addEventListener("click", async () => {
  if (!pendingSessionStart) {
    consentModalNode.classList.add("hidden");
    return;
  }
  const response = await chrome.runtime.sendMessage({
    type: "START_SESSION",
    payload: { mode: "cloud", language: "English", recap_length: "standard" },
  });
  pendingSessionStart = false;
  consentModalNode.classList.add("hidden");
  extensionState = response.state;
  renderState();
  await refreshTranscript();
});

document.getElementById("start-capture").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  await chrome.runtime.sendMessage({ type: "START_TAB_CAPTURE", tabId: tab.id });
  await syncState();
});

document.getElementById("stop-capture").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "STOP_TAB_CAPTURE" });
  await syncState();
});

document.getElementById("leave").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "SET_DEPARTURE" });
  await syncState();
});

document.getElementById("catch-up").addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ type: "REQUEST_RECAP" });
  extensionState = response.state;
  renderState();
  await refreshTranscript();
});

window.addEventListener("message", async (event) => {
  if (event.data?.type === "HOTKEY_CATCH_ME_UP") {
    document.getElementById("catch-up").click();
  }
});

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "EXTENSION_STATE") {
    extensionState = message.state;
    renderState();
    void refreshTranscript();
  }
  if (message.type === "HOTKEY_CATCH_ME_UP") {
    document.getElementById("catch-up").click();
  }
});

window.setInterval(() => {
  void refreshTranscript();
}, 5000);

void syncState();
