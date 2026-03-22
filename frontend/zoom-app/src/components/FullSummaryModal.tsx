type FullSummaryModalProps = {
  open: boolean;
  summary: string;
  onClose: () => void;
};

function FullSummaryModal({ open, summary, onClose }: FullSummaryModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/45 px-4">
      <div className="w-full max-w-[288px] rounded-[28px] bg-white p-5 shadow-soft dark:bg-slate-900">
        <p className="text-xs uppercase tracking-[0.24em] text-ink/55 dark:text-slate-400">Session Ended</p>
        <h2 className="mt-2 text-lg font-semibold">Full Lecture Summary</h2>
        <p className="mt-3 text-sm leading-6 text-ink/80 dark:text-slate-300">
          {summary || "No full summary is available yet."}
        </p>
        <button className="mt-5 w-full rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}

export default FullSummaryModal;
