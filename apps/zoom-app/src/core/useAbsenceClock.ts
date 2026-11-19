import { useEffect, useMemo, useState } from "react";

/**
 * Tracks how long the user has been away since `departureTimestamp`.
 * Ticks once per second only while a departure is active.
 */
export function useAbsenceClock(departureTimestamp: string | null): number {
  const [nowMs, setNowMs] = useState(Date.now());

  useEffect(() => {
    if (!departureTimestamp) return;
    const interval = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [departureTimestamp]);

  return useMemo(() => {
    if (!departureTimestamp) return 0;
    return Math.max(0, Math.floor((nowMs - new Date(departureTimestamp).getTime()) / 1000));
  }, [departureTimestamp, nowMs]);
}
