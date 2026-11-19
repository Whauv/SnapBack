import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SnapBackSettings } from "../core/useSettingsPersistence";
import SettingsPanel from "./SettingsPanel";

const SETTINGS: SnapBackSettings = {
  mode: "cloud",
  recapLength: "standard",
  language: "English",
  apiToken: "token",
  notionApiKey: "",
  notionPageId: "",
  darkMode: false,
};

describe("SettingsPanel", () => {
  it("emits a partial change when a select changes", () => {
    const onChange = vi.fn();
    render(<SettingsPanel settings={SETTINGS} onChange={onChange} onToggleDarkMode={() => {}} />);
    fireEvent.change(screen.getByDisplayValue("Cloud mode"), { target: { value: "local" } });
    expect(onChange).toHaveBeenCalledWith({ mode: "local" });
  });

  it("emits a partial change when the token input changes", () => {
    const onChange = vi.fn();
    render(<SettingsPanel settings={SETTINGS} onChange={onChange} onToggleDarkMode={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("SnapBack API token"), { target: { value: "new-token" } });
    expect(onChange).toHaveBeenCalledWith({ apiToken: "new-token" });
  });

  it("calls onToggleDarkMode from the dark-mode button", () => {
    const onToggleDarkMode = vi.fn();
    render(<SettingsPanel settings={SETTINGS} onChange={() => {}} onToggleDarkMode={onToggleDarkMode} />);
    fireEvent.click(screen.getByText("Off"));
    expect(onToggleDarkMode).toHaveBeenCalledOnce();
  });
});
