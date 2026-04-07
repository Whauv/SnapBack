import { createMeetExtensionHostAdapter } from "./host-adapter.js";

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

const host = createMeetExtensionHostAdapter();

let extensionState = null;
let timerInterval = null;
let pendingSessionStart = false;

function createElement(tagName, options = {}) {
  const node = document.createElement(tagName);
  if (options.className) node.className = options.className;
  if (options.textContent) node.textContent = options.textContent;
  return node;
}

function renderKeywordBadges(keywords) {
  keywordsNode.replaceChildren();
  for (const keyword of keywords || []) {
    keywordsNode.appendChild(createElement("span", { textContent: keyword }));
  }
}

function renderTranscriptEntries(entries) {
  transcriptNode.replaceChildren();
  for (const entry of entries) {
    const paragraph = createElement("p");
    const strong = createElement("strong", { textContent: formatTime(entry.timestamp) });
    paragraph.appendChild(strong);
    paragraph.appendChild(document.createElement("br"));
    paragraph.appendChild(document.createTextNode(entry.text));
    transcriptNode.appendChild(paragraph);
  }
}

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
    transcriptNode.replaceChildren();
    transcriptCountNode.textContent = "0 chunks";
    return;
  }

  const data = await host.getTranscript(extensionState.sessionId);
  transcriptCountNode.textContent = `${data.transcript.length} chunks`;
  renderTranscriptEntries(data.transcript);
}

function renderState() {
  const state = extensionState || {};
  sessionStatusNode.textContent = state.sessionId ? `Live session ${state.sessionId.slice(0, 8)}` : "Inactive";
  captureStatusNode.textContent = state.captureStatus || "idle";
  summaryNode.textContent = state.latestSummary || "Waiting for your first recap.";
  renderKeywordBadges(state.latestKeywords);
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
  consentCopyNode.textContent =
    `Audio for this lecture will be processed via ${host.getConsentProviderLabel()}. No lecture data is shared without your consent.`;
  consentModalNode.classList.remove("hidden");
}

function closeConsentModal() {
  pendingSessionStart = false;
  consentModalNode.classList.add("hidden");
}

async function syncState() {
  extensionState = await host.getState();
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
  extensionState = await host.startSession({ mode: "cloud", language: "English", recap_length: "standard" });
  pendingSessionStart = false;
  consentModalNode.classList.add("hidden");
  renderState();
  await refreshTranscript();
});

document.getElementById("start-capture").addEventListener("click", async () => {
  await host.startCapture();
  await syncState();
});

document.getElementById("stop-capture").addEventListener("click", async () => {
  await host.stopCapture();
  await syncState();
});

document.getElementById("leave").addEventListener("click", async () => {
  extensionState = await host.setDeparture();
  renderState();
});

document.getElementById("catch-up").addEventListener("click", async () => {
  extensionState = await host.requestRecap();
  renderState();
  await refreshTranscript();
});

window.addEventListener("message", async (event) => {
  if (event.data?.type === "HOTKEY_CATCH_ME_UP") {
    document.getElementById("catch-up").click();
  }
});

host.subscribe((message) => {
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
