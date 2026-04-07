import { Moon } from "lucide-react";
import { exportSessionFile } from "./api";
import { useSnapBackPanel } from "./core/useSnapBackPanel";
import ConsentBanner from "./components/ConsentBanner";
import FullSummaryModal from "./components/FullSummaryModal";
import RecapHistory from "./components/RecapHistory";
import RecapPanel from "./components/RecapPanel";
import SessionControls from "./components/SessionControls";
import SettingsPanel from "./components/SettingsPanel";
import StudyPackPanel from "./components/StudyPackPanel";
import TranscriptDrawer from "./components/TranscriptDrawer";
import { exportMarkdownNotes, exportPdfNotes } from "./exporters";
import { createZoomHostAdapter } from "./hosts";
import { formatTimestamp } from "./utils";

const host = createZoomHostAdapter();

function App() {
  const panel = useSnapBackPanel({ host, settingsStorageKey: `snapback.${host.kind}.settings` });

  async function handleExportPdf() {
    if (!panel.sessionId) return;
    try {
      await exportSessionFile("pdf", panel.sessionId);
    } catch {
      // Keep client-side export as the primary fallback.
    }
    exportPdfNotes({
      session: panel.session,
      transcript: panel.transcript,
      recaps: panel.recaps,
      fullSummary: panel.fullSummary,
    });
  }

  async function handleExportMarkdown() {
    if (!panel.sessionId) return;
    try {
      await exportSessionFile("markdown", panel.sessionId);
    } catch {
      // Keep client-side export as the primary fallback.
    }
    exportMarkdownNotes({
      session: panel.session,
      transcript: panel.transcript,
      recaps: panel.recaps,
      fullSummary: panel.fullSummary,
    });
  }

  return (
    <div className={panel.darkMode ? "dark" : ""}>
      <ConsentBanner
        providerLabel={panel.getConsentProviderLabel()}
        open={panel.consentOpen}
        accepted={panel.consentAccepted}
        onAccept={() => void panel.handleConsentAccept()}
        onClose={panel.handleConsentClose}
      />
      <FullSummaryModal
        open={panel.showSummaryModal}
        summary={panel.fullSummary}
        onClose={() => panel.setShowSummaryModal(false)}
      />
      <div className="mx-auto flex min-h-screen w-panel overflow-visible bg-white/85 text-ink shadow-soft dark:bg-slate-900 dark:text-slate-100">
        <main className="min-w-0 flex-1 p-4">
          <header className="mb-4 rounded-2xl bg-ink px-4 py-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-white/70">SnapBack</p>
                <h1 className="mt-1 text-xl font-semibold">Context Recovery</h1>
                <p className="mt-2 text-xs uppercase tracking-[0.2em] text-white/60">{panel.meetingContextLabel}</p>
              </div>
              <button
                className="rounded-full bg-white/10 p-2 hover:bg-white/20"
                onClick={() => panel.setDarkMode((value) => !value)}
              >
                <Moon size={16} />
              </button>
            </div>
          </header>

          {panel.errorMessage ? (
            <section className="mt-4 rounded-[22px] border border-danger/25 bg-danger/10 px-4 py-3 text-sm text-danger">
              {panel.errorMessage}
            </section>
          ) : null}

          <div className="mt-4 space-y-4">
            <SessionControls
              canStart={panel.canStart}
              canEnd={panel.canEnd}
              onStart={() => void panel.handleStartSession()}
              onEnd={() => void panel.handleEndSession()}
              onExportPdf={() => void handleExportPdf()}
              onExportMarkdown={() => void handleExportMarkdown()}
              onExportNotion={() => void panel.handleExportNotion()}
            />

            <RecapPanel
              canLeave={panel.canLeave}
              canCatchUp={panel.canCatchUp}
              absenceSeconds={panel.absenceSeconds}
              latestRecap={panel.latestSummary}
              onLeave={panel.handleLeave}
              onCatchUp={() => void panel.handleCatchUp()}
            />

            <RecapHistory recaps={panel.recaps} />

            <StudyPackPanel
              canGenerate={Boolean(panel.sessionId) && !panel.loading}
              loading={panel.loading}
              studyPack={panel.studyPack}
              onGenerate={() => void panel.handleGenerateStudyPack()}
            />

            <SettingsPanel
              mode={panel.mode}
              recapLength={panel.recapLength}
              language={panel.language}
              apiToken={panel.apiToken}
              darkMode={panel.darkMode}
              notionApiKey={panel.notionApiKey}
              notionPageId={panel.notionPageId}
              onModeChange={panel.setMode}
              onRecapLengthChange={panel.setRecapLength}
              onLanguageChange={panel.setLanguage}
              onApiTokenChange={panel.setApiToken}
              onDarkModeToggle={() => panel.setDarkMode((value) => !value)}
              onNotionApiKeyChange={panel.setNotionApiKey}
              onNotionPageIdChange={panel.setNotionPageId}
            />
          </div>

          {panel.session ? (
            <section className="mt-4 rounded-[24px] bg-ink p-4 text-sm text-white">
              <h2 className="font-semibold">Session status</h2>
              <p className="mt-2 text-white/80">
                Started at {formatTimestamp(panel.session.start_timestamp)} in {panel.session.mode} mode.
              </p>
              <p className="mt-2 text-white/80">
                Summary language: {panel.session.language}. Recap length: {panel.session.recap_length}.
              </p>
              {panel.fullSummary ? <p className="mt-3 leading-6 text-white/80">{panel.fullSummary}</p> : null}
            </section>
          ) : null}
        </main>

        <TranscriptDrawer
          open={panel.drawerOpen}
          transcript={panel.transcript}
          onToggle={() => panel.setDrawerOpen((open) => !open)}
        />
      </div>
    </div>
  );
}

export default App;
