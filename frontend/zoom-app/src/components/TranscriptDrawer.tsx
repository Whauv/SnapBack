import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useEffect, useRef } from "react";
import type { TranscriptChunk } from "../types";
import { formatTimestamp } from "../utils";

type TranscriptDrawerProps = {
  open: boolean;
  transcript: TranscriptChunk[];
  onToggle: () => void;
};

function TranscriptDrawer({ open, transcript, onToggle }: TranscriptDrawerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [transcript, open]);

  return (
    <aside className={`border-l border-ink/10 bg-white/70 dark:bg-slate-950 ${open ? "w-[140px]" : "w-[52px]"}`}>
      <button className="m-2 rounded-full border border-ink/10 p-2" onClick={onToggle}>
        {open ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
      </button>
      {open ? (
        <div className="px-3 pb-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/60 dark:text-slate-400">Live Transcript</h2>
          <div ref={containerRef} className="mt-3 max-h-[80vh] space-y-2 overflow-y-auto pr-1">
            {transcript.length ? (
              transcript.map((entry) => (
                <article key={entry.id} className="rounded-[18px] bg-mist p-2 text-xs dark:bg-slate-800">
                  <p className="font-semibold text-ink/60 dark:text-slate-400">{formatTimestamp(entry.timestamp)}</p>
                  <p className="mt-1 leading-5">{entry.text}</p>
                </article>
              ))
            ) : (
              <p className="text-xs text-ink/60 dark:text-slate-400">Waiting for transcript data.</p>
            )}
          </div>
        </div>
      ) : null}
    </aside>
  );
}

export default TranscriptDrawer;
