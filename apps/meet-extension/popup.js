import { createMeetExtensionHostAdapter } from "./host-adapter.js";

const statusNode = document.getElementById("status");
const captureButton = document.getElementById("toggle-capture");
const host = createMeetExtensionHostAdapter();

function renderState(state) {
  const session = state.sessionId ? `Session: ${state.sessionId.slice(0, 8)}` : "Session inactive";
  const capture = `Capture: ${state.captureStatus || "idle"}`;
  const away = state.departureTimestamp ? `Away since: ${new Date(state.departureTimestamp).toLocaleTimeString()}` : "Present";
  statusNode.textContent = [session, capture, away].join("\n");
  captureButton.textContent = state.captureStatus === "capturing" ? "Stop Tab Audio" : "Start Tab Audio";
}

document.getElementById("open-sidepanel").addEventListener("click", async () => {
  await host.openPanel();
});

document.getElementById("quick-recap").addEventListener("click", async () => {
  const state = await host.requestRecap();
  renderState(state);
});

captureButton.addEventListener("click", async () => {
  const state = await host.getState();
  if (state.captureStatus === "capturing") {
    await host.stopCapture();
  } else {
    await host.startCapture();
  }
  renderState(await host.getState());
});

host.subscribe((message) => {
  if (message.type === "EXTENSION_STATE") {
    renderState(message.state);
  }
});

void host.getState().then(renderState);
