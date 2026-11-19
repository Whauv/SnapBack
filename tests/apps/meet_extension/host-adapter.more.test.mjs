import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

const MODULE = "../../../apps/meet-extension/src/host-adapter.js";

function stubChrome({ sendMessage, tabs } = {}) {
  global.chrome = {
    storage: { local: { async get() { return { snapbackExtensionState: { apiToken: "tok" } }; } } },
    runtime: {
      sendMessage: sendMessage ?? (async () => ({ ok: true, state: {} })),
      onMessage: { addListener() {}, removeListener() {} },
    },
    tabs: {
      async query() { return tabs ?? [{ id: 1, title: "Google Meet" }]; },
      async sendMessage() { return { ok: true }; },
    },
  };
}

afterEach(() => {
  delete global.chrome;
  delete global.fetch;
});

test("getTranscript throws on a non-ok response", async () => {
  stubChrome();
  global.fetch = async () => ({ ok: false, status: 500, async json() { return {}; } });
  const { createMeetExtensionHostAdapter } = await import(MODULE);
  await assert.rejects(() => createMeetExtensionHostAdapter().getTranscript("s1"), /status 500/);
});

test("getTranscript surfaces a friendly error on network failure", async () => {
  stubChrome();
  global.fetch = async () => { throw new TypeError("network down"); };
  const { createMeetExtensionHostAdapter } = await import(MODULE);
  await assert.rejects(() => createMeetExtensionHostAdapter().getTranscript("s1"), /Unable to reach the SnapBack API/);
});

test("getState returns the state from the runtime message", async () => {
  stubChrome({ sendMessage: async () => ({ ok: true, state: { sessionId: "abc" } }) });
  const { createMeetExtensionHostAdapter } = await import(MODULE);
  const state = await createMeetExtensionHostAdapter().getState();
  assert.deepEqual(state, { sessionId: "abc" });
});

test("runtime message failures reject with the reported error", async () => {
  stubChrome({ sendMessage: async () => ({ ok: false, error: "boom" }) });
  const { createMeetExtensionHostAdapter } = await import(MODULE);
  await assert.rejects(() => createMeetExtensionHostAdapter().startSession({ mode: "cloud" }), /boom/);
});

test("getMeetingContext reports the active tab title", async () => {
  stubChrome({ tabs: [{ id: 7, title: "Linear Algebra Lecture" }] });
  const { createMeetExtensionHostAdapter } = await import(MODULE);
  const context = await createMeetExtensionHostAdapter().getMeetingContext();
  assert.equal(context.meetingTitle, "Linear Algebra Lecture");
  assert.equal(context.host, "google-meet-extension");
});
