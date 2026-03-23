import { NotebookText, Play, Square } from "lucide-react";

type SessionControlsProps = {
  canStart: boolean;
  canEnd: boolean;
  onStart: () => void;
  onEnd: () => void;
  onExportPdf: () => void;
  onExportMarkdown: () => void;
  onExportNotion: () => void;
};

function SessionControls(props: SessionControlsProps) {
  const { canStart, canEnd, onStart, onEnd, onExportPdf, onExportMarkdown, onExportNotion } = props;

  return (
    <section className="rounded-[24px] bg-mist p-4 dark:bg-slate-800">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Session Controls</h2>
        <NotebookText size={16} />
      </div>
      <div className="mt-3 flex gap-2">
        <button className="flex flex-1 items-center justify-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={onStart} disabled={!canStart}>
          <Play size={14} /> Start Session
        </button>
        <button className="flex flex-1 items-center justify-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={onEnd} disabled={!canEnd}>
          <Square size={14} /> End Session
        </button>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <button className="rounded-full border border-ink/15 px-3 py-2 text-[11px] font-semibold" onClick={onExportPdf} disabled={!canEnd}>
          Export PDF
        </button>
        <button className="rounded-full border border-ink/15 px-3 py-2 text-[11px] font-semibold" onClick={onExportMarkdown} disabled={!canEnd}>
          Markdown
        </button>
        <button className="rounded-full border border-ink/15 px-3 py-2 text-[11px] font-semibold" onClick={onExportNotion} disabled={!canEnd}>
          Notion
        </button>
      </div>
    </section>
  );
}

export default SessionControls;
