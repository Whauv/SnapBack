const API_TOKEN_STORAGE_KEY = "snapback.apiToken";
const DEFAULT_DEV_API_TOKEN = "snapback-local-dev-token";

export function getApiToken(): string {
  const stored = window.localStorage.getItem(API_TOKEN_STORAGE_KEY)?.trim();
  if (stored) {
    return stored;
  }
  const configured = (import.meta.env.VITE_SNAPBACK_API_TOKEN as string | undefined)?.trim();
  return configured || DEFAULT_DEV_API_TOKEN;
}

export function setApiToken(token: string) {
  const trimmed = token.trim();
  if (!trimmed) {
    window.localStorage.removeItem(API_TOKEN_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(API_TOKEN_STORAGE_KEY, trimmed);
}

export function buildApiHeaders(headers?: HeadersInit): HeadersInit {
  return {
    Authorization: `Bearer ${getApiToken()}`,
    ...(headers ?? {}),
  };
}
