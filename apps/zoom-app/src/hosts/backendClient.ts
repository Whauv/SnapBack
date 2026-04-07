import type { Mode, RecapLength, SessionTranscriptResponse } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch {
    throw new Error("Unable to reach the SnapBack API. Check that the backend is running.");
  }

  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function startBackendSession(mode: Mode, language: string, recapLength: RecapLength) {
  return request<{ session_id: string; start_timestamp: string; session: SessionTranscriptResponse["session"] }>(
    "/session/start",
    {
      method: "POST",
      body: JSON.stringify({ mode, language, recap_length: recapLength }),
    },
  );
}

export async function endBackendSession(sessionId: string) {
  return request<{ full_summary: string; session: SessionTranscriptResponse["session"] }>("/session/end", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function getBackendSessionTranscript(sessionId: string) {
  return request<SessionTranscriptResponse>(`/session/${sessionId}/transcript`);
}

export async function createBackendRecap(sessionId: string, fromTimestamp: string, toTimestamp: string) {
  return request<{
    summary: string;
    keywords: string[];
    topic_shift_detected: boolean;
    missed_alerts: { text: string; timestamp: string }[];
    recap: SessionTranscriptResponse["recaps"][number];
  }>("/recap", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      from_timestamp: fromTimestamp,
      to_timestamp: toTimestamp,
    }),
  });
}

export async function exportSessionFile(type: "pdf" | "markdown", sessionId: string) {
  const response = await fetch(`${API_BASE}/export/${type}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!response.ok) {
    throw new Error(`Export failed with status ${response.status}`);
  }
  return response.blob();
}

export async function exportBackendSessionToNotion(sessionId: string, pageId: string, notionApiKey?: string) {
  return request<{ page_id: string; url: string }>("/export/notion", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      page_id: pageId,
      notion_api_key: notionApiKey || undefined,
    }),
  });
}

export async function generateBackendStudyPack(sessionId: string) {
  return request<{
    session_id: string;
    study_pack: {
      outline: string[];
      flashcards: { question: string; answer: string }[];
      quiz_questions: { question: string; answer: string; explanation: string }[];
      review_priorities: string[];
    };
  }>("/study/pack", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}
