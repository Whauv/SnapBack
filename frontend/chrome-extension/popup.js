const statusNode = document.getElementById("status");
const captureButton = document.getElementById("toggle-capture");

async function getState() {
  const response = await chrome.runtime.sendMessage({ type: "GET_EXTENSION_STATE" });
  return response.state;
}

function renderState(state) {
  const session = state.sessionId ? `Session: ${state.sessionId.slice(0, 8)}` : "Session inactive";
  const capture = `Capture: ${state.captureStatus || "idle"}`;
  const away = state.departureTimestamp ? `Away since: ${new Date(state.departureTimestamp).toLocaleTimeString()}` : "Present";
  statusNode.textContent = [session, capture, away].join("\n");
  captureButton.textContent = state.captureStatus === "capturing" ? "Stop Tab Audio" : "Start Tab Audio";
}

document.getElementById("open-sidepanel").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  await chrome.tabs.sendMessage(tab.id, { type: "OPEN_LECTURELENS_PANEL" });
});

document.getElementById("quick-recap").addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ type: "REQUEST_RECAP" });
  renderState(response.state);
});

captureButton.addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  const state = await getState();
  if (state.captureStatus === "capturing") {
    await chrome.runtime.sendMessage({ type: "STOP_TAB_CAPTURE" });
  } else {
    await chrome.runtime.sendMessage({ type: "START_TAB_CAPTURE", tabId: tab.id });
  }
  renderState(await getState());
});

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "EXTENSION_STATE") {
    renderState(message.state);
  }
});

void getState().then(renderState);
