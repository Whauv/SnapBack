(() => {
  if (document.getElementById("lecturelens-root")) {
    return;
  }

  const root = document.createElement("div");
  root.id = "lecturelens-root";

  const button = document.createElement("button");
  button.id = "lecturelens-pill";
  button.textContent = "🎓 LectureLens";

  let frame = null;
  button.addEventListener("click", () => {
    if (frame) {
      frame.remove();
      frame = null;
      return;
    }
    frame = document.createElement("iframe");
    frame.id = "lecturelens-frame";
    frame.src = chrome.runtime.getURL("sidepanel.html");
    document.body.appendChild(frame);
  });

  root.appendChild(button);
  document.body.appendChild(root);

  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "OPEN_LECTURELENS_PANEL") {
      button.click();
    }
  });
})();
