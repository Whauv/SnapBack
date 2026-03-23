import type { Recap } from "../types";
import { formatTimestamp } from "../utils";

type RecapHistoryProps = {
  recaps: Recap[];
};

function RecapHistory({ recaps }: RecapHistoryProps) {
  return (
    <section className="rounded-[24px] bg-mist p-4 dark:bg-slate-800">
      <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Recap History</h2>
      <div className="mt-3 space-y-3">
        {recaps.length ? (
          recaps.map((recap) => (
            <article key={recap.id} className="rounded-[20px] bg-white p-3 text-sm dark:bg-slate-900">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/55 dark:text-slate-400">
                {formatTimestamp(recap.from_timestamp)} - {formatTimestamp(recap.to_timestamp)}
              </p>
              <p className="mt-2 leading-6">{recap.summary}</p>
            </article>
          ))
        ) : (
          <p className="text-sm text-ink/65 dark:text-slate-400">No recap history yet.</p>
        )}
      </div>
    </section>
  );
}

export default RecapHistory;
