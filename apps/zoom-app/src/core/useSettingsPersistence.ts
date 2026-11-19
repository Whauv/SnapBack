import { useEffect, useState } from "react";
import { getApiToken, setApiToken as persistApiToken } from "../hosts/auth";
import type { Mode, RecapLength } from "../types";

export type SnapBackSettings = {
  mode: Mode;
  recapLength: RecapLength;
  language: string;
  apiToken: string;
  notionApiKey: string;
  notionPageId: string;
  darkMode: boolean;
};

type PersistedSettings = Pick<
  SnapBackSettings,
  "mode" | "recapLength" | "language" | "apiToken" | "notionPageId" | "darkMode"
>;

/**
 * Owns the user settings slice: in-memory state, localStorage load/save,
 * API-token persistence, and the dark-mode document class. `notionApiKey` is
 * intentionally kept in memory only and never written to storage.
 */
export function useSettingsPersistence(storageKey: string) {
  const [mode, setMode] = useState<Mode>("cloud");
  const [recapLength, setRecapLength] = useState<RecapLength>("standard");
  const [language, setLanguage] = useState("English");
  const [apiToken, setApiToken] = useState(() => getApiToken());
  const [notionApiKey, setNotionApiKey] = useState("");
  const [notionPageId, setNotionPageId] = useState("");
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    const savedSettings = window.localStorage.getItem(storageKey);
    if (!savedSettings) return;
    try {
      const parsed = JSON.parse(savedSettings) as Partial<PersistedSettings>;
      if (parsed.mode) setMode(parsed.mode);
      if (parsed.recapLength) setRecapLength(parsed.recapLength);
      if (parsed.language) setLanguage(parsed.language);
      if (parsed.apiToken) setApiToken(parsed.apiToken);
      if (parsed.notionPageId) setNotionPageId(parsed.notionPageId);
      if (typeof parsed.darkMode === "boolean") setDarkMode(parsed.darkMode);
    } catch {
      window.localStorage.removeItem(storageKey);
    }
  }, [storageKey]);

  useEffect(() => {
    persistApiToken(apiToken);
  }, [apiToken]);

  useEffect(() => {
    window.localStorage.setItem(
      storageKey,
      JSON.stringify({ mode, recapLength, language, apiToken, notionPageId, darkMode }),
    );
  }, [apiToken, darkMode, language, mode, notionPageId, recapLength, storageKey]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const settings: SnapBackSettings = {
    mode,
    recapLength,
    language,
    apiToken,
    notionApiKey,
    notionPageId,
    darkMode,
  };

  function update(partial: Partial<SnapBackSettings>) {
    if (partial.mode !== undefined) setMode(partial.mode);
    if (partial.recapLength !== undefined) setRecapLength(partial.recapLength);
    if (partial.language !== undefined) setLanguage(partial.language);
    if (partial.apiToken !== undefined) setApiToken(partial.apiToken);
    if (partial.notionApiKey !== undefined) setNotionApiKey(partial.notionApiKey);
    if (partial.notionPageId !== undefined) setNotionPageId(partial.notionPageId);
    if (partial.darkMode !== undefined) setDarkMode(partial.darkMode);
  }

  return {
    settings,
    update,
    setDarkMode,
    toggleDarkMode: () => setDarkMode((value) => !value),
  };
}
