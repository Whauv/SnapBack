import assert from "node:assert/strict";
import { test } from "node:test";

// Smoke-tests the background service worker's message router by capturing the
// onMessage listener it registers at import time, then invoking it directly.
// The listener is registered once per module load, so both assertions share one
// import.

function invoke(listener, message) {
  return new Promise((resolve) => {
    listener(message, {}, resolve);
  });
}

test("background message router handles known and unknown messages", async () => {
  const store = {};
  let messageListener = null;
  global.chrome = {
    runtime: {
      onInstalled: { addListener() {} },
      onStartup: { addListener() {} },
      onMessage: { addListener(fn) { messageListener = fn; } },
      sendMessage: async () => ({}),
    },
    commands: { onCommand: { addListener() {} } },
    storage: {
      local: {
        async get(key) { return key ? { [key]: store[key] } : { ...store }; },
        async set(obj) { Object.assign(store, obj); },
      },
    },
    tabs: { async query() { return []; }, async sendMessage() { return {}; } },
  };

  await import("../../../apps/meet-extension/src/background.js");
  assert.equal(typeof messageListener, "function");

  const ok = await invoke(messageListener, { type: "GET_EXTENSION_STATE" });
  assert.equal(ok.ok, true);
  assert.ok(ok.state);
  assert.equal(ok.state.sessionId, null);

  const unknown = await invoke(messageListener, { type: "NOPE" });
  assert.equal(unknown.ok, false);
  assert.match(unknown.error, /Unknown message type/);

  delete global.chrome;
});
