import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createBackendRecap,
  getBackendSessionTranscript,
  startBackendSession,
} from "./backendClient";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

describe("backendClient", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends a bearer token and parses JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ session_id: "s1", start_timestamp: "t", session: {} }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await startBackendSession("cloud", "English", "standard");

    expect(result.session_id).toBe("s1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/session/start");
    expect((init.headers as Record<string, string>).Authorization).toMatch(/^Bearer /);
    expect(JSON.parse(init.body)).toEqual({ mode: "cloud", language: "English", recap_length: "standard" });
    vi.unstubAllGlobals();
  });

  it("maps 401 to an auth error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 401)));
    await expect(getBackendSessionTranscript("s1")).rejects.toThrow(/authentication failed/i);
    vi.unstubAllGlobals();
  });

  it("maps 429 to a rate-limit error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 429)));
    await expect(getBackendSessionTranscript("s1")).rejects.toThrow(/rate limited/i);
    vi.unstubAllGlobals();
  });

  it("maps a network failure to a friendly error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));
    await expect(
      createBackendRecap("s1", "2026-04-07T10:00:00+00:00", "2026-04-07T10:05:00+00:00"),
    ).rejects.toThrow(/Unable to reach the SnapBack API/i);
    vi.unstubAllGlobals();
  });
});
