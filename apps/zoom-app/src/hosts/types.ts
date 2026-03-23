import type { Mode, Recap, RecapLength, SessionRecord, SessionTranscriptResponse, StudyPack } from "../types";

export type HostKind = "browser" | "google-meet-extension" | "google-meet-addon" | "zoom-app" | "teams-app";

export type HostCapabilities = {
  nativeMeetingContext: boolean;
  nativeAudioCapture: boolean;
  globalHotkey: boolean;
  transcriptOverlay: boolean;
};

export type HostMeetingContext = {
  host: HostKind;
  label: string;
  surface: string;
  meetingTitle?: string;
  meetingId?: string;
  participantName?: string;
};

export type HostSessionStartInput = {
  mode: Mode;
  language: string;
  recapLength: RecapLength;
};

export type HostSessionStartResult = {
  sessionId: string;
  startTimestamp: string;
  session: SessionRecord;
};

export type HostEndSessionResult = {
  fullSummary: string;
  session: SessionRecord;
};

export type HostRecapResult = {
  summary: string;
  keywords: string[];
  topicShiftDetected: boolean;
  missedAlerts: Recap["missed_alerts"];
  recap: Recap;
};

export interface SnapBackHostAdapter {
  kind: HostKind;
  label: string;
  capabilities: HostCapabilities;
  getMeetingContext(): Promise<HostMeetingContext | null>;
  getConsentProviderLabel(mode: Mode): string;
  startSession(input: HostSessionStartInput): Promise<HostSessionStartResult>;
  endSession(sessionId: string): Promise<HostEndSessionResult>;
  createRecap(sessionId: string, fromTimestamp: string, toTimestamp: string): Promise<HostRecapResult>;
  getSessionTranscript(sessionId: string): Promise<SessionTranscriptResponse>;
  generateStudyPack(sessionId: string): Promise<StudyPack>;
  exportToNotion(sessionId: string, pageId: string, notionApiKey?: string): Promise<{ pageId: string; url: string }>;
}
