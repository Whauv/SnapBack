import test from "node:test";
import assert from "node:assert/strict";

test("meet extension host adapter sends bearer token for transcript fetches", async () => {
  let observedHeaders = null;

  global.chrome = {
    storage: {
      local: {
        async get() {
          return { snapbackExtensionState: { apiToken: "token-from-storage" } };
        },
      },
    },
    runtime: {
      async sendMessage() {
        return { ok: true, state: {} };
      },
      onMessage: {
        addListener() {},
        removeListener() {},
      },
    },
    tabs: {
      async query() {
        return [{ id: 1, title: "Google Meet" }];
      },
      async sendMessage() {
        return { ok: true };
      },
    },
  };

  global.fetch = async (_url, init) => {
    observedHeaders = init?.headers ?? null;
    return {
      ok: true,
      async json() {
        return { session: {}, transcript: [], recaps: [] };
      },
    };
  };

  const { createMeetExtensionHostAdapter } = await import("./host-adapter.js");
  const host = createMeetExtensionHostAdapter();
  const transcript = await host.getTranscript("session-123");

  assert.deepEqual(transcript, { session: {}, transcript: [], recaps: [] });
  assert.equal(observedHeaders.Authorization, "Bearer token-from-storage");

  delete global.fetch;
  delete global.chrome;
});
