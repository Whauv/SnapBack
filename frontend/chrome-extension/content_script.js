(() => {
  if (document.getElementById("lecturelens-root")) {
    return;
  }

  const root = document.createElement("div");
  root.id = "lecturelens-root";

  const button = document.createElement("button");
  button.id = "lecturelens-pill";
  button.textContent = "LectureLens";

  let frame = null;

  function togglePanel(forceOpen) {
    const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : !frame;
    if (!shouldOpen) {
      frame?.remove();
      frame = null;
      return;
    }
    if (frame) return;
    frame = document.createElement("iframe");
    frame.id = "lecturelens-frame";
    frame.src = chrome.runtime.getURL("sidepanel.html");
    document.body.appendChild(frame);
  }

  button.addEventListener("click", () => togglePanel());

  root.appendChild(button);
  document.body.appendChild(root);

  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "OPEN_LECTURELENS_PANEL") {
      togglePanel(true);
    }
    if (message.type === "HOTKEY_CATCH_ME_UP") {
      togglePanel(true);
      frame?.contentWindow?.postMessage({ type: "HOTKEY_CATCH_ME_UP" }, "*");
    }
  });
})();
