const API_BASE = "http://localhost:8000";

let currentSessionId = null;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SET_SESSION_ID") {
    currentSessionId = message.sessionId;
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === "TRANSCRIPT_CHUNK" && currentSessionId) {
    fetch(`${API_BASE}/session/transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        text: message.text,
        timestamp: new Date().toISOString()
      })
    }).catch((error) => console.error("Failed to send transcript chunk", error));
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === "START_TAB_CAPTURE") {
    chrome.tabCapture.capture({ audio: true, video: false }, (stream) => {
      if (!stream) {
        sendResponse({ ok: false, error: "Unable to capture tab audio" });
        return;
      }
      sendResponse({ ok: true });
    });
    return true;
  }

  return false;
});

chrome.commands.onCommand.addListener((command) => {
  if (command === "catch-me-up") {
    chrome.runtime.sendMessage({ type: "HOTKEY_CATCH_ME_UP" });
  }
});
