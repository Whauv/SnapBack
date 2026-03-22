import type { Mode } from "../types";

type ConsentBannerProps = {
  mode: Mode;
  accepted: boolean;
  onAccept: () => void;
};

function ConsentBanner({ mode, accepted, onAccept }: ConsentBannerProps) {
  if (accepted) return null;

  return (
    <section className="rounded-[24px] border border-accent/20 bg-accent/10 p-4 text-sm">
      <p className="font-semibold">Consent required</p>
      <p className="mt-2 leading-6 text-ink/80">
        SnapBack is now transcribing this session. Audio is processed via {mode === "cloud" ? "AssemblyAI" : "Local Whisper"}.
        No data is shared without your consent.
      </p>
      <button className="mt-3 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={onAccept}>
        I Understand
      </button>
    </section>
  );
}

export default ConsentBanner;
