const API_BASE = "http://localhost:8000";
const STORAGE_KEY = "snapbackExtensionState";
const CHUNK_INTERVAL_MS = 4000;

const defaultState = {
  sessionId: null,
  departureTimestamp: null,
  latestSummary: "",
  latestKeywords: [],
  captureStatus: "idle",
  recordingTabId: null,
  chunkIndex: 0,
  lastError: "",
  transcriptCount: 0,
};

let state = { ...defaultState };
let mediaRecorder = null;
let capturedStream = null;
let statusPollInterval = null;

async function loadState() {
  const stored = await chrome.storage.local.get(STORAGE_KEY);
  state = { ...defaultState, ...(stored[STORAGE_KEY] || {}) };
}

async function persistState() {
  await chrome.storage.local.set({ [STORAGE_KEY]: state });
}

async function broadcastState() {
  await persistState();
  chrome.runtime.sendMessage({ type: "EXTENSION_STATE", state }).catch(() => {});
}

async function getActiveMeetTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true, url: ["https://meet.google.com/*"] });
  return tabs[0] || null;
}

async function openSnapBackPanel(tabId) {
  if (!tabId) return;
  await chrome.tabs.sendMessage(tabId, { type: "OPEN_SNAPBACK_PANEL" }).catch(() => {});
}

async function ensureSessionTranscriptCount() {
  if (!state.sessionId) return;
  try {
    const response = await fetch(`${API_BASE}/session/${state.sessionId}/transcript`);
    if (!response.ok) return;
    const data = await response.json();
    state.transcriptCount = Array.isArray(data.transcript) ? data.transcript.length : 0;
    await broadcastState();
  } catch (error) {
    console.error("Failed to refresh transcript count", error);
  }
}

function stopPolling() {
  if (statusPollInterval) {
    clearInterval(statusPollInterval);
    statusPollInterval = null;
  }
}

function startPolling() {
  stopPolling();
  statusPollInterval = setInterval(() => {
    void ensureSessionTranscriptCount();
  }, 5000);
}

async function postAudioChunk(base64Audio, mimeType) {
  if (!state.sessionId) return;
  state.chunkIndex += 1;
  const response = await fetch(`${API_BASE}/session/audio-chunk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: state.sessionId,
      chunk_index: state.chunkIndex,
      mime_type: mimeType,
      audio_base64: base64Audio,
      timestamp: new Date().toISOString(),
      source: "chrome-extension",
    }),
  });
  if (!response.ok) {
    throw new Error(`Audio relay failed with status ${response.status}`);
  }
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Failed to convert blob"));
        return;
      }
      resolve(result.split(",")[1] || "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function stopCapture() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  mediaRecorder = null;
  if (capturedStream) {
    capturedStream.getTracks().forEach((track) => track.stop());
  }
  capturedStream = null;
  state.captureStatus = "idle";
  state.recordingTabId = null;
  await broadcastState();
}

async function startCapture(tabId) {
  await stopCapture();
  return new Promise((resolve) => {
    chrome.tabCapture.capture({ audio: true, video: false, targetTabId: tabId }, async (stream) => {
      if (chrome.runtime.lastError || !stream) {
        state.captureStatus = "error";
        state.lastError = chrome.runtime.lastError?.message || "Unable to capture tab audio";
        await broadcastState();
        resolve({ ok: false, error: state.lastError });
        return;
      }

      capturedStream = stream;
      mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorder.ondataavailable = async (event) => {
        if (!event.data || !event.data.size) return;
        try {
          const base64Audio = await blobToBase64(event.data);
          await postAudioChunk(base64Audio, mediaRecorder.mimeType || "audio/webm");
          await ensureSessionTranscriptCount();
        } catch (error) {
          console.error("Failed to relay audio chunk", error);
          state.lastError = String(error);
          await broadcastState();
        }
      };
      mediaRecorder.onstop = async () => {
        state.captureStatus = "idle";
        await broadcastState();
      };
      mediaRecorder.start(CHUNK_INTERVAL_MS);

      state.captureStatus = "capturing";
      state.recordingTabId = tabId;
      state.lastError = "";
      await broadcastState();
      resolve({ ok: true });
    });
  });
}

async function startSession(payload) {
  const response = await fetch(`${API_BASE}/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode: payload?.mode || "cloud",
      language: payload?.language || "English",
      recap_length: payload?.recap_length || "standard",
    }),
  });
  if (!response.ok) {
    throw new Error(`Session start failed with status ${response.status}`);
  }
  const data = await response.json();
  state.sessionId = data.session_id;
  state.latestSummary = "";
  state.latestKeywords = [];
  state.departureTimestamp = null;
  state.chunkIndex = 0;
  state.lastError = "";
  await ensureSessionTranscriptCount();
  await broadcastState();
  startPolling();
  return data;
}

async function requestRecap() {
  if (!state.sessionId || !state.departureTimestamp) {
    throw new Error("Missing session or departure timestamp");
  }

  const response = await fetch(`${API_BASE}/recap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: state.sessionId,
      from_timestamp: state.departureTimestamp,
      to_timestamp: new Date().toISOString(),
    }),
  });
  if (!response.ok) {
    throw new Error(`Recap request failed with status ${response.status}`);
  }
  const data = await response.json();
  state.latestSummary = data.summary || "";
  state.latestKeywords = data.keywords || [];
  state.departureTimestamp = null;
  await ensureSessionTranscriptCount();
  await broadcastState();
  return data;
}

chrome.runtime.onInstalled.addListener(() => {
  void loadState().then(broadcastState);
});

chrome.runtime.onStartup.addListener(() => {
  void loadState().then(() => {
    if (state.sessionId) startPolling();
    return broadcastState();
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  void (async () => {
    try {
      if (message.type === "GET_EXTENSION_STATE") {
        await loadState();
        sendResponse({ ok: true, state });
        return;
      }

      if (message.type === "START_SESSION") {
        const data = await startSession(message.payload);
        sendResponse({ ok: true, data, state });
        return;
      }

      if (message.type === "SET_DEPARTURE") {
        state.departureTimestamp = new Date().toISOString();
        await broadcastState();
        sendResponse({ ok: true, state });
        return;
      }

      if (message.type === "REQUEST_RECAP") {
        const data = await requestRecap();
        sendResponse({ ok: true, data, state });
        return;
      }

      if (message.type === "START_TAB_CAPTURE") {
        const tabId = message.tabId || sender.tab?.id;
        if (!tabId) throw new Error("Missing tab id for capture");
        const result = await startCapture(tabId);
        sendResponse(result);
        return;
      }

      if (message.type === "STOP_TAB_CAPTURE") {
        await stopCapture();
        sendResponse({ ok: true, state });
        return;
      }

      if (message.type === "OPEN_LECTURELENS_PANEL") {
        const tabId = sender.tab?.id || message.tabId;
        await openSnapBackPanel(tabId);
        sendResponse({ ok: true });
        return;
      }

      if (message.type === "OPEN_SNAPBACK_PANEL") {
        sendResponse({ ok: true });
        return;
      }

      sendResponse({ ok: false, error: "Unknown message type" });
    } catch (error) {
      state.lastError = error instanceof Error ? error.message : String(error);
      await broadcastState();
      sendResponse({ ok: false, error: state.lastError });
    }
  })();

  return true;
});

chrome.commands.onCommand.addListener((command) => {
  void (async () => {
    if (command !== "catch-me-up") return;
    const activeMeetTab = await getActiveMeetTab();
    if (activeMeetTab?.id) {
      await openSnapBackPanel(activeMeetTab.id);
    }

    if (state.sessionId && state.departureTimestamp) {
      try {
        await requestRecap();
      } catch (error) {
        state.lastError = error instanceof Error ? error.message : String(error);
        await broadcastState();
      }
      return;
    }

    chrome.runtime.sendMessage({ type: "HOTKEY_CATCH_ME_UP" }).catch(() => {});
  })();
});
