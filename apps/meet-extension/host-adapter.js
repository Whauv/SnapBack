const API_BASE = "http://localhost:8000";

async function sendRuntimeMessage(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (!response?.ok) {
    throw new Error(response?.error || "Extension host request failed");
  }
  return response;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab || null;
}

async function getTranscript(sessionId) {
  const response = await fetch(`${API_BASE}/session/${sessionId}/transcript`);
  if (!response.ok) {
    throw new Error(`Transcript request failed with status ${response.status}`);
  }
  return response.json();
}

export function createMeetExtensionHostAdapter() {
  return {
    kind: "google-meet-extension",
    label: "Google Meet Extension",
    capabilities: {
      nativeMeetingContext: true,
      nativeAudioCapture: true,
      globalHotkey: true,
      transcriptOverlay: true,
    },
    async getMeetingContext() {
      const tab = await getActiveTab();
      return {
        host: "google-meet-extension",
        label: "Google Meet Extension",
        surface: "meeting-side-panel",
        meetingTitle: tab?.title || "Google Meet",
      };
    },
    getConsentProviderLabel() {
      return "AssemblyAI tab audio capture";
    },
    async getState() {
      const response = await sendRuntimeMessage({ type: "GET_EXTENSION_STATE" });
      return response.state;
    },
    async getTranscript(sessionId) {
      return getTranscript(sessionId);
    },
    async startSession(payload) {
      const response = await sendRuntimeMessage({ type: "START_SESSION", payload });
      return response.state;
    },
    async startCapture(tabId) {
      const resolvedTabId = tabId || (await getActiveTab())?.id;
      if (!resolvedTabId) {
        throw new Error("Missing tab id for capture");
      }
      return sendRuntimeMessage({ type: "START_TAB_CAPTURE", tabId: resolvedTabId });
    },
    async stopCapture() {
      return sendRuntimeMessage({ type: "STOP_TAB_CAPTURE" });
    },
    async setDeparture() {
      const response = await sendRuntimeMessage({ type: "SET_DEPARTURE" });
      return response.state;
    },
    async requestRecap() {
      const response = await sendRuntimeMessage({ type: "REQUEST_RECAP" });
      return response.state;
    },
    async openPanel(tabId) {
      const resolvedTabId = tabId || (await getActiveTab())?.id;
      if (!resolvedTabId) {
        throw new Error("Missing tab id for panel");
      }
      return chrome.tabs.sendMessage(resolvedTabId, { type: "OPEN_SNAPBACK_PANEL" });
    },
    subscribe(listener) {
      const handler = (message) => {
        if (message.type === "EXTENSION_STATE" || message.type === "HOTKEY_CATCH_ME_UP") {
          listener(message);
        }
      };
      chrome.runtime.onMessage.addListener(handler);
      return () => chrome.runtime.onMessage.removeListener(handler);
    },
  };
}
