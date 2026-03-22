import { useEffect, useMemo, useRef, useState } from "react";
import { Moon } from "lucide-react";
import { createRecap, endSession, exportToNotion, getSessionTranscript, startSession } from "./api";
import ConsentBanner from "./components/ConsentBanner";
import FullSummaryModal from "./components/FullSummaryModal";
import RecapHistory from "./components/RecapHistory";
import RecapPanel from "./components/RecapPanel";
import SessionControls from "./components/SessionControls";
import SettingsPanel from "./components/SettingsPanel";
import TranscriptDrawer from "./components/TranscriptDrawer";
import { exportMarkdownNotes, exportPdfNotes } from "./exporters";
import type { Mode, Recap, RecapLength, SessionRecord, TranscriptChunk } from "./types";
import { formatTimestamp } from "./utils";

function App() {
  const settingsStorageKey = "snapback.zoom.settings";
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [transcript, setTranscript] = useState<TranscriptChunk[]>([]);
  const [recaps, setRecaps] = useState<Recap[]>([]);
  const [departureTimestamp, setDepartureTimestamp] = useState<string | null>(null);
  const [latestSummary, setLatestSummary] = useState<Recap | null>(null);
  const [fullSummary, setFullSummary] = useState("");
  const [mode, setMode] = useState<Mode>("cloud");
  const [recapLength, setRecapLength] = useState<RecapLength>("standard");
  const [language, setLanguage] = useState("English");
  const [notionApiKey, setNotionApiKey] = useState("");
  const [notionPageId, setNotionPageId] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentOpen, setConsentOpen] = useState(false);
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(Date.now());
  const pendingStartRef = useRef(false);

  const absenceSeconds = useMemo(() => {
    if (!departureTimestamp) return 0;
    return Math.max(0, Math.floor((nowMs - new Date(departureTimestamp).getTime()) / 1000));
  }, [departureTimestamp, nowMs]);

  useEffect(() => {
    const savedSettings = window.localStorage.getItem(settingsStorageKey);
    if (!savedSettings) return;
    try {
      const parsed = JSON.parse(savedSettings) as Partial<{
        mode: Mode;
        recapLength: RecapLength;
        language: string;
        notionApiKey: string;
        notionPageId: string;
        darkMode: boolean;
      }>;
      if (parsed.mode) setMode(parsed.mode);
      if (parsed.recapLength) setRecapLength(parsed.recapLength);
      if (parsed.language) setLanguage(parsed.language);
      if (parsed.notionApiKey) setNotionApiKey(parsed.notionApiKey);
      if (parsed.notionPageId) setNotionPageId(parsed.notionPageId);
      if (typeof parsed.darkMode === "boolean") setDarkMode(parsed.darkMode);
    } catch {
      window.localStorage.removeItem(settingsStorageKey);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(
      settingsStorageKey,
      JSON.stringify({ mode, recapLength, language, notionApiKey, notionPageId, darkMode }),
    );
  }, [darkMode, language, mode, notionApiKey, notionPageId, recapLength]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    if (!sessionId) return;
    const interval = window.setInterval(() => {
      void loadSession(sessionId);
    }, 5000);
    return () => window.clearInterval(interval);
  }, [sessionId]);

  useEffect(() => {
    if (!departureTimestamp) return;
    const interval = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(interval);
  }, [departureTimestamp]);

  async function loadSession(id: string) {
    const data = await getSessionTranscript(id);
    setSession(data.session);
    setTranscript(data.transcript);
    setRecaps(data.recaps);
    setLatestSummary((current) => current ?? data.recaps[data.recaps.length - 1] ?? null);
  }

  async function startSessionFlow() {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await startSession(mode, language, recapLength);
      setSessionId(data.session_id);
      setSession(data.session);
      setTranscript([]);
      setRecaps([]);
      setLatestSummary(null);
      setFullSummary("");
      setDepartureTimestamp(null);
      setConsentAccepted(false);
      setConsentOpen(false);
      setShowSummaryModal(false);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start session.");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartSession() {
    if (!consentAccepted) {
      pendingStartRef.current = true;
      setConsentOpen(true);
      return;
    }
    await startSessionFlow();
  }

  async function handleConsentAccept() {
    setConsentAccepted(true);
    setConsentOpen(false);
    if (pendingStartRef.current) {
      pendingStartRef.current = false;
      await startSessionFlow();
    }
  }

  async function handleEndSession() {
    if (!sessionId) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await endSession(sessionId);
      setFullSummary(data.full_summary);
      setShowSummaryModal(true);
      await loadSession(sessionId);
      if (notionPageId) {
        await exportToNotion(sessionId, notionPageId, notionApiKey || undefined);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to end session.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCatchUp() {
    if (!sessionId || !departureTimestamp) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await createRecap(sessionId, departureTimestamp, new Date().toISOString());
      setLatestSummary(data.recap);
      setDepartureTimestamp(null);
      await loadSession(sessionId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to generate recap.");
    } finally {
      setLoading(false);
    }
  }

  function handleExportPdf() {
    exportPdfNotes({ session, transcript, recaps, fullSummary });
  }

  function handleExportMarkdown() {
    exportMarkdownNotes({ session, transcript, recaps, fullSummary });
  }

  async function handleExportNotion() {
    if (!sessionId || !notionPageId) {
      setErrorMessage("Add a Notion Page ID in settings before exporting.");
      return;
    }
    try {
      await exportToNotion(sessionId, notionPageId, notionApiKey || undefined);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to export to Notion.");
    }
  }

  return (
    <div className={darkMode ? "dark" : ""}>
      <ConsentBanner
        mode={mode}
        open={consentOpen}
        accepted={consentAccepted}
        onAccept={() => void handleConsentAccept()}
        onClose={() => {
          pendingStartRef.current = false;
          setConsentOpen(false);
        }}
      />
      <FullSummaryModal open={showSummaryModal} summary={fullSummary} onClose={() => setShowSummaryModal(false)} />
      <div className="mx-auto flex min-h-screen w-panel overflow-hidden bg-white/85 text-ink shadow-soft dark:bg-slate-900 dark:text-slate-100">
        <main className="flex-1 p-4">
          <header className="mb-4 rounded-2xl bg-ink px-4 py-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-white/70">SnapBack</p>
                <h1 className="mt-1 text-xl font-semibold">Context Recovery</h1>
              </div>
              <button className="rounded-full bg-white/10 p-2 hover:bg-white/20" onClick={() => setDarkMode((value) => !value)}>
                <Moon size={16} />
              </button>
            </div>
          </header>

          {errorMessage ? (
            <section className="mt-4 rounded-[22px] border border-danger/25 bg-danger/10 px-4 py-3 text-sm text-danger">
              {errorMessage}
            </section>
          ) : null}

          <div className="mt-4 space-y-4">
            <SessionControls
              canStart={!sessionId && !loading}
              canEnd={Boolean(sessionId) && !loading}
              onStart={() => void handleStartSession()}
              onEnd={() => void handleEndSession()}
              onExportPdf={handleExportPdf}
              onExportMarkdown={handleExportMarkdown}
              onExportNotion={() => void handleExportNotion()}
            />

            <RecapPanel
              canLeave={Boolean(sessionId) && !loading}
              canCatchUp={Boolean(sessionId && departureTimestamp) && !loading}
              absenceSeconds={absenceSeconds}
              latestRecap={latestSummary}
              onLeave={() => setDepartureTimestamp(new Date().toISOString())}
              onCatchUp={() => void handleCatchUp()}
            />

            <RecapHistory recaps={recaps} />

            <SettingsPanel
              mode={mode}
              recapLength={recapLength}
              language={language}
              darkMode={darkMode}
              notionApiKey={notionApiKey}
              notionPageId={notionPageId}
              onModeChange={setMode}
              onRecapLengthChange={setRecapLength}
              onLanguageChange={setLanguage}
              onDarkModeToggle={() => setDarkMode((value) => !value)}
              onNotionApiKeyChange={setNotionApiKey}
              onNotionPageIdChange={setNotionPageId}
            />
          </div>

          {session ? (
            <section className="mt-4 rounded-[24px] bg-ink p-4 text-sm text-white">
              <h2 className="font-semibold">Session status</h2>
              <p className="mt-2 text-white/80">Started at {formatTimestamp(session.start_timestamp)} in {session.mode} mode.</p>
              <p className="mt-2 text-white/80">
                Summary language: {session.language}. Recap length: {session.recap_length}.
              </p>
              {fullSummary ? <p className="mt-3 leading-6 text-white/80">{fullSummary}</p> : null}
            </section>
          ) : null}
        </main>

        <TranscriptDrawer open={drawerOpen} transcript={transcript} onToggle={() => setDrawerOpen((open) => !open)} />
      </div>
    </div>
  );
}

export default App;
