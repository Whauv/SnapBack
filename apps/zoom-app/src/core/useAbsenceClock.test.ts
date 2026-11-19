import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAbsenceClock } from "./useAbsenceClock";

describe("useAbsenceClock", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns 0 when there is no departure", () => {
    const { result } = renderHook(() => useAbsenceClock(null));
    expect(result.current).toBe(0);
  });

  it("counts seconds since departure and ticks over time", () => {
    const fiveSecondsAgo = new Date(Date.now() - 5000).toISOString();
    const { result } = renderHook(() => useAbsenceClock(fiveSecondsAgo));
    expect(result.current).toBe(5);

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current).toBe(7);
  });

  it("resets to 0 when departure is cleared", () => {
    const start = new Date(Date.now() - 3000).toISOString();
    const { result, rerender } = renderHook(({ ts }: { ts: string | null }) => useAbsenceClock(ts), {
      initialProps: { ts: start as string | null },
    });
    expect(result.current).toBe(3);
    rerender({ ts: null });
    expect(result.current).toBe(0);
  });
});
