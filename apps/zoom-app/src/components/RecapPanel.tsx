import type { Recap } from "../types";
import { formatDuration, formatTimestamp } from "../utils";

type RecapPanelProps = {
  canLeave: boolean;
  canCatchUp: boolean;
  absenceSeconds: number;
  latestRecap: Recap | null;
  onLeave: () => void;
  onCatchUp: () => void;
};

function RecapPanel({ canLeave, canCatchUp, absenceSeconds, latestRecap, onLeave, onCatchUp }: RecapPanelProps) {
  return (
    <section className="rounded-[24px] border border-amber/40 bg-white p-4 dark:border-amber/30 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Recap Panel</h2>
        {canCatchUp ? (
          <span className="rounded-full bg-amber px-3 py-1 text-xs font-semibold text-ink">
            Away {formatDuration(absenceSeconds)}
          </span>
        ) : null}
      </div>
      <div className="mt-3 flex gap-2">
        <button className="flex-1 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={onLeave} disabled={!canLeave}>
          I&apos;m Leaving
        </button>
        <button className="flex-1 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={onCatchUp} disabled={!canCatchUp}>
          I&apos;m Back - Catch Me Up
        </button>
      </div>

      {latestRecap ? (
        <div className="mt-4 rounded-[22px] bg-mist p-4 dark:bg-slate-800">
          {latestRecap.topic_shift_detected ? (
            <div className="mb-3 rounded-2xl bg-amber/85 px-3 py-2 text-xs font-semibold text-ink">
              ⚠ Topic changed while you were away
            </div>
          ) : null}
          {latestRecap.missed_alerts.length ? (
            <div className="mb-3 space-y-2">
              {latestRecap.missed_alerts.map((alert) => (
                <div key={`${alert.timestamp}-${alert.text}`} className="rounded-2xl bg-danger px-3 py-2 text-xs font-semibold text-white">
                  Professor alert at {formatTimestamp(alert.timestamp)}: {alert.text}
                </div>
              ))}
            </div>
          ) : null}
          <p className="text-[11px] uppercase tracking-[0.2em] text-ink/50 dark:text-slate-400">
            {formatTimestamp(latestRecap.from_timestamp)} - {formatTimestamp(latestRecap.to_timestamp)}
          </p>
          <p className="mt-2 text-sm leading-6">{latestRecap.summary}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {latestRecap.keywords.map((keyword) => (
              <span key={keyword} className="rounded-full bg-white px-3 py-1 text-xs font-medium text-ink dark:bg-slate-700 dark:text-slate-100">
                {keyword}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-4 text-sm text-ink/65 dark:text-slate-400">
          Press &quot;I&apos;m Leaving&quot; before you step away, then come back to generate a targeted recap.
        </p>
      )}
    </section>
  );
}

export default RecapPanel;
