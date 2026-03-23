import type { StudyPack } from "../types";

type StudyPackPanelProps = {
  canGenerate: boolean;
  loading: boolean;
  studyPack: StudyPack | null;
  onGenerate: () => void;
};

function StudyPackPanel({ canGenerate, loading, studyPack, onGenerate }: StudyPackPanelProps) {
  return (
    <section className="rounded-[24px] bg-mist p-4 dark:bg-slate-800">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Study Pack</h2>
        <button
          className="rounded-full bg-accent px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
          onClick={onGenerate}
          disabled={!canGenerate || loading}
        >
          {loading ? "Building..." : "Generate"}
        </button>
      </div>

      {studyPack ? (
        <div className="mt-4 space-y-4 text-sm">
          <div className="rounded-[20px] bg-white p-3 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/55 dark:text-slate-400">Outline</p>
            <ul className="mt-2 list-disc space-y-2 pl-5">
              {studyPack.outline.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="rounded-[20px] bg-white p-3 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/55 dark:text-slate-400">Flashcards</p>
            <div className="mt-2 space-y-3">
              {studyPack.flashcards.map((card) => (
                <article key={card.question} className="rounded-2xl border border-ink/10 p-3 dark:border-slate-700">
                  <p className="font-semibold">{card.question}</p>
                  <p className="mt-2 text-ink/75 dark:text-slate-300">{card.answer}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-[20px] bg-white p-3 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/55 dark:text-slate-400">Quiz Questions</p>
            <div className="mt-2 space-y-3">
              {studyPack.quiz_questions.map((item) => (
                <article key={item.question} className="rounded-2xl border border-ink/10 p-3 dark:border-slate-700">
                  <p className="font-semibold">{item.question}</p>
                  <p className="mt-2"><span className="font-semibold">Answer:</span> {item.answer}</p>
                  <p className="mt-1 text-ink/75 dark:text-slate-300">{item.explanation}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-[20px] bg-white p-3 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/55 dark:text-slate-400">Review Priorities</p>
            <ul className="mt-2 list-disc space-y-2 pl-5">
              {studyPack.review_priorities.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <p className="mt-4 text-sm text-ink/65 dark:text-slate-400">
          Generate a study pack to turn this lecture into an outline, flashcards, quiz questions, and review priorities.
        </p>
      )}
    </section>
  );
}

export default StudyPackPanel;
