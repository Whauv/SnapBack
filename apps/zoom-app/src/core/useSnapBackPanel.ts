import { useEffect, useMemo, useRef, useState } from "react";
import type { SnapBackHostAdapter } from "../hosts";
import type { Mode, Recap, RecapLength, SessionRecord, StudyPack, TranscriptChunk } from "../types";

type UseSnapBackPanelOptions = {
  host: SnapBackHostAdapter;
  settingsStorageKey?: string;
};

export function useSnapBackPanel({ host, settingsStorageKey = "snapback.zoom.settings" }: UseSnapBackPanelOptions) {
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
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentOpen, setConsentOpen] = useState(false);
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [studyPack, setStudyPack] = useState<StudyPack | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(Date.now());
  const [meetingContextLabel, setMeetingContextLabel] = useState(host.label);
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
        notionPageId: string;
        darkMode: boolean;
      }>;
      if (parsed.mode) setMode(parsed.mode);
      if (parsed.recapLength) setRecapLength(parsed.recapLength);
      if (parsed.language) setLanguage(parsed.language);
      if (parsed.notionPageId) setNotionPageId(parsed.notionPageId);
      if (typeof parsed.darkMode === "boolean") setDarkMode(parsed.darkMode);
    } catch {
      window.localStorage.removeItem(settingsStorageKey);
    }
  }, [settingsStorageKey]);

  useEffect(() => {
    window.localStorage.setItem(
      settingsStorageKey,
      JSON.stringify({ mode, recapLength, language, notionPageId, darkMode }),
    );
  }, [darkMode, language, mode, notionPageId, recapLength, settingsStorageKey]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    void host.getMeetingContext().then((context) => {
      if (context?.label) {
        setMeetingContextLabel(context.label);
      }
    });
  }, [host]);

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
    const data = await host.getSessionTranscript(id);
    setSession(data.session);
    setTranscript(data.transcript);
    setRecaps(data.recaps);
    setLatestSummary((current) => current ?? data.recaps[data.recaps.length - 1] ?? null);
  }

  async function startSessionFlow() {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await host.startSession({ mode, language, recapLength });
      setSessionId(data.sessionId);
      setSession(data.session);
      setTranscript([]);
      setRecaps([]);
      setLatestSummary(null);
      setFullSummary("");
      setStudyPack(null);
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
      const data = await host.endSession(sessionId);
      setFullSummary(data.fullSummary);
      setShowSummaryModal(true);
      await loadSession(sessionId);
      if (notionPageId) {
        await host.exportToNotion(sessionId, notionPageId, notionApiKey || undefined);
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
      const data = await host.createRecap(sessionId, departureTimestamp, new Date().toISOString());
      setLatestSummary(data.recap);
      setDepartureTimestamp(null);
      await loadSession(sessionId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to generate recap.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExportNotion() {
    if (!sessionId || !notionPageId) {
      setErrorMessage("Add a Notion Page ID in settings before exporting.");
      return;
    }
    try {
      await host.exportToNotion(sessionId, notionPageId, notionApiKey || undefined);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to export to Notion.");
    }
  }

  async function handleGenerateStudyPack() {
    if (!sessionId) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const generatedStudyPack = await host.generateStudyPack(sessionId);
      setStudyPack(generatedStudyPack);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to generate study pack.");
    } finally {
      setLoading(false);
    }
  }

  return {
    absenceSeconds,
    consentAccepted,
    consentOpen,
    darkMode,
    departureTimestamp,
    drawerOpen,
    errorMessage,
    fullSummary,
    host,
    language,
    latestSummary,
    loading,
    meetingContextLabel,
    mode,
    notionApiKey,
    notionPageId,
    recapLength,
    recaps,
    session,
    sessionId,
    showSummaryModal,
    studyPack,
    transcript,
    fullSummaryOpen: showSummaryModal,
    setDarkMode,
    setDrawerOpen,
    setLanguage,
    setMode,
    setNotionApiKey,
    setNotionPageId,
    setRecapLength,
    setShowSummaryModal,
    handleCatchUp,
    handleConsentAccept,
    handleEndSession,
    handleExportNotion,
    handleGenerateStudyPack,
    handleLeave: () => setDepartureTimestamp(new Date().toISOString()),
    handleStartSession,
    handleConsentClose: () => {
      pendingStartRef.current = false;
      setConsentOpen(false);
    },
    getConsentProviderLabel: () => host.getConsentProviderLabel(mode),
    canStart: !sessionId && !loading,
    canEnd: Boolean(sessionId) && !loading,
    canLeave: Boolean(sessionId) && !loading,
    canCatchUp: Boolean(sessionId && departureTimestamp) && !loading,
  };
}
