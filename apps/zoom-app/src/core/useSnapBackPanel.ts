import { useEffect, useRef, useState } from "react";
import { exportMarkdownNotes, exportPdfNotes } from "../exporters";
import type { SnapBackHostAdapter } from "../hosts";
import { exportSessionFile } from "../hosts/backendClient";
import type { Recap, SessionRecord, StudyPack, TranscriptChunk } from "../types";
import { useAbsenceClock } from "./useAbsenceClock";
import { useSettingsPersistence } from "./useSettingsPersistence";

type UseSnapBackPanelOptions = {
  host: SnapBackHostAdapter;
  settingsStorageKey?: string;
};

export function useSnapBackPanel({ host, settingsStorageKey = "snapback.zoom.settings" }: UseSnapBackPanelOptions) {
  const { settings, update: updateSettings, toggleDarkMode } = useSettingsPersistence(settingsStorageKey);
  const { mode, language, recapLength, notionApiKey, notionPageId, darkMode } = settings;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [transcript, setTranscript] = useState<TranscriptChunk[]>([]);
  const [recaps, setRecaps] = useState<Recap[]>([]);
  const [departureTimestamp, setDepartureTimestamp] = useState<string | null>(null);
  const [latestSummary, setLatestSummary] = useState<Recap | null>(null);
  const [fullSummary, setFullSummary] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentOpen, setConsentOpen] = useState(false);
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [studyPack, setStudyPack] = useState<StudyPack | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [meetingContextLabel, setMeetingContextLabel] = useState(host.label);
  const pendingStartRef = useRef(false);

  const absenceSeconds = useAbsenceClock(departureTimestamp);

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
    // Polling should restart only when the session id changes, not when the
    // per-render loadSession closure is recreated.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

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

  async function handleExport(kind: "pdf" | "markdown") {
    if (!sessionId) return;
    try {
      await exportSessionFile(kind, sessionId);
    } catch {
      // Keep client-side export as the primary fallback.
    }
    const payload = { session, transcript, recaps, fullSummary };
    if (kind === "pdf") {
      exportPdfNotes(payload);
    } else {
      exportMarkdownNotes(payload);
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
    latestSummary,
    loading,
    meetingContextLabel,
    recaps,
    session,
    sessionId,
    settings,
    showSummaryModal,
    studyPack,
    transcript,
    updateSettings,
    toggleDarkMode,
    setDrawerOpen,
    setShowSummaryModal,
    handleCatchUp,
    handleConsentAccept,
    handleEndSession,
    handleExportMarkdown: () => handleExport("markdown"),
    handleExportNotion,
    handleExportPdf: () => handleExport("pdf"),
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
