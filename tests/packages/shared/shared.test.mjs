import assert from "node:assert/strict";
import { test } from "node:test";

import { buildConsentCopy, formatDuration, formatTimestamp } from "../../../packages/shared/src/index.js";

test("formatDuration pads hours, minutes, and seconds", () => {
  assert.equal(formatDuration(0), "00:00:00");
  assert.equal(formatDuration(3661), "01:01:01");
  assert.equal(formatDuration(59), "00:00:59");
});

test("formatTimestamp returns a placeholder for empty input", () => {
  assert.equal(formatTimestamp(null), "Not set");
  assert.equal(formatTimestamp(undefined), "Not set");
  assert.equal(formatTimestamp(""), "Not set");
});

test("buildConsentCopy embeds the provider label", () => {
  const copy = buildConsentCopy("AssemblyAI");
  assert.match(copy, /AssemblyAI/);
  assert.match(copy, /without your consent/);
});

test("extension copy stays in sync with the shared source", async () => {
  const shared = await import("../../../packages/shared/src/formatters.js");
  const copied = await import("../../../apps/meet-extension/src/shared/formatters.js");
  assert.equal(copied.formatDuration(3661), shared.formatDuration(3661));
  assert.equal(copied.formatTimestamp(null), shared.formatTimestamp(null));
});
