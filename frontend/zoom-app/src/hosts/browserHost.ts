import {
  createBackendRecap,
  endBackendSession,
  exportBackendSessionToNotion,
  getBackendSessionTranscript,
  startBackendSession,
} from "./backendClient";
import type { HostMeetingContext, SnapBackHostAdapter } from "./types";
import type { Mode } from "../types";

function detectMeetingContext(): HostMeetingContext {
  return {
    host: "browser",
    label: "Browser Companion",
    surface: "standalone-panel",
    meetingTitle: document.title || "SnapBack Session",
  };
}

function providerLabel(mode: Mode) {
  return mode === "cloud" ? "AssemblyAI" : "Local Whisper";
}

export function createBrowserHostAdapter(): SnapBackHostAdapter {
  return {
    kind: "browser",
    label: "Browser Companion",
    capabilities: {
      nativeMeetingContext: false,
      nativeAudioCapture: false,
      globalHotkey: false,
      transcriptOverlay: true,
    },
    async getMeetingContext() {
      return detectMeetingContext();
    },
    getConsentProviderLabel(mode) {
      return providerLabel(mode);
    },
    async startSession(input) {
      const result = await startBackendSession(input.mode, input.language, input.recapLength);
      return {
        sessionId: result.session_id,
        startTimestamp: result.start_timestamp,
        session: result.session,
      };
    },
    async endSession(sessionId) {
      const result = await endBackendSession(sessionId);
      return {
        fullSummary: result.full_summary,
        session: result.session,
      };
    },
    async createRecap(sessionId, fromTimestamp, toTimestamp) {
      const result = await createBackendRecap(sessionId, fromTimestamp, toTimestamp);
      return {
        summary: result.summary,
        keywords: result.keywords,
        topicShiftDetected: result.topic_shift_detected,
        missedAlerts: result.missed_alerts,
        recap: result.recap,
      };
    },
    getSessionTranscript(sessionId) {
      return getBackendSessionTranscript(sessionId);
    },
    async exportToNotion(sessionId, pageId, notionApiKey) {
      const result = await exportBackendSessionToNotion(sessionId, pageId, notionApiKey);
      return {
        pageId: result.page_id,
        url: result.url,
      };
    },
  };
}
