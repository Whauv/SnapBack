import type { Mode, RecapLength } from "../types";

type SettingsPanelProps = {
  mode: Mode;
  recapLength: RecapLength;
  language: string;
  darkMode: boolean;
  notionApiKey: string;
  notionPageId: string;
  onModeChange: (mode: Mode) => void;
  onRecapLengthChange: (length: RecapLength) => void;
  onLanguageChange: (language: string) => void;
  onDarkModeToggle: () => void;
  onNotionApiKeyChange: (value: string) => void;
  onNotionPageIdChange: (value: string) => void;
};

function SettingsPanel(props: SettingsPanelProps) {
  const {
    mode,
    recapLength,
    language,
    darkMode,
    notionApiKey,
    notionPageId,
    onModeChange,
    onRecapLengthChange,
    onLanguageChange,
    onDarkModeToggle,
    onNotionApiKeyChange,
    onNotionPageIdChange,
  } = props;

  return (
    <section className="rounded-[24px] bg-mist p-4 dark:bg-slate-800">
      <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-ink/70 dark:text-slate-300">Settings</h2>
      <div className="mt-3 space-y-3 text-sm">
        <label className="flex items-center justify-between gap-3">
          <span>Transcription mode</span>
          <select value={mode} onChange={(event) => onModeChange(event.target.value as Mode)} className="rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900">
            <option value="cloud">Cloud mode</option>
            <option value="local">Local mode</option>
          </select>
        </label>
        <label className="flex items-center justify-between gap-3">
          <span>Recap length</span>
          <select value={recapLength} onChange={(event) => onRecapLengthChange(event.target.value as RecapLength)} className="rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900">
            <option value="brief">Brief</option>
            <option value="standard">Standard</option>
            <option value="detailed">Detailed</option>
          </select>
        </label>
        <label className="flex items-center justify-between gap-3">
          <span>Summary language</span>
          <select value={language} onChange={(event) => onLanguageChange(event.target.value)} className="rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900">
            <option>English</option>
            <option>Spanish</option>
            <option>French</option>
            <option>German</option>
          </select>
        </label>
        <label className="flex items-center justify-between gap-3">
          <span>Dark mode</span>
          <button className="rounded-full border border-ink/15 px-3 py-2 text-xs font-semibold" onClick={onDarkModeToggle}>
            {darkMode ? "On" : "Off"}
          </button>
        </label>
        <input type="password" value={notionApiKey} onChange={(event) => onNotionApiKeyChange(event.target.value)} placeholder="Optional Notion API key override" className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900" autoComplete="off" />
        <input value={notionPageId} onChange={(event) => onNotionPageIdChange(event.target.value)} placeholder="Notion page ID" className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2 dark:bg-slate-900" />
        <p className="text-xs leading-5 text-ink/60 dark:text-slate-400">
          Cloud mode streams audio through AssemblyAI. Local mode uses whisper.cpp on-device. Session data is cleaned up
          automatically based on your backend retention window.
        </p>
        <p className="text-xs leading-5 text-ink/60 dark:text-slate-400">
          Tip: leave the Notion key blank to use the backend environment secret instead of keeping a personal key in the browser.
        </p>
      </div>
    </section>
  );
}

export default SettingsPanel;
