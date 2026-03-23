type ConsentBannerProps = {
  providerLabel: string;
  open: boolean;
  accepted: boolean;
  onAccept: () => void;
  onClose: () => void;
};

function ConsentBanner({ providerLabel, open, accepted, onAccept, onClose }: ConsentBannerProps) {
  if (accepted || !open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 px-4 backdrop-blur-sm">
      <section className="w-full max-w-[296px] rounded-[28px] bg-white p-5 text-sm shadow-soft dark:bg-slate-900">
        <p className="text-xs uppercase tracking-[0.24em] text-ink/55 dark:text-slate-400">Consent Required</p>
        <h2 className="mt-2 text-lg font-semibold">SnapBack is ready to transcribe</h2>
        <p className="mt-3 leading-6 text-ink/80 dark:text-slate-300">
          Audio for this lecture will be processed via {providerLabel}. No lecture data is shared without your consent.
        </p>
        <div className="mt-4 flex gap-2">
          <button
            className="flex-1 rounded-full border border-ink/15 px-4 py-2 font-semibold dark:border-slate-700"
            onClick={onClose}
          >
            Cancel
          </button>
          <button className="flex-1 rounded-full bg-accent px-4 py-2 font-semibold text-white" onClick={onAccept}>
            I Understand
          </button>
        </div>
      </section>
    </div>
  );
}

export default ConsentBanner;
