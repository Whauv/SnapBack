import { useEffect, useMemo, useRef, useState } from "react";
import { Moon, NotebookText, PanelRightClose, PanelRightOpen, Play, Square } from "lucide-react";
import jsPDF from "jspdf";

type Mode = "cloud" | "local";
type RecapLength = "brief" | "standard" | "detailed";

type SessionRecord = {
  id: string;
  start_timestamp: string;
  end_timestamp?: string | null;
  full_summary?: string | null;
  mode: Mode;
  language: string;
  recap_length: RecapLength;
};

type TranscriptChunk = {
  id: number;
  session_id: string;
  text: string;
  timestamp: string;
};

type MissedAlert = {
  text: string;
  timestamp: string;
};

type Recap = {
  id: number;
  from_timestamp: string;
  to_timestamp: string;
  summary: string;
  keywords: string[];
  topic_shift_detected: boolean;
  missed_alerts: MissedAlert[];
};

const API_BASE = "http://localhost:8000";

function formatTimestamp(timestamp?: string | null) {
  if (!timestamp) return "Not set";
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [transcript, setTranscript] = useState<TranscriptChunk[]>([]);
  const [recaps, setRecaps] = useState<Recap[]>([]);
  const [departureTimestamp, setDepartureTimestamp] = useState<string | null>(null);
  const [latestSummary, setLatestSummary] = useState<Recap | null>(null);
  const [fullSummary, setFullSummary] = useState<string>("");
  const [mode, setMode] = useState<Mode>("cloud");
  const [recapLength, setRecapLength] = useState<RecapLength>("standard");
  const [language, setLanguage] = useState("English");
  const [notionApiKey, setNotionApiKey] = useState("");
  const [notionPageId, setNotionPageId] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [nowMs, setNowMs] = useState(Date.now());
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const absenceSeconds = useMemo(() => {
    if (!departureTimestamp) return 0;
    return Math.max(0, Math.floor((nowMs - new Date(departureTimestamp).getTime()) / 1000));
  }, [departureTimestamp, nowMs]);

  useEffect(() => {
    if (drawerRef.current) {
      drawerRef.current.scrollTop = drawerRef.current.scrollHeight;
    }
  }, [transcript, drawerOpen]);

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
    const response = await fetch(`${API_BASE}/session/${id}/transcript`);
    const data = await response.json();
    setSession(data.session);
    setTranscript(data.transcript);
    setRecaps(data.recaps);
  }

  async function startSession() {
    if (!consentAccepted) return;
    const response = await fetch(`${API_BASE}/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, language, recap_length: recapLength })
    });
    const data = await response.json();
    setSessionId(data.session_id);
    setSession(data.session);
    setTranscript([]);
    setRecaps([]);
    setLatestSummary(null);
    setFullSummary("");
  }

  async function endSession() {
    if (!sessionId) return;
    const response = await fetch(`${API_BASE}/session/end`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });
    const data = await response.json();
    setFullSummary(data.full_summary);
    await loadSession(sessionId);
  }

  async function catchMeUp() {
    if (!sessionId || !departureTimestamp) return;
    const response = await fetch(`${API_BASE}/recap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        from_timestamp: departureTimestamp,
        to_timestamp: new Date().toISOString()
      })
    });
    const data = await response.json();
    setLatestSummary(data.recap);
    setDepartureTimestamp(null);
    await loadSession(sessionId);
  }

  async function exportFile(type: "pdf" | "markdown") {
    if (!sessionId) return;
    const response = await fetch(`${API_BASE}/export/${type}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lecturelens.${type === "pdf" ? "pdf" : "md"}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function exportNotesPdfClientSide() {
    const pdf = new jsPDF();
    pdf.setFontSize(16);
    pdf.text("LectureLens Notes", 12, 16);
    pdf.setFontSize(11);
    pdf.text(fullSummary || "Session summary will appear here after ending the session.", 12, 26, { maxWidth: 180 });
    let y = 46;
    recaps.forEach((recap) => {
      pdf.text(`${formatTimestamp(recap.from_timestamp)} - ${formatTimestamp(recap.to_timestamp)}`, 12, y);
      y += 6;
      pdf.text(recap.summary, 12, y, { maxWidth: 180 });
      y += 12;
    });
    pdf.save("lecturelens-notes.pdf");
  }

  async function exportToNotion() {
    if (!sessionId || !notionPageId) return;
    await fetch(`${API_BASE}/export/notion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        page_id: notionPageId,
        notion_api_key: notionApiKey || undefined
      })
    });
  }

  return (
    <div className={darkMode ? "dark" : ""}>
      <div className="mx-auto flex min-h-screen w-panel overflow-hidden bg-white/85 text-ink shadow-soft dark:bg-slate-900 dark:text-slate-100">
        <main className="flex-1 p-4">
          <header className="mb-4 rounded-2xl bg-ink px-4 py-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-white/70">LectureLens</p>
                <h1 className="mt-1 text-xl font-semibold">Context Recovery</h1>
              </div>
              <button className="rounded-full bg-white/10 p-2 hover:bg-white/20" onClick={() => setDarkMode((value) => !value)}>
                <Moon size={16} />
              </button>
            </div>
          </header>

          {!consentAccepted ? (
            <section className="rounded-2xl border border-accent/20 bg-accent/10 p-4 text-sm">
              <p className="font-semibold">Consent required</p>
              <p className="mt-2">
                LectureLens is now transcribing this session. Audio is processed via {mode === "cloud" ? "AssemblyAI" : "Local Whisper"}.
                No data is shared without your consent.
              </p>
              <button className="mt-3 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => setConsentAccepted(true)}>
                I Understand
              </button>
            </section>
          ) : null}

          <section className="mt-4 rounded-2xl bg-mist p-4 dark:bg-slate-800">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Session Controls</h2>
              <NotebookText size={16} />
            </div>
            <div className="mt-3 flex gap-2">
              <button className="flex flex-1 items-center justify-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={startSession} disabled={!consentAccepted}>
                <Play size={14} /> Start Session
              </button>
              <button className="flex flex-1 items-center justify-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={endSession} disabled={!sessionId}>
                <Square size={14} /> End Session
              </button>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button className="rounded-full border border-ink/15 px-3 py-2 text-xs" onClick={() => exportFile("pdf")} disabled={!sessionId}>Backend PDF</button>
              <button className="rounded-full border border-ink/15 px-3 py-2 text-xs" onClick={() => exportFile("markdown")} disabled={!sessionId}>Markdown</button>
              <button className="rounded-full border border-ink/15 px-3 py-2 text-xs" onClick={exportNotesPdfClientSide}>Export Notes</button>
              <button className="rounded-full border border-ink/15 px-3 py-2 text-xs" onClick={exportToNotion} disabled={!sessionId || !notionPageId}>Push to Notion</button>
            </div>
          </section>

          <section className="mt-4 rounded-2xl border border-amber/40 bg-white p-4 dark:border-amber/30 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Recap Panel</h2>
              {departureTimestamp ? <span className="rounded-full bg-amber px-3 py-1 text-xs font-semibold text-ink">{absenceSeconds}s away</span> : null}
            </div>
            <div className="mt-3 flex gap-2">
              <button className="flex-1 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={() => setDepartureTimestamp(new Date().toISOString())} disabled={!sessionId}>
                I&apos;m Leaving
              </button>
              <button className="flex-1 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={catchMeUp} disabled={!sessionId || !departureTimestamp}>
                I&apos;m Back - Catch Me Up
              </button>
            </div>

            {latestSummary ? (
              <div className="mt-4 rounded-2xl bg-mist p-4 dark:bg-slate-800">
                {latestSummary.topic_shift_detected ? <div className="mb-3 rounded-xl bg-amber/80 px-3 py-2 text-xs font-semibold text-ink">Topic changed while you were away</div> : null}
                {latestSummary.missed_alerts.map((alert) => (
                  <div key={`${alert.timestamp}-${alert.text}`} className="mb-2 rounded-xl bg-danger px-3 py-2 text-xs font-semibold text-white">
                    Important moment missed at {formatTimestamp(alert.timestamp)}: {alert.text}
                  </div>
                ))}
                <p className="text-sm leading-6">{latestSummary.summary}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {latestSummary.keywords.map((keyword) => (
                    <span key={keyword} className="rounded-full bg-white px-3 py-1 text-xs font-medium text-ink dark:bg-slate-700 dark:text-slate-100">{keyword}</span>
                  ))}
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-ink/65 dark:text-slate-400">Recaps will appear here after you return.</p>
            )}
          </section>

          <section className="mt-4 rounded-2xl bg-mist p-4 dark:bg-slate-800">
            <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Recap History</h2>
            <div className="mt-3 space-y-3">
              {recaps.length ? recaps.map((recap) => (
                <article key={recap.id} className="rounded-2xl bg-white p-3 text-sm dark:bg-slate-900">
                  <p className="text-xs uppercase tracking-[0.2em] text-ink/55 dark:text-slate-400">
                    {formatTimestamp(recap.from_timestamp)} - {formatTimestamp(recap.to_timestamp)}
                  </p>
                  <p className="mt-2 leading-6">{recap.summary}</p>
                </article>
              )) : <p className="text-sm text-ink/65 dark:text-slate-400">No recap history yet.</p>}
            </div>
          </section>

          <section className="mt-4 rounded-2xl bg-mist p-4 dark:bg-slate-800">
            <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Settings</h2>
            <div className="mt-3 space-y-3 text-sm">
              <label className="flex items-center justify-between">
                <span>Transcription mode</span>
                <select value={mode} onChange={(event) => setMode(event.target.value as Mode)} className="rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900">
                  <option value="cloud">Cloud mode</option>
                  <option value="local">Local mode</option>
                </select>
              </label>
              <label className="flex items-center justify-between">
                <span>Recap length</span>
                <select value={recapLength} onChange={(event) => setRecapLength(event.target.value as RecapLength)} className="rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900">
                  <option value="brief">Brief</option>
                  <option value="standard">Standard</option>
                  <option value="detailed">Detailed</option>
                </select>
              </label>
              <label className="flex items-center justify-between">
                <span>Summary language</span>
                <select value={language} onChange={(event) => setLanguage(event.target.value)} className="rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900">
                  <option>English</option>
                  <option>Spanish</option>
                  <option>French</option>
                </select>
              </label>
              <input value={notionApiKey} onChange={(event) => setNotionApiKey(event.target.value)} placeholder="Notion API key" className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900" />
              <input value={notionPageId} onChange={(event) => setNotionPageId(event.target.value)} placeholder="Notion page ID" className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900" />
            </div>
          </section>

          {session ? (
            <section className="mt-4 rounded-2xl bg-ink p-4 text-sm text-white">
              <h2 className="font-semibold">Session status</h2>
              <p className="mt-2 text-white/80">Started at {formatTimestamp(session.start_timestamp)} in {session.mode} mode.</p>
              {fullSummary ? <p className="mt-3 leading-6 text-white/80">{fullSummary}</p> : null}
            </section>
          ) : null}
        </main>

        <aside className={`border-l border-ink/10 bg-white/70 dark:bg-slate-950 ${drawerOpen ? "w-[140px]" : "w-[52px]"}`}>
          <button className="m-2 rounded-full border border-ink/10 p-2" onClick={() => setDrawerOpen((open) => !open)}>
            {drawerOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
          </button>
          {drawerOpen ? (
            <div className="px-3 pb-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/60 dark:text-slate-400">Live Transcript</h2>
              <div ref={drawerRef} className="mt-3 max-h-[80vh] space-y-2 overflow-y-auto pr-1">
                {transcript.length ? transcript.map((entry) => (
                  <article key={entry.id} className="rounded-2xl bg-mist p-2 text-xs dark:bg-slate-800">
                    <p className="font-semibold text-ink/60 dark:text-slate-400">{formatTimestamp(entry.timestamp)}</p>
                    <p className="mt-1 leading-5">{entry.text}</p>
                  </article>
                )) : <p className="text-xs text-ink/60 dark:text-slate-400">Waiting for transcript data.</p>}
              </div>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

export default App;
