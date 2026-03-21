const API_BASE = "http://localhost:8000";

document.getElementById("open-sidepanel").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  await chrome.tabs.sendMessage(tab.id, { type: "OPEN_LECTURELENS_PANEL" });
});

document.getElementById("quick-recap").addEventListener("click", async () => {
  const { sessionId, departureTimestamp } = await chrome.storage.local.get(["sessionId", "departureTimestamp"]);
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
  document.getElementById("status").textContent = data.summary || "Recap generated";
});
